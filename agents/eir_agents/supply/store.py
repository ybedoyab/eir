"""Supply persistence protocol.

Handlers depend on this narrow interface, never on a concrete repository, the
same way records handlers depend on FhirClient. The backend repositories satisfy
it structurally.
"""

from __future__ import annotations

from typing import Protocol

from eir_shared.events import DomainEvent
from eir_shared.supply import InventoryItem, ReplenishmentCase, Supplier


class SupplyStore(Protocol):
    def get_item(self, sku: str) -> InventoryItem | None: ...

    def list_items(self) -> list[InventoryItem]: ...

    def get_supplier(self, supplier_id: str) -> Supplier | None: ...

    def list_suppliers(self, sku: str | None = None) -> list[Supplier]: ...

    def get_case(self, case_id: str) -> ReplenishmentCase | None: ...

    def save_case(self, case: ReplenishmentCase) -> ReplenishmentCase: ...

    def append_event(self, case_id: str, event: DomainEvent) -> DomainEvent: ...
