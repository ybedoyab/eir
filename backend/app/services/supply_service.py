"""Supply read/write operations for the HTTP layer.

Mirrors RecoveryService: the API persists and publishes, the workflow runtime
runs the agents. Nothing here invokes an agent directly.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from eir_shared.events import DomainEvent, parse_event
from eir_shared.supply import (
    InventoryItem,
    PurchaseOrderStatus,
    ReplenishmentCase,
    ReplenishmentStatus,
    Supplier,
)

from app.repositories.supply_repository import SupplyRepository


class SupplyService:
    def __init__(self, supply: SupplyRepository) -> None:
        self._supply = supply

    def list_items(self) -> list[InventoryItem]:
        return self._supply.list_items()

    def get_item(self, sku: str) -> InventoryItem | None:
        return self._supply.get_item(sku)

    def low_stock_items(self) -> list[InventoryItem]:
        return [item for item in self._supply.list_items() if item.needs_replenishment()]

    def adjust_stock(self, sku: str, delta: int) -> InventoryItem | None:
        item = self._supply.adjust_stock(sku, delta)
        if item is None:
            return None
        item.updated_at = datetime.now(UTC)
        return self._supply.save_item(item)

    def list_suppliers(self, sku: str | None = None) -> list[Supplier]:
        return self._supply.list_suppliers(sku)

    def list_cases(self) -> list[ReplenishmentCase]:
        return self._supply.list_cases()

    def open_cases(self) -> list[ReplenishmentCase]:
        closed = {ReplenishmentStatus.COMPLETED, ReplenishmentStatus.CANCELLED}
        return [case for case in self._supply.list_cases() if case.status not in closed]

    def get_case(self, case_id: str) -> ReplenishmentCase | None:
        return self._supply.get_case(case_id)

    def list_events(self, case_id: str) -> list[DomainEvent]:
        return self._supply.list_events(case_id)

    def append_event(
        self,
        case_id: str,
        event_type: str,
        payload: dict | None = None,
    ) -> DomainEvent | None:
        if self._supply.get_case(case_id) is None:
            return None
        event = parse_event(event_type, episode_id=case_id, payload=payload or {})
        self._supply.append_event(case_id, event)
        return event

    def receive_delivery(self, case_id: str) -> ReplenishmentCase | None:
        """Close the loop: stock arrives, the case completes.

        Only an order that was actually placed can be received; a draft that was
        never approved must not silently top up inventory.
        """
        case = self._supply.get_case(case_id)
        if case is None or case.purchase_order is None:
            return None
        order = case.purchase_order
        if order.status not in {PurchaseOrderStatus.APPROVED, PurchaseOrderStatus.PLACED}:
            return None
        self._supply.adjust_stock(case.sku, order.quantity)
        order.status = PurchaseOrderStatus.RECEIVED
        case.purchase_order = order
        case.status = ReplenishmentStatus.COMPLETED
        case.closed_at = datetime.now(UTC)
        return self._supply.save_case(case)

    def seed(self, inventory_path: Path, suppliers_path: Path) -> None:
        """Load synthetic fixtures. Existing stock levels are never overwritten."""
        if inventory_path.exists():
            raw = json.loads(inventory_path.read_text(encoding="utf-8"))
            for entry in raw.get("items", []):
                item = InventoryItem.model_validate(entry)
                if self._supply.get_item(item.sku) is None:
                    self._supply.save_item(item)
        if suppliers_path.exists():
            raw = json.loads(suppliers_path.read_text(encoding="utf-8"))
            for entry in raw.get("suppliers", []):
                supplier = Supplier.model_validate(entry)
                if self._supply.get_supplier(supplier.id) is None:
                    self._supply.save_supplier(supplier)
