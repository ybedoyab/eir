"""Pharmacy supply domain models.

A ReplenishmentCase is the supply-side counterpart of a RecoveryEpisode: a
long-running, event-sourced workflow that outlives any single request. Stock is
an operational record, not a clinical one, so nothing here touches FHIR.

These live in shared because both the agents package (procurement handlers) and
the backend (repositories, API) need them typed, the same way appointments do.
"""

from collections.abc import Iterable
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, computed_field

PHARMACY_SKU_SYSTEM = "https://eir.local/pharmacy-sku"
RXNORM_SYSTEM = "http://www.nlm.nih.gov/research/umls/rxnorm"


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
    rxnorm_code: str = ""
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


def _codings(resource: dict[str, Any]) -> list[dict[str, Any]]:
    concept = resource.get("medicationCodeableConcept") or {}
    coding = concept.get("coding") or []
    return [item for item in coding if isinstance(item, dict)]


def sku_for_medication_request(
    resource: dict[str, Any],
    items: Iterable[InventoryItem] | None = None,
) -> str | None:
    """Pharmacy SKU coded on the request, else a reverse lookup by RxNorm."""
    for coding in _codings(resource):
        system = str(coding.get("system") or "")
        code = str(coding.get("code") or "").strip()
        if system == PHARMACY_SKU_SYSTEM and code:
            return code
    rxnorm = rxnorm_for_medication_request(resource)
    if not rxnorm or items is None:
        return None
    for item in items:
        if item.rxnorm_code and item.rxnorm_code == rxnorm:
            return item.sku
    return None


def rxnorm_for_medication_request(resource: dict[str, Any]) -> str:
    for coding in _codings(resource):
        system = str(coding.get("system") or "")
        code = str(coding.get("code") or "").strip()
        if (system == RXNORM_SYSTEM or "rxnorm" in system.lower()) and code:
            return code
    return ""


def medication_display_name(resource: dict[str, Any]) -> str:
    concept = resource.get("medicationCodeableConcept") or {}
    text = str(concept.get("text") or "").strip()
    if text:
        return text
    for coding in _codings(resource):
        display = str(coding.get("display") or "").strip()
        if display:
            return display
    return str(resource.get("id") or "Medication")


def daily_units_from_medication_request(resource: dict[str, Any]) -> float:
    """Units consumed per day from FHIR timing.repeat. 0 when unknown."""
    if str(resource.get("status") or "").lower() not in {"", "active"}:
        return 0.0
    for instruction in resource.get("dosageInstruction") or []:
        if not isinstance(instruction, dict):
            continue
        repeat = ((instruction.get("timing") or {}).get("repeat") or {})
        try:
            frequency = float(repeat.get("frequency") or 0)
            period = float(repeat.get("period") or 0)
        except (TypeError, ValueError):
            continue
        if frequency <= 0 or period <= 0:
            continue
        unit = str(repeat.get("periodUnit") or "d").lower()
        if unit in {"d", "day", "days"}:
            return round(frequency / period, 4)
        if unit in {"h", "hour", "hours"}:
            return round(frequency * (24.0 / period), 4)
        if unit in {"wk", "week", "weeks"}:
            return round(frequency / (period * 7.0), 4)
    return 0.0


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
