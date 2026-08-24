"""Procurement and inventory handlers in isolation.

Uses a hand-rolled store rather than the backend repository: these handlers must
work against the SupplyStore protocol, not against one concrete implementation.
"""

import asyncio

from eir_agents.inventory.handler import forecast_replenishment
from eir_agents.procurement.conversation import quote_from_conversation
from eir_agents.procurement.handler import (
    commit_purchase_order,
    contact_suppliers,
    draft_purchase_order,
)
from eir_agents.procurement.voice import (
    SyntheticSupplierVoiceProvider,
    UnavailableSupplierVoiceProvider,
)
from eir_shared.events import (
    DomainEvent,
    InventoryLevelLow,
    PurchaseOrderDrafted,
    ReplenishmentRequested,
    SupplierQuoteReceived,
)
from eir_shared.supply import (
    InventoryItem,
    PurchaseOrderStatus,
    ReplenishmentCase,
    ReplenishmentStatus,
    Supplier,
    SupplierCatalogEntry,
)

SKU = "MED-TEST-01"


class FakeSupplyStore:
    def __init__(self, item: InventoryItem, suppliers: list[Supplier]) -> None:
        self._item = item
        self._suppliers = {supplier.id: supplier for supplier in suppliers}
        self.case = ReplenishmentCase(id="case-1", sku=item.sku, item_name=item.name)
        self.events: list[DomainEvent] = []

    def get_item(self, sku: str) -> InventoryItem | None:
        return self._item if sku == self._item.sku else None

    def get_supplier(self, supplier_id: str) -> Supplier | None:
        return self._suppliers.get(supplier_id)

    def list_suppliers(self, sku: str | None = None) -> list[Supplier]:
        items = list(self._suppliers.values())
        if sku is None:
            return items
        return [item for item in items if item.entry_for(sku) is not None]

    def get_case(self, case_id: str) -> ReplenishmentCase | None:
        return self.case if case_id == self.case.id else None

    def save_case(self, case: ReplenishmentCase) -> ReplenishmentCase:
        self.case = case
        return case

    def append_event(self, case_id: str, event: DomainEvent) -> DomainEvent:
        self.events.append(event)
        return event


def _item(**overrides) -> InventoryItem:
    defaults = {
        "sku": SKU,
        "name": "Test medication",
        "unit": "vial",
        "on_hand": 20,
        "reorder_point": 100,
        "target_level": 300,
        "daily_usage": 10.0,
        "critical": False,
    }
    defaults.update(overrides)
    return InventoryItem(**defaults)


def _supplier(supplier_id: str, price: float, available: int, lead: int = 3) -> Supplier:
    return Supplier(
        id=supplier_id,
        name=f"Supplier {supplier_id}",
        contact_name="Sam",
        phone_e164="+15550100999",
        lead_time_days=lead,
        catalog=[
            SupplierCatalogEntry(sku=SKU, unit_price=price, available_units=available)
        ],
    )


def _store(item: InventoryItem | None = None, suppliers: list[Supplier] | None = None):
    return FakeSupplyStore(
        item or _item(),
        suppliers if suppliers is not None else [_supplier("s1", 5.0, 1000)],
    )


def test_forecast_sizes_to_target_when_that_is_larger() -> None:
    store = _store()
    result = forecast_replenishment(InventoryLevelLow(episode_id="case-1", sku=SKU), supply=store)

    # target 300 - on hand 20 = 280, versus 10/day * (3 lead + 7 safety) = 100.
    assert store.case.requested_quantity == 280
    assert result.episode_status == ReplenishmentStatus.SOURCING.value


def test_forecast_covers_the_delivery_window_when_target_is_too_small() -> None:
    store = _store(_item(on_hand=20, target_level=40, daily_usage=30.0))
    forecast_replenishment(InventoryLevelLow(episode_id="case-1", sku=SKU), supply=store)

    # 30/day * (3 + 7) = 300 beats the 20-unit gap to target.
    assert store.case.requested_quantity == 300


def test_forecast_flags_a_critical_medication_running_out_before_delivery() -> None:
    store = _store(_item(on_hand=10, daily_usage=10.0, critical=True))
    result = forecast_replenishment(InventoryLevelLow(episode_id="case-1", sku=SKU), supply=store)

    assert store.case.urgency.value == "CRITICAL"
    assert result.risk_level == "CRITICAL"


def test_unreachable_suppliers_block_the_case_for_a_human() -> None:
    store = _store()
    store.case.requested_quantity = 100
    result = asyncio.run(
        contact_suppliers(
            ReplenishmentRequested(episode_id="case-1", sku=SKU),
            supply=store,
            voice=UnavailableSupplierVoiceProvider(),
        )
    )

    assert result.review_reason, "an unanswered sourcing round needs a human"
    assert [event.event_type for event in result.next_events] == ["SupplierUnavailable"]
    assert store.case.quotes == []


