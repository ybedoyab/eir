"""Risk assessment with recovery uncertainty signals."""

from __future__ import annotations

from typing import Any

from eir_shared.events import AdherenceConcernDetected, DomainEvent, RiskEscalated

from eir_agents.common.types import HandlerResult

PAIN_ESCALATION_THRESHOLD = 7


def medication_adherence_missed(payload: dict[str, Any]) -> bool:
    """True when the patient reported not taking prescribed medication."""
    medications = payload.get("medications")
    if isinstance(medications, list) and medications:
        return any(
            isinstance(item, dict) and item.get("taken") is False for item in medications
        )
    return str(payload.get("medication_adherence") or "") == "no"


def assess_response(event: DomainEvent) -> HandlerResult:
    payload = event.payload or {}
    pain_score_raw = payload.get("pain_score")
    pain_score = int(pain_score_raw) if pain_score_raw is not None else None
    reported_issue = bool(payload.get("reported_issue"))
    missing_pain = pain_score is None
    uncertain = missing_pain or payload.get("synthetic") is True
    missed_adherence = medication_adherence_missed(payload)

    escalate = reported_issue or (
        pain_score is not None and pain_score >= PAIN_ESCALATION_THRESHOLD
    )

    next_events: list[DomainEvent] = []
    if missed_adherence:
        next_events.append(
            AdherenceConcernDetected(
                episode_id=event.episode_id,
                payload={
                    "medication_adherence": payload.get("medication_adherence") or "no",
                    "medications": payload.get("medications") or [],
                    "pain_score": pain_score,
                    "synthetic": payload.get("synthetic"),
                },
            )
        )

    if not escalate:
        summary = "No escalation signal in structured follow-up."
        if missed_adherence:
            summary = "Medication adherence concern recorded for specialist review."
        if uncertain and not missed_adherence:
            summary += " Recovery uncertainty: synthetic or incomplete structured data."
        return HandlerResult(
            summary=summary,
            episode_status="WAITING_FOR_NEXT_FOLLOWUP",
            risk_level="LOW",
            next_events=next_events,
        )

    uncertainty_note = ""
    if uncertain:
        uncertainty_note = " Recovery uncertainty: clinician review recommended."

    next_events.append(
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
    )
    return HandlerResult(
        summary=(
            "Structured follow-up contains an escalation signal; requesting human review."
            + uncertainty_note
        ),
        risk_level="HIGH",
        next_events=next_events,
    )
