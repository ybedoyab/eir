from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class AppointmentStatus(StrEnum):
    PROPOSED = "proposed"
    PENDING = "pending"
    BOOKED = "booked"
    ARRIVED = "arrived"
    FULFILLED = "fulfilled"
    CANCELLED = "cancelled"
    NO_SHOW = "noshow"


class SlotStatus(StrEnum):
    FREE = "free"
    BUSY = "busy"
    BUSY_UNAVAILABLE = "busy-unavailable"
    ENTERED_IN_ERROR = "entered-in-error"


class AppointmentView(BaseModel):
    id: str
    patient_id: str
    status: AppointmentStatus
    specialty: str
    service_name: str
    practitioner_name: str
    practitioner_id: str = ""
    location_name: str
    location_id: str = ""
    start: datetime
    end: datetime
    slot_id: str | None = None
    appointment_type: str = "routine"
    cancellation_reason: str = ""


class SlotView(BaseModel):
    id: str
    schedule_id: str
    status: SlotStatus
    start: datetime
    end: datetime
    specialty: str
    service_name: str
    practitioner_name: str
    practitioner_id: str
    location_name: str
    location_id: str
    appointment_type: str = "routine"


class SlotSearchParams(BaseModel):
    patient_id: str
    specialty: str = ""
    service_name: str = ""
    location_id: str = ""
    practitioner_id: str = ""
    start_date: datetime | None = None
    end_date: datetime | None = None
    time_of_day: str = "any"
    appointment_type: str = "routine"
    limit: int = 24


class WaitlistRequest(BaseModel):
    id: str
    patient_id: str
    appointment_id: str
    specialty: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    status: str = "active"


class AppointmentReminder(BaseModel):
    id: str
    appointment_id: str
    patient_id: str
    scheduled_for: datetime
    status: str = "scheduled"
    channel: str = "in_app"
