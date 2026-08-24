"""Patient medications as an operational DTO. Frontend never talks FHIR."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from eir_shared.supply import (
    InventoryItem,
    daily_units_from_medication_request,
    medication_display_name,
    rxnorm_for_medication_request,
    sku_for_medication_request,
)
from pydantic import BaseModel


class PatientMedication(BaseModel):
    sku: str = ""
    name: str
    dose: str = ""
    critical: bool = False
    rxnorm_code: str = ""
    status: str = "active"


class InventoryItemView(InventoryItem):
    patient_count: int = 0


def _dose_text(resource: dict[str, Any]) -> str:
    instructions = resource.get("dosageInstruction") or []
    if instructions and isinstance(instructions[0], dict):
        return str(instructions[0].get("text") or "")
    return ""


def medications_for_patient(
    resources: list[dict[str, Any]],
    items: Iterable[InventoryItem],
) -> list[PatientMedication]:
    catalog = list(items)
    result: list[PatientMedication] = []
    for resource in resources:
        sku = sku_for_medication_request(resource, catalog) or ""
        item = next((entry for entry in catalog if entry.sku == sku), None) if sku else None
        result.append(
            PatientMedication(
                sku=sku,
                name=item.name if item else medication_display_name(resource),
                dose=_dose_text(resource),
                critical=bool(item and item.critical),
                rxnorm_code=(
                    rxnorm_for_medication_request(resource)
                    or (item.rxnorm_code if item else "")
                ),
                status=str(resource.get("status") or "active"),
            )
        )
    return result


def patient_counts_by_sku(
    medications_by_patient: dict[str, list[dict[str, Any]]],
    items: Iterable[InventoryItem],
) -> dict[str, int]:
    catalog = list(items)
    seen: dict[str, set[str]] = {item.sku: set() for item in catalog}
    for patient_id, resources in medications_by_patient.items():
        for resource in resources:
            sku = sku_for_medication_request(resource, catalog)
            if sku and sku in seen:
                seen[sku].add(patient_id)
    return {sku: len(patients) for sku, patients in seen.items()}


def prescription_demand_by_sku(
    medications_by_patient: dict[str, list[dict[str, Any]]],
    items: Iterable[InventoryItem],
) -> dict[str, float]:
    catalog = list(items)
    demand: dict[str, float] = {item.sku: 0.0 for item in catalog}
    for resources in medications_by_patient.values():
        for resource in resources:
            sku = sku_for_medication_request(resource, catalog)
            if not sku or sku not in demand:
                continue
            demand[sku] += daily_units_from_medication_request(resource)
    return demand


def overlay_daily_usage(item: InventoryItem, derived: float) -> InventoryItem:
    """Keep fixture usage as a floor so demo replenishment numbers stay tuned."""
    effective = max(float(item.daily_usage), float(derived or 0.0))
    if effective == item.daily_usage:
        return item
    return item.model_copy(update={"daily_usage": effective})


def medications_by_patient(
    fhir: Any,
    patient_ids: Iterable[str],
) -> dict[str, list[dict[str, Any]]]:
    return {patient_id: fhir.get_medications(patient_id) for patient_id in patient_ids}
