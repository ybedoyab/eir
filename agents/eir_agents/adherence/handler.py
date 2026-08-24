"""Adherence checks against prescribed medications and inventory criticality."""

from __future__ import annotations

from eir_shared.events import DomainEvent, RiskEscalated
from eir_shared.supply import medication_display_name, sku_for_medication_request

from eir_agents.common.types import HandlerResult
from eir_agents.records.fhir_client import FhirClient, LocalFhirClient
from eir_agents.risk.handler import medication_adherence_missed
from eir_agents.supply.store import SupplyStore


def check_task_completion(
    event: DomainEvent,
    *,
    patient_id: str | None = None,
    fhir: FhirClient | None = None,
    supply: SupplyStore | None = None,
) -> HandlerResult:
    fhir = fhir or LocalFhirClient()
    payload = event.payload or {}
    if not medication_adherence_missed(payload):
        return HandlerResult(
            summary="Prescribed medications reported as taken.",
            episode_status="WAITING_FOR_NEXT_FOLLOWUP",
        )

    medications = fhir.get_medications(patient_id) if patient_id else []
    items = supply.list_items() if supply is not None else []
    recorded: list[dict[str, str | bool]] = []
    critical_hits: list[dict[str, str | bool]] = []
    for resource in medications:
        sku = sku_for_medication_request(resource, items) or ""
        item = next((entry for entry in items if entry.sku == sku), None) if sku else None
        entry: dict[str, str | bool] = {
            "sku": sku,
            "name": medication_display_name(resource),
            "critical": bool(item and item.critical),
        }
        recorded.append(entry)
        if entry["critical"]:
            critical_hits.append(entry)

    if not critical_hits:
        names = ", ".join(str(item["name"]) for item in recorded) or "prescribed medication"
        return HandlerResult(
            summary=f"Adherence concern recorded for {names}; no critical medication missed.",
            episode_status="WAITING_FOR_NEXT_FOLLOWUP",
            risk_level="LOW",
        )

    names = ", ".join(str(item["name"]) for item in critical_hits)
    return HandlerResult(
        summary=f"Critical medication not taken: {names}.",
        episode_status="ACTIVE",
        risk_level="HIGH",
        next_events=[
            RiskEscalated(
                episode_id=event.episode_id,
                risk_level="HIGH",
                payload={
                    "reason": "critical_medication_adherence",
                    "medications": critical_hits,
                    "medication_adherence": payload.get("medication_adherence") or "no",
                },
            )
        ],
    )
