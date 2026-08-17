"""Adherence checks against synthetic medication tasks."""

from __future__ import annotations

from eir_shared.events import AdherenceConcernDetected, DomainEvent

from eir_agents.common.types import HandlerResult
from eir_agents.records.fhir_client import FhirClient, LocalFhirClient


def check_task_completion(
    event: DomainEvent,
    *,
    patient_id: str | None = None,
    fhir: FhirClient | None = None,
) -> HandlerResult:
    fhir = fhir or LocalFhirClient()
    payload = event.payload or {}
    completed = bool(payload.get("completed", True))
    missed_doses = int(payload.get("missed_doses", 0))

    if patient_id:
        medications = fhir.get_medications(patient_id)
        if medications and not completed:
            missed_doses = max(missed_doses, 1)

    if completed and missed_doses == 0:
        return HandlerResult(
            summary="Recovery medication tasks marked complete (synthetic).",
            episode_status="WAITING",
        )

    concern = AdherenceConcernDetected(
        episode_id=event.episode_id,
        payload={"missed_doses": missed_doses, "synthetic": True},
    )
    return HandlerResult(
        summary=f"Adherence concern: {missed_doses} missed dose(s) (synthetic).",
        episode_status="ACTIVE",
        risk_level="MEDIUM",
        next_events=[concern],
    )
