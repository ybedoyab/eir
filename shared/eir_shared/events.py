"""Domain events for long-running recovery workflows.

Event types are stable contracts. Transport (in-memory vs Pub/Sub) is an adapter.
"""

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _new_id() -> str:
    return str(uuid4())


class DomainEvent(BaseModel):
    """Base event published on the EventBus."""

    event_id: str = Field(default_factory=_new_id)
    event_type: str
    episode_id: str
    occurred_at: datetime = Field(default_factory=_utcnow)
    payload: dict[str, Any] = Field(default_factory=dict)


class RecoveryEpisodeStarted(DomainEvent):
    event_type: Literal["RecoveryEpisodeStarted"] = "RecoveryEpisodeStarted"
    patient_id: str


class FollowUpDue(DomainEvent):
    event_type: Literal["FollowUpDue"] = "FollowUpDue"


class PatientResponded(DomainEvent):
    event_type: Literal["PatientResponded"] = "PatientResponded"
    channel: str = "unknown"


class AdherenceConcernDetected(DomainEvent):
    event_type: Literal["AdherenceConcernDetected"] = "AdherenceConcernDetected"


class RiskEscalated(DomainEvent):
    event_type: Literal["RiskEscalated"] = "RiskEscalated"
    risk_level: str = "HIGH"


class AppointmentRequested(DomainEvent):
    event_type: Literal["AppointmentRequested"] = "AppointmentRequested"


class HumanReviewRequested(DomainEvent):
    event_type: Literal["HumanReviewRequested"] = "HumanReviewRequested"
    reason: str = ""


class ClinicianResolved(DomainEvent):
    event_type: Literal["ClinicianResolved"] = "ClinicianResolved"
    review_id: str = ""
    note: str = ""


class RecoveryEpisodeCompleted(DomainEvent):
    event_type: Literal["RecoveryEpisodeCompleted"] = "RecoveryEpisodeCompleted"


class ContentSecurityBlocked(DomainEvent):
    event_type: Literal["ContentSecurityBlocked"] = "ContentSecurityBlocked"
    filter_category: str = ""
    adapter: str = ""
    capability: str = ""


class VoiceCallStarted(DomainEvent):
    event_type: Literal["VoiceCallStarted"] = "VoiceCallStarted"


class VoiceCallConnected(DomainEvent):
    event_type: Literal["VoiceCallConnected"] = "VoiceCallConnected"


class VoiceCallCompleted(DomainEvent):
    event_type: Literal["VoiceCallCompleted"] = "VoiceCallCompleted"


class VoiceCallFailed(DomainEvent):
    event_type: Literal["VoiceCallFailed"] = "VoiceCallFailed"


class InventoryLevelLow(DomainEvent):
    """Emitted by the stock monitor when on-hand stock crosses the reorder point."""

    event_type: Literal["InventoryLevelLow"] = "InventoryLevelLow"
    sku: str = ""


class ReplenishmentRequested(DomainEvent):
    event_type: Literal["ReplenishmentRequested"] = "ReplenishmentRequested"
    sku: str = ""


class SupplierContacted(DomainEvent):
    event_type: Literal["SupplierContacted"] = "SupplierContacted"
    supplier_id: str = ""


class SupplierQuoteReceived(DomainEvent):
    event_type: Literal["SupplierQuoteReceived"] = "SupplierQuoteReceived"
    supplier_id: str = ""


class SupplierUnavailable(DomainEvent):
    event_type: Literal["SupplierUnavailable"] = "SupplierUnavailable"
    supplier_id: str = ""


class PurchaseOrderDrafted(DomainEvent):
    event_type: Literal["PurchaseOrderDrafted"] = "PurchaseOrderDrafted"
    purchase_order_id: str = ""


class SupplyApprovalGranted(DomainEvent):
    """Operations sign-off. Mirrors ClinicianResolved for the supply workflow."""

    event_type: Literal["SupplyApprovalGranted"] = "SupplyApprovalGranted"
    review_id: str = ""
    note: str = ""


class PurchaseOrderApproved(DomainEvent):
    event_type: Literal["PurchaseOrderApproved"] = "PurchaseOrderApproved"
    purchase_order_id: str = ""


class RestockScheduled(DomainEvent):
    event_type: Literal["RestockScheduled"] = "RestockScheduled"
    purchase_order_id: str = ""


EVENT_TYPE_MAP: dict[str, type[DomainEvent]] = {
    "RecoveryEpisodeStarted": RecoveryEpisodeStarted,
    "FollowUpDue": FollowUpDue,
    "PatientResponded": PatientResponded,
    "AdherenceConcernDetected": AdherenceConcernDetected,
    "RiskEscalated": RiskEscalated,
    "AppointmentRequested": AppointmentRequested,
    "HumanReviewRequested": HumanReviewRequested,
    "ClinicianResolved": ClinicianResolved,
    "RecoveryEpisodeCompleted": RecoveryEpisodeCompleted,
    "ContentSecurityBlocked": ContentSecurityBlocked,
    "VoiceCallStarted": VoiceCallStarted,
    "VoiceCallConnected": VoiceCallConnected,
    "VoiceCallCompleted": VoiceCallCompleted,
    "VoiceCallFailed": VoiceCallFailed,
    "InventoryLevelLow": InventoryLevelLow,
    "ReplenishmentRequested": ReplenishmentRequested,
    "SupplierContacted": SupplierContacted,
    "SupplierQuoteReceived": SupplierQuoteReceived,
    "SupplierUnavailable": SupplierUnavailable,
    "PurchaseOrderDrafted": PurchaseOrderDrafted,
    "SupplyApprovalGranted": SupplyApprovalGranted,
    "PurchaseOrderApproved": PurchaseOrderApproved,
    "RestockScheduled": RestockScheduled,
}

# Each workflow runtime subscribes to its own slice of EVENT_TYPE_MAP. A runtime
# silently drops events whose aggregate it does not own, so the split must be
# explicit rather than "everything in the map".
SUPPLY_EVENT_TYPES: frozenset[str] = frozenset(
    {
        "InventoryLevelLow",
        "ReplenishmentRequested",
        "SupplierContacted",
        "SupplierQuoteReceived",
        "SupplierUnavailable",
        "PurchaseOrderDrafted",
        "SupplyApprovalGranted",
        "PurchaseOrderApproved",
        "RestockScheduled",
    }
)

RECOVERY_EVENT_TYPES: frozenset[str] = frozenset(EVENT_TYPE_MAP) - SUPPLY_EVENT_TYPES


def parse_event(event_type: str, **kwargs: Any) -> DomainEvent:
    cls = EVENT_TYPE_MAP.get(event_type)
    payload = dict(kwargs.get("payload") or {})
    merged = {**payload, **kwargs}
    if cls is None:
        data = {key: value for key, value in kwargs.items() if key != "event_type"}
        return DomainEvent(event_type=event_type, **data)
    allowed = {key: value for key, value in merged.items() if key in cls.model_fields}
    return cls(**allowed)


def parse_event_dict(raw: dict[str, Any]) -> DomainEvent:
    data = dict(raw)
    event_type = str(data.pop("event_type", "DomainEvent"))
    return parse_event(event_type, **data)
