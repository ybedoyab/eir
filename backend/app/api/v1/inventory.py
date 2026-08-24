"""Pharmacy inventory read/write. Stock is operational data, never PHI."""

from typing import Annotated, Any

from eir_shared.auth import DemoRole
from eir_shared.supply import InventoryItem, Supplier
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.deps.auth import require_role
from app.core.deps import get_container
from app.services.medications import (
    InventoryItemView,
    medications_by_patient,
    overlay_daily_usage,
    patient_counts_by_sku,
    prescription_demand_by_sku,
)
from app.services.supply_service import SupplyService

router = APIRouter()

AdminOrClinician = Annotated[
    dict[str, Any],
    Depends(require_role(DemoRole.OPERATIONS_ADMIN, DemoRole.CLINICIAN)),
]
OperationsAdmin = Annotated[
    dict[str, Any],
    Depends(require_role(DemoRole.OPERATIONS_ADMIN)),
]


class AdjustStockRequest(BaseModel):
    delta: int = Field(description="Signed change in units. Negative dispenses stock.")
    reason: str = ""


def _service() -> SupplyService:
    return SupplyService(get_container().supply)


def _inventory_views() -> list[InventoryItemView]:
    container = get_container()
    items = _service().list_items()
    patient_ids = [patient.id for patient in container.patients.list()]
    by_patient = medications_by_patient(container.fhir, patient_ids)
    counts = patient_counts_by_sku(by_patient, items)
    demand = prescription_demand_by_sku(by_patient, items)
    views: list[InventoryItemView] = []
    for item in items:
        overlaid = overlay_daily_usage(item, demand.get(item.sku, 0.0))
        payload = overlaid.model_dump(exclude={"status", "days_of_cover"})
        views.append(
            InventoryItemView.model_validate(
                {**payload, "patient_count": counts.get(item.sku, 0)}
            )
        )
    return views


@router.get("", response_model=list[InventoryItemView])
def list_inventory(_claims: AdminOrClinician) -> list[InventoryItemView]:
    return _inventory_views()


@router.get("/low-stock", response_model=list[InventoryItemView])
def list_low_stock(_claims: AdminOrClinician) -> list[InventoryItemView]:
    return [item for item in _inventory_views() if item.needs_replenishment()]


@router.get("/suppliers", response_model=list[Supplier])
def list_suppliers(_claims: AdminOrClinician, sku: str | None = None) -> list[Supplier]:
    return _service().list_suppliers(sku)


@router.get("/{sku}", response_model=InventoryItemView)
def get_inventory_item(sku: str, _claims: AdminOrClinician) -> InventoryItemView:
    for item in _inventory_views():
        if item.sku == sku:
            return item
    raise HTTPException(status_code=404, detail="Inventory item not found")


@router.post("/{sku}/adjust", response_model=InventoryItem)
def adjust_stock(
    sku: str,
    body: AdjustStockRequest,
    _claims: OperationsAdmin,
) -> InventoryItem:
    """Record dispensing or a manual correction.

    Crossing the reorder point does not open a case here. Cloud Scheduler calls
    the stock monitor, which owns that claim, so there is exactly one path that
    can start a purchase.
    """
    item = _service().adjust_stock(sku, body.delta)
    if item is None:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    return item
