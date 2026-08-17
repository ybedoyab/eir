"""Risk assessment with recovery uncertainty signals."""

from __future__ import annotations

from eir_shared.events import DomainEvent, RiskEscalated

from eir_agents.common.types import HandlerResult

PAIN_ESCALATION_THRESHOLD = 7


def assess_response(event: DomainEvent) -> HandlerResult:
    payload = event.payload or {}
    pain_score_raw = payload.get("pain_score")
    pain_score = int(pain_score_raw) if pain_score_raw is not None else None
    reported_issue = bool(payload.get("reported_issue"))
    missing_pain = pain_score is None
    uncertain = missing_pain or payload.get("synthetic") is True

    escalate = reported_issue or (
        pain_score is not None and pain_score >= PAIN_ESCALATION_THRESHOLD
    )

    if not escalate:
        summary = "No escalation signal in structured follow-up."
        if uncertain:
            summary += " Recovery uncertainty: synthetic or incomplete structured data."
        return HandlerResult(
            summary=summary,
            episode_status="WAITING_FOR_NEXT_FOLLOWUP",
            risk_level="LOW",
        )

    uncertainty_note = ""
    if uncertain:
        uncertainty_note = " Recovery uncertainty: clinician review recommended."

    return HandlerResult(
        summary=(
            "Structured follow-up contains an escalation signal; requesting human review."
            + uncertainty_note
        ),
        risk_level="HIGH",
        next_events=[
            RiskEscalated(
                episode_id=event.episode_id,
                risk_level="HIGH",
                payload={
                    "pain_score": pain_score,
                    "reported_issue": reported_issue,
                    "uncertain": uncertain,
                    "missing_pain": missing_pain,
                },
            )
        ],
    )
