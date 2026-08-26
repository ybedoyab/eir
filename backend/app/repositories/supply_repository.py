"""Supply persistence: inventory, suppliers, and replenishment cases.

One repository rather than three: the low-stock claim has to read inventory and
write a case atomically, and splitting that across stores would invite a second
purchase order for the same stock-out.
"""

from __future__ import annotations

import threading
from datetime import datetime
from typing import Protocol
from uuid import uuid4

from eir_shared.events import DomainEvent, InventoryLevelLow
from eir_shared.supply import (
    InventoryItem,
    ReplenishmentCase,
    ReplenishmentStatus,
    Supplier,
)

OPEN_CASE_STATUSES = frozenset(
    {
        ReplenishmentStatus.ACTIVE,
        ReplenishmentStatus.SOURCING,
        ReplenishmentStatus.AWAITING_APPROVAL,
        ReplenishmentStatus.BLOCKED,
        ReplenishmentStatus.ORDERED,
    }
)


class SupplyRepository(Protocol):
    def get_item(self, sku: str) -> InventoryItem | None: ...

    def list_items(self) -> list[InventoryItem]: ...

    def save_item(self, item: InventoryItem) -> InventoryItem: ...

    def adjust_stock(self, sku: str, delta: int) -> InventoryItem | None: ...

    def get_supplier(self, supplier_id: str) -> Supplier | None: ...

    def list_suppliers(self, sku: str | None = None) -> list[Supplier]: ...

    def save_supplier(self, supplier: Supplier) -> Supplier: ...

    def get_case(self, case_id: str) -> ReplenishmentCase | None: ...

    def list_cases(self) -> list[ReplenishmentCase]: ...

    def open_case_for_sku(self, sku: str) -> ReplenishmentCase | None: ...

    def save_case(self, case: ReplenishmentCase) -> ReplenishmentCase: ...

    def append_event(self, case_id: str, event: DomainEvent) -> DomainEvent: ...

    def list_events(self, case_id: str) -> list[DomainEvent]: ...

    def claim_replenishment(
        self,
        sku: str,
        *,
        now: datetime,
    ) -> InventoryLevelLow | None: ...


class InMemorySupplyRepository:
    def __init__(self) -> None:
        self._items: dict[str, InventoryItem] = {}
        self._suppliers: dict[str, Supplier] = {}
        self._cases: dict[str, ReplenishmentCase] = {}
        self._events: dict[str, list[DomainEvent]] = {}
        self._lock = threading.Lock()

    def get_item(self, sku: str) -> InventoryItem | None:
        return self._items.get(sku)

    def list_items(self) -> list[InventoryItem]:
        return sorted(self._items.values(), key=lambda item: item.sku)

    def save_item(self, item: InventoryItem) -> InventoryItem:
        self._items[item.sku] = item
        return item

    def adjust_stock(self, sku: str, delta: int) -> InventoryItem | None:
        with self._lock:
            item = self._items.get(sku)
            if item is None:
                return None
            item.on_hand = max(item.on_hand + delta, 0)
            return self.save_item(item)

    def get_supplier(self, supplier_id: str) -> Supplier | None:
        return self._suppliers.get(supplier_id)

    def list_suppliers(self, sku: str | None = None) -> list[Supplier]:
        items = sorted(self._suppliers.values(), key=lambda supplier: supplier.name)
        if sku is None:
            return items
        return [supplier for supplier in items if supplier.entry_for(sku) is not None]

    def save_supplier(self, supplier: Supplier) -> Supplier:
        self._suppliers[supplier.id] = supplier
        return supplier

    def get_case(self, case_id: str) -> ReplenishmentCase | None:
        return self._cases.get(case_id)

    def list_cases(self) -> list[ReplenishmentCase]:
        return sorted(self._cases.values(), key=lambda case: case.opened_at, reverse=True)

    def open_case_for_sku(self, sku: str) -> ReplenishmentCase | None:
        for case in self._cases.values():
            if case.sku == sku and case.status in OPEN_CASE_STATUSES:
                return case
        return None

    def save_case(self, case: ReplenishmentCase) -> ReplenishmentCase:
        self._cases[case.id] = case
        self._events.setdefault(case.id, [])
        return case

    def append_event(self, case_id: str, event: DomainEvent) -> DomainEvent:
        self._events.setdefault(case_id, []).append(event)
        return event

    def list_events(self, case_id: str) -> list[DomainEvent]:
        return list(self._events.get(case_id, []))

    def claim_replenishment(
        self,
        sku: str,
        *,
        now: datetime,
    ) -> InventoryLevelLow | None:
        """Open exactly one replenishment case per stock-out.

        Returns None when stock is healthy or a case is already in flight, so the
        scheduler can run every minute without stacking duplicate orders.
        """
        with self._lock:
            item = self._items.get(sku)
            if item is None or not item.needs_replenishment():
                return None
            if self.open_case_for_sku(sku) is not None:
                return None
            case = ReplenishmentCase(
                id=str(uuid4()),
                sku=item.sku,
                item_name=item.name,
                opened_at=now,
                requested_quantity=item.suggested_quantity(),
                rationale=(
                    f"on hand {item.on_hand} {item.unit} at or below reorder point "
                    f"{item.reorder_point}"
                ),
            )
            self.save_case(case)
            event = InventoryLevelLow(
                episode_id=case.id,
                sku=item.sku,
                occurred_at=now,
                payload={
                    "sku": item.sku,
                    "item_name": item.name,
                    "on_hand": item.on_hand,
                    "reorder_point": item.reorder_point,
                    "target_level": item.target_level,
                    "suggested_quantity": case.requested_quantity,
                    "days_of_cover": item.days_of_cover,
                    "critical": item.critical,
                    "stock_status": item.status.value,
                },
            )
            self._events.setdefault(case.id, []).append(event)
            return event