def test_no_supplier_carries_the_sku() -> None:
    store = _store(suppliers=[])
    result = asyncio.run(
        contact_suppliers(ReplenishmentRequested(episode_id="case-1", sku=SKU), supply=store)
    )

    assert result.review_reason
    assert [event.event_type for event in result.next_events] == ["SupplierUnavailable"]


def test_partial_availability_is_escalated_rather_than_split_silently() -> None:
    store = _store(suppliers=[_supplier("s1", 5.0, 40)])
    store.case.requested_quantity = 100
    asyncio.run(
        contact_suppliers(
            ReplenishmentRequested(episode_id="case-1", sku=SKU),
            supply=store,
            voice=SyntheticSupplierVoiceProvider(),
        )
    )
    result = draft_purchase_order(SupplierQuoteReceived(episode_id="case-1"), supply=store)

    assert store.case.purchase_order is None
    assert result.review_reason
    assert "40 of 100" in result.review_reason


def test_draft_leaves_the_order_unplaced() -> None:
    store = _store(suppliers=[_supplier("s1", 5.0, 1000)])
    store.case.requested_quantity = 100
    asyncio.run(
        contact_suppliers(ReplenishmentRequested(episode_id="case-1", sku=SKU), supply=store)
    )
    result = draft_purchase_order(SupplierQuoteReceived(episode_id="case-1"), supply=store)

    order = store.case.purchase_order
    assert order is not None
    assert order.status is PurchaseOrderStatus.DRAFT
    assert order.approved_by == ""
    assert order.total_cost == 500.0
    # The gate, not the handler, decides the case is waiting on a person: the
    # handler must not park it in AWAITING_APPROVAL itself.
    assert result.episode_status == ReplenishmentStatus.SOURCING.value


def test_commit_records_the_approver_and_places_the_order() -> None:
    store = _store(suppliers=[_supplier("s1", 5.0, 1000, lead=4)])
    store.case.requested_quantity = 100
    asyncio.run(
        contact_suppliers(ReplenishmentRequested(episode_id="case-1", sku=SKU), supply=store)
    )
    draft_purchase_order(SupplierQuoteReceived(episode_id="case-1"), supply=store)

    result = commit_purchase_order(
        PurchaseOrderDrafted(episode_id="case-1", payload={"approved_by": "ops.admin"}),
        supply=store,
    )

    order = store.case.purchase_order
    assert order.status is PurchaseOrderStatus.PLACED
    assert order.approved_by == "ops.admin"
    assert store.case.status is ReplenishmentStatus.ORDERED
    assert [event.event_type for event in result.next_events] == [
        "PurchaseOrderApproved",
        "RestockScheduled",
    ]


def test_commit_will_not_place_the_same_order_twice() -> None:
    store = _store(suppliers=[_supplier("s1", 5.0, 1000)])
    store.case.requested_quantity = 100
    asyncio.run(
        contact_suppliers(ReplenishmentRequested(episode_id="case-1", sku=SKU), supply=store)
    )
    draft_purchase_order(SupplierQuoteReceived(episode_id="case-1"), supply=store)
    commit_purchase_order(PurchaseOrderDrafted(episode_id="case-1"), supply=store)

    replay = commit_purchase_order(PurchaseOrderDrafted(episode_id="case-1"), supply=store)
    assert replay.next_events == []
    assert "not placing again" in replay.summary


def test_commit_without_a_draft_asks_for_review() -> None:
    store = _store()
    result = commit_purchase_order(PurchaseOrderDrafted(episode_id="case-1"), supply=store)
    assert result.review_reason


def test_handlers_degrade_safely_without_a_store() -> None:
    assert forecast_replenishment(InventoryLevelLow(episode_id="case-1")).next_events == []
    assert draft_purchase_order(SupplierQuoteReceived(episode_id="case-1")).next_events == []
    assert commit_purchase_order(PurchaseOrderDrafted(episode_id="case-1")).next_events == []


def test_quote_parser_reads_only_the_supplier_turn() -> None:
    conversation = [
        {"role": "agent", "text": "We need 900 units at 1.00 dollars, ideally in 1 day."},
        {"role": "supplier", "text": "We can ship 250 units at 3.75 USD per unit in 6 days."},
    ]
    quote = quote_from_conversation(conversation)
    assert quote.available_units == 250
    assert quote.unit_price == 3.75
    assert quote.lead_time_days == 6


def test_quote_parser_refuses_to_guess() -> None:
    assert quote_from_conversation([]) is None
    vague = [{"role": "supplier", "text": "Let me get back to you."}]
    assert quote_from_conversation(vague) is None
    assert (
        quote_from_conversation([{"role": "supplier", "text": "We are out of stock today."}])
        is None
    )
