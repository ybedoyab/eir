from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class EpisodeStatus(StrEnum):
    ACTIVE = "ACTIVE"
    WAITING = "WAITING"
    WAITING_FOR_NEXT_FOLLOWUP = "WAITING_FOR_NEXT_FOLLOWUP"
    ESCALATED = "ESCALATED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class RiskLevel(StrEnum):
    """Platform workflow risk, not a diagnosis."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RecoveryEpisode(BaseModel):
    id: str
    patient_id: str
    status: EpisodeStatus = EpisodeStatus.ACTIVE
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    next_follow_up_at: datetime | None = None
    risk_level: RiskLevel = RiskLevel.LOW
    assigned_agents: list[str] = Field(default_factory=list)
