"""Proactive stock monitoring (Cloud Scheduler entry point).

The supply-side counterpart of FollowUpScheduler. Cloud Scheduler calls this on
a fixed cadence; the repository claim decides whether anything actually happens,
so an over-eager schedule cannot open duplicate purchase orders.
"""

from __future__ import annotations

import threading
from datetime import UTC, datetime

from eir_shared.events import InventoryLevelLow

from app.repositories.scheduler_idempotency import (
    InMemorySchedulerIdempotencyStore,
    SchedulerIdempotencyStore,
)
from app.repositories.supply_repository import SupplyRepository


class StockMonitor:
    def __init__(
        self,
        supply: SupplyRepository,
        *,
        idempotency: SchedulerIdempotencyStore | None = None,
    ) -> None:
        self._supply = supply
        self._idempotency = idempotency or InMemorySchedulerIdempotencyStore()
        self._lock = threading.Lock()

    def process_due(
        self,
        *,
        now: datetime | None = None,
        idempotency_key: str | None = None,
    ) -> list[InventoryLevelLow]:
        now = now or datetime.now(UTC)
        idempotency_key = idempotency_key or now.isoformat()
        with self._lock:
            if not self._idempotency.claim_run(idempotency_key):
                return []
            events: list[InventoryLevelLow] = []
            for item in self._supply.list_items():
                if not item.needs_replenishment():
                    continue
                claimed = self._supply.claim_replenishment(item.sku, now=now)
                if claimed is not None:
                    events.append(claimed)
            return events

    def trigger_sku(
        self,
        sku: str,
        *,
        now: datetime | None = None,
    ) -> InventoryLevelLow | None:
        """Demo control: claim one SKU through the production path.

        Uses the same ``claim_replenishment`` as Cloud Scheduler. Does not invoke
        procurement agents and does not bypass the EventBus.
        """
        now = now or datetime.now(UTC)
        return self._supply.claim_replenishment(sku, now=now)

    def drain_stock(self, sku: str, *, now: datetime | None = None) -> InventoryLevelLow | None:
        """Demo control: consume stock down to the reorder point, then claim.

        Models dispensing to patients rather than editing the number by hand, so
        the low-stock event is produced by the same rule that guards production.
        """
        item = self._supply.get_item(sku)
        if item is None:
            return None
        if not item.needs_replenishment():
            shortfall = item.on_hand - (item.reorder_point // 2)
            self._supply.adjust_stock(sku, -max(shortfall, 1))
        return self.trigger_sku(sku, now=now)
