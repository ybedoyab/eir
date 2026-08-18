"""Appointment scheduling with FHIR Appointment lifecycle."""

from __future__ import annotations

from eir_shared.events import AppointmentRequested, HumanReviewRequested

from eir_agents.common.types import HandlerResult
from eir_agents.records.fhir_client import FhirClient, LocalFhirClient


def schedule_appointment(
    event: AppointmentRequested | None,
    *,
    episode_id: str,
    reason: str,
    patient_id: str | None = None,
    fhir: FhirClient | None = None,
    recovery_context: bool = True,
) -> HandlerResult:
    fhir = fhir or LocalFhirClient()
    appointment = fhir.create_appointment(
        patient_id=patient_id or "unknown",
        episode_id=episode_id,
        reason=reason,
    )

    if recovery_context:
        review = HumanReviewRequested(
            episode_id=episode_id,
            reason=f"Recovery follow-up appointment requires clinician approval: {reason}",
            payload={"appointment": appointment},
        )
        return HandlerResult(
            summary=f"Requested recovery follow-up appointment: {reason}",
            episode_status="WAITING_FOR_NEXT_FOLLOWUP",
            review_reason=review.reason,
            next_events=[review],
        )

    return HandlerResult(
        summary=f"Booked routine appointment: {reason}",
        episode_status="WAITING_FOR_NEXT_FOLLOWUP",
        next_events=[],
    )
