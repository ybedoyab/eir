"""Local agent runtime adapter.

The HTTP layer only persists and publishes. This subscriber runs the
capability-based workflow. Agents are not imported from API route files.

TODO: replace with Agent Runtime / Agent Gateway.
"""

from __future__ import annotations

from datetime import UTC, datetime

from eir_agents.adherence.handler import check_task_completion
from eir_agents.common.types import DelegationDecision, HandlerResult
from eir_agents.escalation.handler import request_human_review
from eir_agents.orchestrator.handler import RecoveryOrchestrator
from eir_agents.outreach.handler import handle_follow_up
from eir_agents.outreach.llm import FollowUpSummarizer, TemplateFollowUpSummarizer
from eir_agents.outreach.voice import MockVoiceProvider
from eir_agents.records.fhir_client import FhirClient, LocalFhirClient
from eir_agents.risk.handler import assess_response
from eir_agents.scheduling.handler import request_appointment
from eir_shared.capabilities import BLOCKING_CAPABILITIES, Capability
from eir_shared.event_bus import EventBus
from eir_shared.events import EVENT_TYPE_MAP, DomainEvent
from eir_shared.memory import AgentMemory, EpisodeStore
from eir_shared.observability import StructuredLogger

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
        self.voice = MockVoiceProvider()
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
            await self._checkpoint(episode, event, None)
            return

        if event.event_type == "ClinicianResolved":
            await self._resume_after_review(episode, event)
            return

        if event.event_type in {"RecoveryEpisodeStarted", "HumanReviewRequested"}:
            await self._checkpoint(episode, event, None)
            return

        decision = self.orchestrator.delegate(event.episode_id, event)
        await self._checkpoint(episode, event, decision)
        if not decision.allowed or not decision.capability:
            return

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
        if capability == Capability.PATIENT_CONTACT:
            return await handle_follow_up(
                event,
                patient_id=episode.patient_id,
                fhir=self.fhir,
                voice=self.voice,
                memory=self.agent_memory,
                summarizer=self.summarizer,
            )
        if capability == Capability.RISK_ASSESS:
            return assess_response(event)
        if capability == Capability.ESCALATION_REQUEST:
            return request_human_review(event)
        if capability == Capability.ADHERENCE_CHECK:
            return check_task_completion(event)
        if capability == Capability.APPOINTMENT_SCHEDULE:
            stub = request_appointment(episode.id, "synthetic follow-up visit")
            return HandlerResult(summary=str(stub), episode_status="WAITING")
        return HandlerResult(summary=f"no handler for {capability}")

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
        episode.status = EpisodeStatus.ACTIVE
        self.episodes.save(episode)
        review_id = getattr(event, "review_id", "") or event.payload.get("review_id")
        if review_id:
            review = self.reviews.get(str(review_id))
            if review is not None:
                review.status = ReviewStatus.RESOLVED
                review.note = getattr(event, "note", "") or event.payload.get("note", "")
                review.resolved_at = datetime.now(UTC)
                self.reviews.save(review)
        await self._checkpoint(episode, event, None)

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
