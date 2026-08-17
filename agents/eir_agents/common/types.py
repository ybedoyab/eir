from pydantic import BaseModel


class DelegationDecision(BaseModel):
    episode_id: str
    capability: str | None
    agent_name: str | None = None
    allowed: bool
    requires_human_approval: bool = False
    reason: str = ""
    event_type: str = ""
