"""Supply workflow runtime.

Deliberately a sibling of WorkflowRuntime rather than a generalization of it.
The two share the registry, the safety gate, the gateway, and the ADK runner,
but they advance unrelated aggregates: one a patient's recovery, the other a
purchase. Keeping them apart means a change to purchasing cannot regress the
recovery path.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from eir_agents.common.types import DelegationDecision, HandlerResult
from eir_agents.runtime.adk_runner import AdkAgentRunner, InvocationContext
from eir_agents.supply.orchestrator import SupplyOrchestrator
from eir_shared.capabilities import BLOCKING_CAPABILITIES
from eir_shared.event_bus import EventBus
from eir_shared.events import (
    SUPPLY_EVENT_TYPES,
    ContentSecurityBlocked,
    DomainEvent,
    parse_event,
)
from eir_shared.observability import StructuredLogger, WorkflowTrace
from eir_shared.supply import ReplenishmentCase, ReplenishmentStatus, SupplyUrgency

from app.repositories.review_repository import HumanReview, ReviewStatus
from app.repositories.supply_repository import SupplyRepository

WORKFLOW = "supply"

# A case in one of these states is waiting on a person or is finished. Only an
# approval may move it; anything else is recorded and dropped.
PAUSED_STATUSES = frozenset(
    {
        ReplenishmentStatus.AWAITING_APPROVAL,
        ReplenishmentStatus.BLOCKED,
        ReplenishmentStatus.ORDERED,
        ReplenishmentStatus.COMPLETED,
        ReplenishmentStatus.CANCELLED,
    }
)


class SupplyWorkflowRuntime:
    def __init__(
        self,
        *,
        event_bus: EventBus,
        supply: SupplyRepository,
        orchestrator: SupplyOrchestrator,
        reviews: Any,
        logger: StructuredLogger,
        adk_runner: AdkAgentRunner | None = None,
        supplier_voice: Any | None = None,
        episode_store: Any | None = None,
        gateway: Any | None = None,
    ) -> None:
        self.event_bus = event_bus
        self.supply = supply
        self.orchestrator = orchestrator
        self.reviews = reviews
        self.logger = logger
        self.adk_runner = adk_runner or AdkAgentRunner(mode="direct")
        self.supplier_voice = supplier_voice
        self.episode_store = episode_store
        self.gateway = gateway
        self._bound = False
        self._depth = 0

    def bind(self) -> None:
        if self._bound:
            return
        for event_type in sorted(SUPPLY_EVENT_TYPES):
            self.event_bus.subscribe(event_type, self.handle)
        self._bound = True

    async def handle(self, event: DomainEvent) -> None:
        if self._depth > 12:
            return
        self._depth += 1
        try:
            await self._handle(event)
        finally:
            self._depth -= 1

    async def _handle(self, event: DomainEvent) -> None:
        case = self.supply.get_case(event.episode_id)
        if case is None:
            return

        if event.event_type == "SupplyApprovalGranted":
            await self._resume_after_approval(case, event)
            return

        if case.status in PAUSED_STATUSES:
            await self._checkpoint(case, event, None)
            return

        if self.gateway is not None:
            gateway_decision = self.gateway.authorize_event(event)
            if not gateway_decision.allowed:
                self._record_security_block(case, event, gateway_decision)
                await self._checkpoint(case, event, None)
                return

        snapshot = case.model_dump(mode="json")
        decision = self.orchestrator.delegate(case.id, event, snapshot)
        await self._checkpoint(case, event, decision)
        if not decision.allowed or not decision.capability:
            return

        if decision.requires_human_approval:
            self._open_pending_approval(case, decision, event)
            return

        await self._execute_decision(case, decision, event)

    async def _execute_decision(
        self,
        case: ReplenishmentCase,
        decision: DelegationDecision,
        event: DomainEvent,
    ) -> None:
        result = await self._invoke(decision, event, case)
        case = self.supply.get_case(case.id) or case
        self._apply_result(case, decision, result)

        blocking = decision.capability in BLOCKING_CAPABILITIES
        if blocking or result.review_reason:
            self._open_review(case, decision, result)
            blocking = True

        for next_event in result.next_events:
            self.supply.append_event(case.id, next_event)
            if blocking:
                continue
            await self.event_bus.publish(next_event)

    async def _invoke(
        self,
        decision: DelegationDecision,
        event: DomainEvent,
        case: ReplenishmentCase,
    ) -> HandlerResult:
        capability = decision.capability
        if capability is None:
            return HandlerResult(summary="no capability delegated")
        ctx = InvocationContext(
            capability=capability,
            event=event,
            patient_id="",
            episode_id=case.id,
            fhir=None,
            voice=None,
            memory=None,
            summarizer=None,
            supply=self.supply,
            supplier_voice=self.supplier_voice,
        )
        return await self.adk_runner.invoke(ctx)

    def _apply_result(
        self,
        case: ReplenishmentCase,
        decision: DelegationDecision,
        result: HandlerResult,
    ) -> None:
        if result.episode_status:
            case.status = ReplenishmentStatus(result.episode_status)
        if result.risk_level:
            try:
                case.urgency = SupplyUrgency(result.risk_level)
            except ValueError:
                pass
        if decision.agent_name and decision.agent_name not in case.assigned_agents:
            case.assigned_agents.append(decision.agent_name)
        self.supply.save_case(case)

    def _open_pending_approval(
        self,
        case: ReplenishmentCase,
        decision: DelegationDecision,
        event: DomainEvent,
    ) -> None:
        """Park the action until a person authorizes it.

        The event that triggered the capability is stored verbatim so the deferred
        run replays exactly what was approved, not a re-derived version of it.
        """
        if self._pending_approval_for(case.id) is not None:
            return
        case.status = ReplenishmentStatus.AWAITING_APPROVAL
        self.supply.save_case(case)
        self.reviews.save(
            HumanReview(
                episode_id=case.id,
                workflow=WORKFLOW,
                reason=decision.reason or "human authorization required before action",
                capability=decision.capability or "",
                agent_name=decision.agent_name or "unknown",
                pending_capability=decision.capability or "",
                pending_event_type=event.event_type,
                pending_event_payload=dict(event.payload),
            )
        )

    def _open_review(
        self,
        case: ReplenishmentCase,
        decision: DelegationDecision,
        result: HandlerResult,
    ) -> None:
        case.status = ReplenishmentStatus.BLOCKED
        self.supply.save_case(case)
        self.reviews.save(
            HumanReview(
                episode_id=case.id,
                workflow=WORKFLOW,
                reason=result.review_reason or decision.reason or "human review required",
                capability=decision.capability or "",
                agent_name=decision.agent_name or "unknown",
            )
        )

    def _pending_approval_for(self, case_id: str) -> HumanReview | None:
        for review in self.reviews.list(pending_only=True, workflow=WORKFLOW):
            if review.episode_id == case_id and review.pending_capability:
                return review
        return None

    async def _resume_after_approval(
        self,
        case: ReplenishmentCase,
        event: DomainEvent,
    ) -> None:
        review_id = getattr(event, "review_id", "") or event.payload.get("review_id")
        review = self.reviews.get(str(review_id)) if review_id else None
        pending_capability = review.pending_capability if review else ""
        pending_event_type = review.pending_event_type if review else ""
        pending_payload = dict(review.pending_event_payload) if review else {}
        pending_agent = review.agent_name if review else "procurement"

        if review is not None:
            review.status = ReviewStatus.RESOLVED
            review.note = getattr(event, "note", "") or event.payload.get("note", "")
            review.resolved_at = datetime.now(UTC)
            review.pending_capability = ""
            review.pending_event_type = ""
            review.pending_event_payload = {}
            self.reviews.save(review)

        if not (pending_capability and pending_event_type):
            await self._checkpoint(case, event, None)
            return

        case.status = ReplenishmentStatus.ACTIVE
        self.supply.save_case(case)
        await self._checkpoint(case, event, None)

        # Carry the approver through so the placed order records who authorized it.
        pending_payload.setdefault("approved_by", event.payload.get("approved_by", ""))
        pending_event = parse_event(
            pending_event_type,
            episode_id=case.id,
            payload=pending_payload,
        )
        decision = DelegationDecision(
            episode_id=case.id,
            capability=pending_capability,
            agent_name=pending_agent,
            allowed=True,
            requires_human_approval=False,
            reason="operations approved deferred purchase",
            event_type=pending_event_type,
        )
        await self._execute_decision(case, decision, pending_event)

    def _record_security_block(
        self,
        case: ReplenishmentCase,
        event: DomainEvent,
        gateway_decision: Any,
    ) -> None:
        from eir_agents.supply.orchestrator import EVENT_TO_CAPABILITY

        blocked = ContentSecurityBlocked(
            episode_id=case.id,
            filter_category=gateway_decision.filter_category,
            adapter=gateway_decision.adapter,
            capability=EVENT_TO_CAPABILITY.get(event.event_type, ""),
            payload={
                "reason": gateway_decision.reason,
                "filter_category": gateway_decision.filter_category,
                "adapter": gateway_decision.adapter,
            },
        )
        self.supply.append_event(case.id, blocked)
        self.logger.emit(
            WorkflowTrace(
                workflow_id=case.id,
                episode_id=case.id,
                trace_id=blocked.event_id,
                agent_name="content_guard",
                event_type="ContentSecurityBlocked",
                status="blocked",
            )
        )
        self.adk_runner.record_security_event(
            episode_id=case.id,
            capability=EVENT_TO_CAPABILITY.get(event.event_type, ""),
            adapter=gateway_decision.adapter,
            category=gateway_decision.filter_category,
            trace_id=blocked.event_id,
        )

    async def _checkpoint(
        self,
        case: ReplenishmentCase,
        event: DomainEvent,
        decision: DelegationDecision | None,
    ) -> None:
        if self.episode_store is None:
            return
        await self.episode_store.save(
            case.id,
            {
                "workflow": WORKFLOW,
                "case": case.model_dump(mode="json"),
                "last_event": event.event_type,
                "last_decision": decision.model_dump() if decision else None,
            },
        )
