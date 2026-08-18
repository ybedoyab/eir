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
}


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
