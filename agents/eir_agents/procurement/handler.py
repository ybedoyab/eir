"""Procurement: call suppliers, record quotes, draft and commit purchase orders.

The agent may negotiate and draft. It may not commit spend on its own: the
commit step runs only after `purchase_order.approve` clears the safety gate,
which requires a recorded human authorization.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from eir_shared.events import (
    DomainEvent,
    PurchaseOrderApproved,
    PurchaseOrderDrafted,
    RestockScheduled,
    SupplierContacted,
    SupplierQuoteReceived,
    SupplierUnavailable,
)
from eir_shared.supply import (
    PurchaseOrder,
    PurchaseOrderStatus,
    ReplenishmentStatus,
    SupplierQuote,
)

from eir_agents.common.types import HandlerResult
from eir_agents.procurement.conversation import quote_from_conversation
from eir_agents.procurement.voice import (
    SupplierVoiceProvider,
    SyntheticSupplierVoiceProvider,
)
from eir_agents.supply.store import SupplyStore


async def contact_suppliers(
    event: DomainEvent,
    *,
    supply: SupplyStore | None = None,
    voice: SupplierVoiceProvider | None = None,
) -> HandlerResult:
    """Call every vendor that lists the SKU and record what each one says."""
    if supply is None:
        return HandlerResult(summary="supply store unavailable; cannot contact suppliers")
    voice = voice or SyntheticSupplierVoiceProvider()

    case = supply.get_case(event.episode_id)
    if case is None:
        return HandlerResult(summary="replenishment case not found")

    item = supply.get_item(case.sku)
    quantity = case.requested_quantity or (item.suggested_quantity() if item else 0)
    suppliers = supply.list_suppliers(case.sku)

    if not suppliers:
        unavailable = SupplierUnavailable(
            episode_id=case.id,
            payload={"sku": case.sku, "reason": "no supplier lists this SKU"},
        )
        return HandlerResult(
            summary=f"No supplier in the catalog carries {case.sku}.",
            episode_status=ReplenishmentStatus.SOURCING.value,
            review_reason=f"No supplier carries {case.sku}; procurement needs a human buyer.",
            next_events=[unavailable],
        )

    quotes: list[SupplierQuote] = []
    contacted: list[str] = []
    pending_async = False

    for supplier in suppliers:
        entry = supplier.entry_for(case.sku)
        if entry is None:
            continue
        launch = await voice.start_supplier_call(
            to=supplier.phone_e164,
            case_id=case.id,
            supplier_id=supplier.id,
            metadata={
                "sku": case.sku,
                "item_name": case.item_name or (item.name if item else case.sku),
                "unit": item.unit if item else "unit",
                "quantity": quantity,
                "contact_name": supplier.contact_name,
                "supplier_name": supplier.name,
                "unit_price": entry.unit_price,
                "available_units": entry.available_units,
                "lead_time_days": supplier.lead_time_days,
            },
        )
        contacted.append(supplier.id)
        supply.append_event(
            case.id,
            SupplierContacted(
                episode_id=case.id,
                supplier_id=supplier.id,
                payload={
                    "supplier_name": supplier.name,
                    "sku": case.sku,
                    "quantity": quantity,
                    "provider": launch.provider,
                    "call_id": launch.call_id,
                    "correlation_id": launch.correlation_id,
                    "mode": launch.mode,
                    "synthetic": True,
                },
            ),
        )

        if launch.mode == "async":
            # Real PSTN: the vendor answers later. The quote arrives through the
            # authenticated callback, not from this call frame.
            pending_async = True
            continue

        await voice.end_call(launch.call_id)
        parsed = quote_from_conversation(launch.conversation)
        if parsed is None:
            continue
        quotes.append(
            SupplierQuote(
                supplier_id=supplier.id,
                supplier_name=supplier.name,
                sku=case.sku,
                unit_price=parsed.unit_price,
                available_units=parsed.available_units,
                lead_time_days=parsed.lead_time_days or supplier.lead_time_days,
                call_id=launch.call_id,
                provider=launch.provider,
                transcript=list(launch.conversation),
            )
        )

    case.contacted_supplier_ids = contacted
    case.quotes = quotes
    supply.save_case(case)

    if pending_async and not quotes:
        return HandlerResult(
            summary=f"Called {len(contacted)} supplier(s); waiting for quote callbacks.",
            episode_status=ReplenishmentStatus.SOURCING.value,
        )

    if not quotes:
        unavailable = SupplierUnavailable(
            episode_id=case.id,
            payload={
                "sku": case.sku,
                "contacted": contacted,
                "reason": "no supplier quoted an available price",
            },
        )
        return HandlerResult(
            summary=f"Called {len(contacted)} supplier(s) for {case.sku}; none quoted stock.",
            episode_status=ReplenishmentStatus.SOURCING.value,
            review_reason=(
                f"No supplier quoted stock for {case.sku} after "
                f"{len(contacted)} call(s); manual sourcing required."
            ),
            next_events=[unavailable],
        )

    best = case.best_quote(quantity)
    received = SupplierQuoteReceived(
        episode_id=case.id,
        supplier_id=best.supplier_id if best else "",
        payload={
            "sku": case.sku,
            "quantity": quantity,
            "quote_count": len(quotes),
            "quotes": [
                {
                    "supplier_id": quote.supplier_id,
                    "supplier_name": quote.supplier_name,
                    "unit_price": quote.unit_price,
                    "available_units": quote.available_units,
                    "lead_time_days": quote.lead_time_days,
                    "can_fulfill": quote.can_fulfill(quantity),
                }
                for quote in quotes
            ],
            "synthetic": True,
        },
    )
    return HandlerResult(
        summary=(
            f"Collected {len(quotes)} quote(s) for {quantity} units of {case.sku} "
            f"from {len(contacted)} supplier call(s)."
        ),
        episode_status=ReplenishmentStatus.SOURCING.value,
        next_events=[received],
    )


def draft_purchase_order(
    event: DomainEvent,
    *,
    supply: SupplyStore | None = None,
) -> HandlerResult:
    """Pick a supplier and write a draft order. Places nothing."""
    if supply is None:
        return HandlerResult(summary="supply store unavailable; cannot draft order")

    case = supply.get_case(event.episode_id)
    if case is None:
        return HandlerResult(summary="replenishment case not found")

    quantity = case.requested_quantity
    best = case.best_quote(quantity)
    if best is None:
        cheapest = min(case.quotes, key=lambda quote: quote.unit_price, default=None)
        shortfall = (
            f"best offer covers {cheapest.available_units} of {quantity} units"
            if cheapest
            else "no quotes on file"
        )
        unavailable = SupplierUnavailable(
            episode_id=case.id,
            payload={"sku": case.sku, "quantity": quantity, "reason": shortfall},
        )
        return HandlerResult(
            summary=f"No supplier can fulfil {quantity} units of {case.sku}: {shortfall}.",
            episode_status=ReplenishmentStatus.SOURCING.value,
            review_reason=(
                f"Partial supply only for {case.sku} ({shortfall}); "
                "a buyer must decide whether to split the order."
            ),
            next_events=[unavailable],
        )

    order = PurchaseOrder(
        id=f"PO-{uuid4().hex[:8].upper()}",
        case_id=case.id,
        sku=case.sku,
        supplier_id=best.supplier_id,
        supplier_name=best.supplier_name,
        quantity=quantity,
        unit_price=best.unit_price,
        currency=best.currency,
        lead_time_days=best.lead_time_days,
        status=PurchaseOrderStatus.DRAFT,
    )
    case.purchase_order = order
    # The case stays in SOURCING here on purpose. Moving it to AWAITING_APPROVAL
    # is the safety gate's job, and doing it early would pause the workflow before
    # the approval it is waiting for has been created.
    supply.save_case(case)

    undercut = [
        quote
        for quote in case.quotes
        if quote.supplier_id != best.supplier_id
        and quote.unit_price < best.unit_price
        and not quote.can_fulfill(quantity)
    ]
    reasoning = (
        f"{best.supplier_name} at {best.unit_price:.2f} {best.currency}/unit, "
        f"{best.lead_time_days}-day lead time"
    )
    if undercut:
        cheaper = undercut[0]
        reasoning += (
            f". {cheaper.supplier_name} quoted {cheaper.unit_price:.2f} but can only "
            f"ship {cheaper.available_units} of {quantity} units"
        )

    drafted = PurchaseOrderDrafted(
        episode_id=case.id,
        purchase_order_id=order.id,
        payload={
            "purchase_order_id": order.id,
            "sku": case.sku,
            "quantity": quantity,
            "supplier_id": best.supplier_id,
            "supplier_name": best.supplier_name,
            "unit_price": best.unit_price,
            "currency": best.currency,
            "total_cost": order.total_cost,
            "lead_time_days": best.lead_time_days,
            "selection_reason": reasoning,
            "synthetic": True,
        },
    )
    return HandlerResult(
        summary=(
            f"Drafted {order.id}: {quantity} x {case.sku} from {reasoning}. "
            f"Total {order.total_cost:.2f} {order.currency}. Awaiting authorization."
        ),
        episode_status=ReplenishmentStatus.SOURCING.value,
        next_events=[drafted],
    )


def commit_purchase_order(
    event: DomainEvent,
    *,
    supply: SupplyStore | None = None,
) -> HandlerResult:
    """Place the order. Only reachable after a human authorization."""
    if supply is None:
        return HandlerResult(summary="supply store unavailable; cannot place order")

    case = supply.get_case(event.episode_id)
    if case is None:
        return HandlerResult(summary="replenishment case not found")
    order = case.purchase_order
    if order is None:
        return HandlerResult(
            summary="no drafted purchase order to place",
            review_reason="approval granted but no draft order exists on the case",
        )
    if order.status is not PurchaseOrderStatus.DRAFT:
        return HandlerResult(
            summary=f"{order.id} already {order.status.value.lower()}; not placing again.",
            episode_status=ReplenishmentStatus.ORDERED.value,
        )

    now = datetime.now(UTC)
    payload = event.payload or {}
    order.status = PurchaseOrderStatus.PLACED
    order.approved_by = str(payload.get("approved_by") or "operations")
    order.approved_at = now
    order.expected_delivery = now + timedelta(days=order.lead_time_days)
    case.purchase_order = order
    case.status = ReplenishmentStatus.ORDERED
    supply.save_case(case)

    approved = PurchaseOrderApproved(
        episode_id=case.id,
        purchase_order_id=order.id,
        payload={
            "purchase_order_id": order.id,
            "approved_by": order.approved_by,
            "total_cost": order.total_cost,
            "currency": order.currency,
            "supplier_name": order.supplier_name,
            "synthetic": True,
        },
    )
    restock = RestockScheduled(
        episode_id=case.id,
        purchase_order_id=order.id,
        payload={
            "purchase_order_id": order.id,
            "sku": case.sku,
            "quantity": order.quantity,
            "supplier_name": order.supplier_name,
            "expected_delivery": order.expected_delivery.isoformat(),
            "lead_time_days": order.lead_time_days,
            "synthetic": True,
        },
    )
    return HandlerResult(
        summary=(
            f"{order.id} placed with {order.supplier_name} by {order.approved_by}. "
            f"{order.quantity} {case.sku} expected in {order.lead_time_days} day(s)."
        ),
        episode_status=ReplenishmentStatus.ORDERED.value,
        next_events=[approved, restock],
    )
