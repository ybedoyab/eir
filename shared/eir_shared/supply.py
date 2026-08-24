"""Pharmacy supply domain models.

A ReplenishmentCase is the supply-side counterpart of a RecoveryEpisode: a
long-running, event-sourced workflow that outlives any single request. Stock is
an operational record, not a clinical one, so nothing here touches FHIR.

These live in shared because both the agents package (procurement handlers) and
the backend (repositories, API) need them typed, the same way appointments do.
"""

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field, computed_field


def _utcnow() -> datetime:
    return datetime.now(UTC)


class StockStatus(StrEnum):
    HEALTHY = "HEALTHY"
    LOW = "LOW"
    CRITICAL = "CRITICAL"
    OUT_OF_STOCK = "OUT_OF_STOCK"


class SupplyUrgency(StrEnum):
    """Operational urgency of a stock-out. Not a clinical risk score."""

    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ReplenishmentStatus(StrEnum):
    ACTIVE = "ACTIVE"
    SOURCING = "SOURCING"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    BLOCKED = "BLOCKED"
    ORDERED = "ORDERED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class PurchaseOrderStatus(StrEnum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    PLACED = "PLACED"
    RECEIVED = "RECEIVED"
    CANCELLED = "CANCELLED"


class InventoryItem(BaseModel):
    """A medication the clinic dispenses to patients."""

    sku: str
    name: str
    form: str = ""
    unit: str = "unit"
    on_hand: int = 0
    reorder_point: int = 0
    target_level: int = 0
    daily_usage: float = 0.0
    critical: bool = False
    updated_at: datetime = Field(default_factory=_utcnow)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def status(self) -> StockStatus:
        if self.on_hand <= 0:
            return StockStatus.OUT_OF_STOCK
        if self.reorder_point and self.on_hand <= self.reorder_point // 2:
            return StockStatus.CRITICAL
        if self.on_hand <= self.reorder_point:
            return StockStatus.LOW
        return StockStatus.HEALTHY

    @computed_field  # type: ignore[prop-decorator]
    @property
    def days_of_cover(self) -> float | None:
        """Days of stock left at current usage. None when usage is unknown."""
        if self.daily_usage <= 0:
            return None
        return round(self.on_hand / self.daily_usage, 1)

    def needs_replenishment(self) -> bool:
        return self.on_hand <= self.reorder_point

    def suggested_quantity(self) -> int:
        """Order back up to target level, never below one unit."""
        return max(self.target_level - self.on_hand, 1)


class SupplierCatalogEntry(BaseModel):
    sku: str
    unit_price: float
    available_units: int
    currency: str = "USD"


class Supplier(BaseModel):
    id: str
    name: str
    contact_name: str = ""
    phone_e164: str = ""
    lead_time_days: int = 3
    catalog: list[SupplierCatalogEntry] = Field(default_factory=list)

    def entry_for(self, sku: str) -> SupplierCatalogEntry | None:
        for entry in self.catalog:
            if entry.sku == sku:
                return entry
        return None


class SupplierQuote(BaseModel):
    """What a supplier said on the call. Recorded, never inferred."""

    supplier_id: str
    supplier_name: str
    sku: str
    unit_price: float
    currency: str = "USD"
    available_units: int
    lead_time_days: int
    quoted_at: datetime = Field(default_factory=_utcnow)
    call_id: str = ""
    provider: str = ""
    transcript: list[dict[str, str]] = Field(default_factory=list)

    def can_fulfill(self, quantity: int) -> bool:
        return self.available_units >= quantity


class PurchaseOrder(BaseModel):
    id: str
    case_id: str
    sku: str
    supplier_id: str
    supplier_name: str
    quantity: int
    unit_price: float
    currency: str = "USD"
    lead_time_days: int = 0
    status: PurchaseOrderStatus = PurchaseOrderStatus.DRAFT
    drafted_at: datetime = Field(default_factory=_utcnow)
    approved_by: str = ""
    approved_at: datetime | None = None
    expected_delivery: datetime | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_cost(self) -> float:
        return round(self.quantity * self.unit_price, 2)


class ReplenishmentCase(BaseModel):
    """Event-sourced supply workflow. ``id`` is the event bus correlation key."""

    id: str
    sku: str
    item_name: str = ""
    status: ReplenishmentStatus = ReplenishmentStatus.ACTIVE
    urgency: SupplyUrgency = SupplyUrgency.NORMAL
    opened_at: datetime = Field(default_factory=_utcnow)
    closed_at: datetime | None = None
    requested_quantity: int = 0
    rationale: str = ""
    quotes: list[SupplierQuote] = Field(default_factory=list)
    purchase_order: PurchaseOrder | None = None
    contacted_supplier_ids: list[str] = Field(default_factory=list)
    assigned_agents: list[str] = Field(default_factory=list)

    def best_quote(self, quantity: int) -> SupplierQuote | None:
        """Cheapest quote that can actually fulfil the request.

        Availability wins over price: a cheaper supplier that cannot ship the
        full quantity does not solve the stock-out.
        """
        viable = [quote for quote in self.quotes if quote.can_fulfill(quantity)]
        if not viable:
            return None
        return min(viable, key=lambda quote: (quote.unit_price, quote.lead_time_days))
