"""Local agent runtime adapter.

The HTTP layer only persists and publishes. This subscriber runs the
capability-based workflow. Agents are not imported from API route files.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from eir_agents.common.types import DelegationDecision, HandlerResult
from eir_agents.orchestrator.handler import RecoveryOrchestrator
from eir_agents.outreach.llm import FollowUpSummarizer, TemplateFollowUpSummarizer
from eir_agents.outreach.voice import MockVoiceProvider, VoiceProvider
from eir_agents.records.fhir_client import FhirClient, LocalFhirClient
from eir_agents.runtime.adk_runner import AdkAgentRunner, InvocationContext
from eir_shared.capabilities import BLOCKING_CAPABILITIES
from eir_shared.event_bus import EventBus
from eir_shared.events import EVENT_TYPE_MAP, ContentSecurityBlocked, DomainEvent, parse_event
from eir_shared.memory import AgentMemory, EpisodeStore
from eir_shared.observability import StructuredLogger, WorkflowTrace

from app.domain.recovery.models import EpisodeStatus, RecoveryEpisode, RiskLevel
from app.repositories.recovery_repository import RecoveryEpisodeRepository
from app.repositories.review_repository import HumanReview, InMemoryReviewRepository, ReviewStatus


class WorkflowRuntime:
    def __init__(
        self,
        *,
        event_bus: EventBus,
        episodes: RecoveryEpisodeRepository,
        episode_store: EpisodeStore,
        agent_memory: AgentMemory,
        reviews: InMemoryReviewRepository,
        orchestrator: RecoveryOrchestrator,
        logger: StructuredLogger,
        fhir: FhirClient | None = None,
        summarizer: FollowUpSummarizer | None = None,
        adk_runner: AdkAgentRunner | None = None,
        voice: VoiceProvider | None = None,
        gateway: Any | None = None,
    ) -> None:
        self.event_bus = event_bus
        self.episodes = episodes
        self.episode_store = episode_store
        self.agent_memory = agent_memory
        self.reviews = reviews
        self.orchestrator = orchestrator
        self.logger = logger
        self.fhir = fhir or LocalFhirClient()
        self.summarizer = summarizer or TemplateFollowUpSummarizer()
        self.voice = voice or MockVoiceProvider()
        self.adk_runner = adk_runner or AdkAgentRunner(mode="direct")
        self.gateway = gateway
        self._bound = False
        self._depth = 0

    def bind(self) -> None:
        if self._bound:
            return
        for event_type in EVENT_TYPE_MAP:
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
        episode = self.episodes.get(event.episode_id)
        if episode is None:
            return

        paused = episode.status in {
            EpisodeStatus.ESCALATED,
            EpisodeStatus.COMPLETED,
            EpisodeStatus.CANCELLED,
        }
        if paused and event.event_type not in {
            "ClinicianResolved",
            "RiskEscalated",
            "HumanReviewRequested",
        }:
            if event.event_type == "PatientResponded":
                gateway = getattr(self, "gateway", None)
                if gateway is not None:
                    gateway_decision = gateway.authorize_event(event)
                    if not gateway_decision.allowed:
                        await self._record_security_block(episode, event, gateway_decision)
            await self._checkpoint(episode, event, None)
            return

        if event.event_type == "ClinicianResolved":
            await self._resume_after_review(episode, event)
            return

        if event.event_type in {"RecoveryEpisodeStarted", "HumanReviewRequested"}:
            await self._checkpoint(episode, event, None)
            return

        gateway = getattr(self, "gateway", None)
        if gateway is not None:
            gateway_decision = gateway.authorize_event(event)
            if not gateway_decision.allowed:
                await self._record_security_block(episode, event, gateway_decision)
                await self._checkpoint(episode, event, None)
                return

        episode_snapshot = episode.model_dump(mode="json")
        decision = self.orchestrator.delegate(event.episode_id, event, episode_snapshot)
        await self._checkpoint(episode, event, decision)
        if not decision.allowed or not decision.capability:
            return

        if decision.requires_human_approval:
            self._open_pending_approval(episode, decision, event)
            return

        await self._execute_decision(episode, decision, event)

    async def _record_security_block(
        self,
        episode: RecoveryEpisode,
        event: DomainEvent,
        gateway_decision: Any,
    ) -> None:
        from eir_agents.orchestrator.handler import EVENT_TO_CAPABILITY

        blocked = ContentSecurityBlocked(
            episode_id=episode.id,
            filter_category=gateway_decision.filter_category,
            adapter=gateway_decision.adapter,
            capability=EVENT_TO_CAPABILITY.get(event.event_type, ""),
            payload={
                "reason": gateway_decision.reason,
                "filter_category": gateway_decision.filter_category,
                "adapter": gateway_decision.adapter,
            },
        )
        self.episodes.append_event(episode.id, blocked)
        self.logger.emit(
            WorkflowTrace(
                workflow_id=episode.id,
                episode_id=episode.id,
                trace_id=blocked.event_id,
                agent_name="content_guard",
                event_type="ContentSecurityBlocked",
                status="blocked",
            )
        )
        self.adk_runner.record_security_event(
            episode_id=episode.id,
            capability=EVENT_TO_CAPABILITY.get(event.event_type, ""),
            adapter=gateway_decision.adapter,
            category=gateway_decision.filter_category,
            trace_id=blocked.event_id,
        )

    async def _execute_decision(
        self,
        episode: RecoveryEpisode,
        decision: DelegationDecision,
        event: DomainEvent,
    ) -> None:
        result = await self._invoke(decision, event, episode)
        self._apply_result(episode, decision, result)

        blocking = decision.capability in BLOCKING_CAPABILITIES
        if blocking or result.review_reason:
            self._open_review(episode, decision, result)
            blocking = True

        for next_event in result.next_events:
            self.episodes.append_event(episode.id, next_event)
            if blocking and next_event.event_type != "HumanReviewRequested":
                continue
            await self.event_bus.publish(next_event)

    async def _invoke(
        self,
        decision: DelegationDecision,
        event: DomainEvent,
        episode: RecoveryEpisode,
    ) -> HandlerResult:
        capability = decision.capability
        if capability is None:
            return HandlerResult(summary="no capability delegated")
        ctx = InvocationContext(
            capability=capability,
            event=event,
            patient_id=episode.patient_id,
            episode_id=episode.id,
            fhir=self.fhir,
            voice=self.voice,
            memory=self.agent_memory,
            summarizer=self.summarizer,
        )
        return await self.adk_runner.invoke(ctx)

    def _open_pending_approval(
        self,
        episode: RecoveryEpisode,
        decision: DelegationDecision,
        event: DomainEvent,
    ) -> None:
        episode.status = EpisodeStatus.ESCALATED
        self.episodes.save(episode)
        self.reviews.save(
            HumanReview(
                episode_id=episode.id,
                reason=decision.reason or "human approval required before action",
                capability=decision.capability or "",
                agent_name=decision.agent_name or "unknown",
                pending_capability=decision.capability or "",
                pending_event_type=event.event_type,
                pending_event_payload=dict(event.payload),
            )
        )

    def _apply_result(
        self,
        episode: RecoveryEpisode,
        decision: DelegationDecision,
        result: HandlerResult,
    ) -> None:
        if result.episode_status:
            episode.status = EpisodeStatus(result.episode_status)
        if result.risk_level:
            episode.risk_level = RiskLevel(result.risk_level)
        if decision.agent_name and decision.agent_name not in episode.assigned_agents:
            episode.assigned_agents.append(decision.agent_name)
        self.episodes.save(episode)

    def _open_review(
        self,
        episode: RecoveryEpisode,
        decision: DelegationDecision,
        result: HandlerResult,
    ) -> None:
        episode.status = EpisodeStatus.ESCALATED
        self.episodes.save(episode)
        self.reviews.save(
            HumanReview(
                episode_id=episode.id,
                reason=result.review_reason or decision.reason or "human review required",
                capability=decision.capability or "",
                agent_name=decision.agent_name or "unknown",
            )
        )

    async def _resume_after_review(self, episode: RecoveryEpisode, event: DomainEvent) -> None:
        review_id = getattr(event, "review_id", "") or event.payload.get("review_id")
        review = self.reviews.get(str(review_id)) if review_id else None
        pending_capability = review.pending_capability if review else ""
        pending_event_type = review.pending_event_type if review else ""
        pending_payload = dict(review.pending_event_payload) if review else {}
        pending_agent = review.agent_name if review else "unknown"

        episode.status = EpisodeStatus.ACTIVE
        self.episodes.save(episode)
        if review is not None:
            review.status = ReviewStatus.RESOLVED
            review.note = getattr(event, "note", "") or event.payload.get("note", "")
            review.resolved_at = datetime.now(UTC)
            review.pending_capability = ""
            review.pending_event_type = ""
            review.pending_event_payload = {}
            self.reviews.save(review)
        await self._checkpoint(episode, event, None)

        if pending_capability and pending_event_type:
            pending_event = parse_event(
                pending_event_type,
                episode_id=episode.id,
                payload=pending_payload,
            )
            decision = DelegationDecision(
                episode_id=episode.id,
                capability=pending_capability,
                agent_name=pending_agent,
                allowed=True,
                requires_human_approval=False,
                reason="clinician approved deferred action",
                event_type=pending_event_type,
            )
            await self._execute_decision(episode, decision, pending_event)

    async def _checkpoint(
        self,
        episode: RecoveryEpisode,
        event: DomainEvent,
        decision: DelegationDecision | None,
    ) -> None:
        await self.episode_store.save(
            episode.id,
            {
                "episode": episode.model_dump(mode="json"),
                "last_event": event.event_type,
                "last_decision": decision.model_dump() if decision else None,
            },
        )
