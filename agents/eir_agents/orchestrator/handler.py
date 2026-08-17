"""Recovery orchestrator: inspect state, pick next capability, delegate.

Does not implement outreach, risk, FHIR, or scheduling itself.
"""

from uuid import uuid4

from eir_shared.capabilities import Capability
from eir_shared.events import DomainEvent
from eir_shared.identity import AgentIdentity
from eir_shared.observability import StructuredLogger, WorkflowTrace
from eir_shared.registry import AgentDescriptor

from eir_agents.common.types import DelegationDecision
from eir_agents.registry.service import AgentRegistry
from eir_agents.safety.handler import SafetyGate

EVENT_TO_CAPABILITY: dict[str, str] = {
    "FollowUpDue": Capability.PATIENT_CONTACT,
    "PatientResponded": Capability.RISK_ASSESS,
    "RiskEscalated": Capability.ESCALATION_REQUEST,
    "AdherenceConcernDetected": Capability.ADHERENCE_CHECK,
    "AppointmentRequested": Capability.APPOINTMENT_SCHEDULE,
}


class RecoveryOrchestrator:
    def __init__(
        self,
        registry: AgentRegistry,
        safety: SafetyGate | None = None,
        logger: StructuredLogger | None = None,
    ) -> None:
        self.registry = registry
        self.safety = safety or SafetyGate()
        self.logger = logger or StructuredLogger("eir.orchestrator")

    def next_capability(self, event: DomainEvent) -> str | None:
        return EVENT_TO_CAPABILITY.get(event.event_type)

    def delegate(self, episode_id: str, event: DomainEvent) -> DelegationDecision:
        trace_id = str(uuid4())
        capability = self.next_capability(event)
        if capability is None:
            decision = DelegationDecision(
                episode_id=episode_id,
                capability=None,
                allowed=False,
                event_type=event.event_type,
                reason=f"no capability mapping for {event.event_type}",
            )
            self._trace(episode_id, trace_id, event, "recovery_orchestrator", "ok")
            return decision

        descriptor = self.registry.find_by_capability(capability)
        if descriptor is None:
            return DelegationDecision(
                episode_id=episode_id,
                capability=capability,
                allowed=False,
                event_type=event.event_type,
                reason=f"no agent registered for capability {capability}",
            )

        policy = self.safety.authorize(
            identity=_identity_from(descriptor),
            capability=capability,
            context={"episode_id": episode_id, "event_type": event.event_type},
            agent_risk_level=descriptor.risk_level,
        )
        status = "delegated" if policy.allowed else "blocked"
        self._trace(episode_id, trace_id, event, descriptor.name, status)
        return DelegationDecision(
            episode_id=episode_id,
            capability=capability,
            agent_name=descriptor.name,
            allowed=policy.allowed,
            requires_human_approval=policy.requires_human_approval,
            reason=policy.reason,
            event_type=event.event_type,
        )

    def _trace(
        self,
        episode_id: str,
        trace_id: str,
        event: DomainEvent,
        agent_name: str,
        status: str,
    ) -> None:
        self.logger.emit(
            WorkflowTrace(
                workflow_id=episode_id,
                episode_id=episode_id,
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
        granted_capabilities=list(descriptor.capabilities),
    )
