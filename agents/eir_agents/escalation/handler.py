"""Human-review dispatch stubs."""

from eir_shared.events import DomainEvent, HumanReviewRequested

from eir_agents.common.types import HandlerResult


def request_human_review(event: DomainEvent, reason: str | None = None) -> HandlerResult:
    review_reason = (
        reason or event.payload.get("reason") or "structured risk signal needs clinician review"
    )
    return HandlerResult(
        summary=f"Human review requested: {review_reason}",
        episode_status="ESCALATED",
        risk_level=str(event.payload.get("risk_level") or "HIGH"),
        review_reason=review_reason,
        next_events=[
            HumanReviewRequested(
                episode_id=event.episode_id,
                reason=review_reason,
                payload={"source_event": event.event_type},
            )
        ],
    )
