"""Supply orchestrator: inspect case state, pick next capability, delegate.

Separate from RecoveryOrchestrator on purpose. Both share the registry and the
SafetyGate, but their state machines are unrelated: one advances a patient's
recovery, the other advances a purchase.
"""

from __future__ import annotations

from typing import Any, Protocol
from uuid import uuid4

from eir_shared.capabilities import Capability
from eir_shared.events import DomainEvent
from eir_shared.identity import AgentIdentity
from eir_shared.observability import StructuredLogger, WorkflowTrace
from eir_shared.registry import AgentDescriptor
from eir_shared.supply import ReplenishmentStatus

from eir_agents.common.types import DelegationDecision
from eir_agents.safety.handler import SafetyGate

EVENT_TO_CAPABILITY: dict[str, str] = {
    "InventoryLevelLow": Capability.SUPPLY_FORECAST,
    "ReplenishmentRequested": Capability.SUPPLIER_CONTACT,
    "SupplierQuoteReceived": Capability.PURCHASE_ORDER_DRAFT,
    "PurchaseOrderDrafted": Capability.PURCHASE_ORDER_APPROVE,
}

CLOSED_STATUSES = frozenset(
    {
        ReplenishmentStatus.COMPLETED.value,
        ReplenishmentStatus.CANCELLED.value,
    }
)


class CapabilityRegistry(Protocol):
    def find_by_capability(self, capability: str) -> AgentDescriptor | None: ...

    def list_agents(self) -> list[AgentDescriptor]: ...


class SupplyOrchestrator:
    def __init__(
        self,
        registry: CapabilityRegistry,
        safety: SafetyGate | None = None,
        logger: StructuredLogger | None = None,
    ) -> None:
        self.registry = registry
        self.safety = safety or SafetyGate()
        self.logger = logger or StructuredLogger("eir.supply_orchestrator")

    def plan_capability(
        self,
        event: DomainEvent,
        case: dict[str, Any] | None = None,
    ) -> str | None:
        case = case or {}
        status = str(case.get("status", ReplenishmentStatus.ACTIVE.value))
        base = EVENT_TO_CAPABILITY.get(event.event_type)
        if base is None:
            return None
        if status in CLOSED_STATUSES:
            return None

        if event.event_type == "InventoryLevelLow":
            if status != ReplenishmentStatus.ACTIVE.value:
                return None
            return Capability.SUPPLY_FORECAST

        if event.event_type == "ReplenishmentRequested":
            if status not in {
                ReplenishmentStatus.ACTIVE.value,
                ReplenishmentStatus.SOURCING.value,
            }:
                return None
            return Capability.SUPPLIER_CONTACT

        if event.event_type == "SupplierQuoteReceived":
            if status != ReplenishmentStatus.SOURCING.value:
                return None
            return Capability.PURCHASE_ORDER_DRAFT

        if event.event_type == "PurchaseOrderDrafted":
            # Already ordered means the approval was consumed; replaying the
            # drafted event must not place a second order.
            if status == ReplenishmentStatus.ORDERED.value:
                return None
            return Capability.PURCHASE_ORDER_APPROVE

        return base

    def next_capability(
        self,
        event: DomainEvent,
        case: dict[str, Any] | None = None,
    ) -> str | None:
        return self.plan_capability(event, case)

    def delegate(
        self,
        case_id: str,
        event: DomainEvent,
        case: dict[str, Any] | None = None,
    ) -> DelegationDecision:
        trace_id = str(uuid4())
        capability = self.plan_capability(event, case)
        if capability is None:
            decision = DelegationDecision(
                episode_id=case_id,
                capability=None,
                allowed=False,
                event_type=event.event_type,
                reason=f"planner: no capability for {event.event_type} in current case state",
            )
            self._trace(case_id, trace_id, event, "supply_orchestrator", "ok")
            return decision

        descriptor = self.registry.find_by_capability(capability)
        if descriptor is None:
            return DelegationDecision(
                episode_id=case_id,
                capability=capability,
                allowed=False,
                event_type=event.event_type,
                reason=f"no agent registered for capability {capability}",
            )

        policy = self.safety.authorize(
            identity=_identity_from(descriptor),
            capability=capability,
            context={
                "episode_id": case_id,
                "event_type": event.event_type,
                "payload": event.payload,
                "case_status": (case or {}).get("status"),
            },
            agent_risk_level=descriptor.risk_level,
        )
        status = "delegated" if policy.allowed else "blocked"
        self._trace(case_id, trace_id, event, descriptor.name, status)
        return DelegationDecision(
            episode_id=case_id,
            capability=capability,
            agent_name=descriptor.name,
            allowed=policy.allowed,
            requires_human_approval=policy.requires_human_approval,
            reason=policy.reason,
            event_type=event.event_type,
        )

    def _trace(
        self,
        case_id: str,
        trace_id: str,
        event: DomainEvent,
        agent_name: str,
        status: str,
    ) -> None:
        self.logger.emit(
            WorkflowTrace(
                workflow_id=case_id,
                episode_id=case_id,
                trace_id=trace_id,
                agent_name=agent_name,
                event_type=event.event_type,
                status=status,  # type: ignore[arg-type]
            )
        )


def _identity_from(descriptor: AgentDescriptor) -> AgentIdentity:
    return AgentIdentity(
        name=descriptor.name,
        version=descriptor.version,
        granted_capabilities=descriptor.effective_grants(),
    )
