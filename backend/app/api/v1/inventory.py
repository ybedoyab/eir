"""Pharmacy inventory read/write. Stock is operational data, never PHI."""

from typing import Annotated, Any

from eir_shared.auth import DemoRole
from eir_shared.supply import InventoryItem, Supplier
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.deps.auth import require_role
from app.core.deps import get_container
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


@router.get("", response_model=list[InventoryItem])
def list_inventory(_claims: AdminOrClinician) -> list[InventoryItem]:
    return _service().list_items()


@router.get("/low-stock", response_model=list[InventoryItem])
def list_low_stock(_claims: AdminOrClinician) -> list[InventoryItem]:
    return _service().low_stock_items()


@router.get("/suppliers", response_model=list[Supplier])
def list_suppliers(_claims: AdminOrClinician, sku: str | None = None) -> list[Supplier]:
    return _service().list_suppliers(sku)


@router.get("/{sku}", response_model=InventoryItem)
def get_inventory_item(sku: str, _claims: AdminOrClinician) -> InventoryItem:
    item = _service().get_item(sku)
    if item is None:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    return item


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
