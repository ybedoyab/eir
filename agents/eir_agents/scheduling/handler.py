"""Appointment scheduling with FHIR Appointment stub."""

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
) -> HandlerResult:
    fhir = fhir or LocalFhirClient()
    appointment = {
        "status": "proposed",
        "description": reason,
        "patient_id": patient_id,
        "synthetic": True,
    }
    if patient_id:
        appointment["participant"] = fhir.get_patient(patient_id)

    review = HumanReviewRequested(
        episode_id=episode_id,
        reason=f"Appointment scheduling requires clinician approval: {reason}",
        payload={"appointment": appointment},
    )
    return HandlerResult(
        summary=f"Requested synthetic appointment: {reason}",
        episode_status="WAITING",
        review_reason=review.reason,
        next_events=[review],
    )


def request_appointment(episode_id: str, reason: str) -> dict:
    return {"episode_id": episode_id, "reason": reason, "status": "requested"}
