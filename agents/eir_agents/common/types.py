from eir_shared.events import DomainEvent
from pydantic import BaseModel, Field


class DelegationDecision(BaseModel):
    episode_id: str
    capability: str | None
    agent_name: str | None = None
    allowed: bool
    requires_human_approval: bool = False
    reason: str = ""
    event_type: str = ""


class HandlerResult(BaseModel):
    """Deterministic specialist output. No clinical diagnosis."""

    summary: str = ""
    episode_status: str | None = None
    risk_level: str | None = None
    review_reason: str | None = None
    next_events: list[DomainEvent] = Field(default_factory=list)
