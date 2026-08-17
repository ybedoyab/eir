"""Risk stubs. Does not autonomously diagnose."""

from eir_shared.events import DomainEvent, RiskEscalated

from eir_agents.common.types import HandlerResult

PAIN_ESCALATION_THRESHOLD = 7


def assess_response(event: DomainEvent) -> HandlerResult:
    payload = event.payload or {}
    pain_score = int(payload.get("pain_score") or 0)
    reported_issue = bool(payload.get("reported_issue"))
    escalate = reported_issue or pain_score >= PAIN_ESCALATION_THRESHOLD

    if not escalate:
        return HandlerResult(
            summary="No escalation signal in structured follow-up.",
            episode_status="WAITING",
            risk_level="LOW",
        )

    return HandlerResult(
        summary="Structured follow-up contains an escalation signal; requesting human review.",
        risk_level="HIGH",
        next_events=[
            RiskEscalated(
                episode_id=event.episode_id,
                risk_level="HIGH",
                payload={"pain_score": pain_score, "reported_issue": reported_issue},
            )
        ],
    )
