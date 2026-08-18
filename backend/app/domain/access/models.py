from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class AccessChannel(StrEnum):
    WEB = "web"
    VOICE = "voice"
    SMS = "sms"


class AccessSessionStatus(StrEnum):
    ACTIVE = "active"
    AWAITING_SELECTION = "awaiting_selection"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    HANDOFF = "handoff"
    COMPLETED = "completed"
    CLOSED = "closed"


class PatientAccessSession(BaseModel):
    id: str
    patient_id: str | None = None
    channel: AccessChannel = AccessChannel.WEB
    status: AccessSessionStatus = AccessSessionStatus.ACTIVE
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    current_intent: str = ""
    selected_appointment_id: str | None = None
    selected_slot_id: str | None = None
    handoff_required: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
