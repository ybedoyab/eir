"""Replenishment sizing. Deterministic arithmetic, no purchasing authority."""

from __future__ import annotations

import math

from eir_shared.events import DomainEvent, ReplenishmentRequested
from eir_shared.supply import ReplenishmentStatus, SupplyUrgency

from eir_agents.common.types import HandlerResult
from eir_agents.supply.store import SupplyStore

SAFETY_STOCK_DAYS = 7


def forecast_replenishment(
    event: DomainEvent,
    *,
    supply: SupplyStore | None = None,
) -> HandlerResult:
    if supply is None:
        return HandlerResult(summary="supply store unavailable; cannot size replenishment")

    case = supply.get_case(event.episode_id)
    if case is None:
        return HandlerResult(summary="replenishment case not found")

    item = supply.get_item(case.sku)
    if item is None:
        return HandlerResult(
            summary=f"inventory item {case.sku} not found",
            review_reason=f"replenishment opened for unknown SKU {case.sku}",
        )

    suppliers = supply.list_suppliers(case.sku)
    lead_time_days = max((supplier.lead_time_days for supplier in suppliers), default=3)

    # Order back to target, but never less than the stock consumed while the
    # delivery is in transit plus a safety buffer.
    to_target = item.suggested_quantity()
    in_transit_need = math.ceil(item.daily_usage * (lead_time_days + SAFETY_STOCK_DAYS))
    quantity = max(to_target, in_transit_need, 1)

    cover = item.days_of_cover
    urgency = SupplyUrgency.NORMAL
    if cover is not None and cover < lead_time_days:
        urgency = SupplyUrgency.CRITICAL if item.critical else SupplyUrgency.HIGH
    elif item.critical:
        urgency = SupplyUrgency.HIGH

    case.requested_quantity = quantity
    case.urgency = urgency
    case.status = ReplenishmentStatus.SOURCING
    case.rationale = (
        f"{item.on_hand} {item.unit} on hand against a reorder point of "
        f"{item.reorder_point}; "
        + (
            f"{cover} days of cover versus a {lead_time_days}-day supplier lead time"
            if cover is not None
            else f"usage not recorded; sizing to target level {item.target_level}"
        )
    )
    supply.save_case(case)

    requested = ReplenishmentRequested(
        episode_id=case.id,
        sku=case.sku,
        payload={
            "sku": case.sku,
            "item_name": item.name,
            "quantity": quantity,
            "unit": item.unit,
            "on_hand": item.on_hand,
            "target_level": item.target_level,
            "days_of_cover": cover,
            "lead_time_days": lead_time_days,
            "urgency": urgency.value,
            "rationale": case.rationale,
            "synthetic": True,
        },
    )
    return HandlerResult(
        summary=(
            f"{item.name}: {case.rationale}. Requesting {quantity} {item.unit} "
            f"({urgency.value.lower()} urgency)."
        ),
        episode_status=ReplenishmentStatus.SOURCING.value,
        risk_level=urgency.value,
        next_events=[requested],
    )
