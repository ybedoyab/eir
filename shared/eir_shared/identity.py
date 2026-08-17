"""Agent identity and authorization placeholders.

Agents request capabilities rather than assuming unrestricted access.
Later this maps to Agent Identity + Agent Gateway.

Do not grow this into a full RBAC framework in the scaffold.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class AgentIdentity(BaseModel):
    name: str
    version: str = "0.1.0"
    granted_capabilities: list[str] = Field(default_factory=list)


class PolicyDecision(BaseModel):
    allowed: bool
    reason: str = ""
    requires_human_approval: bool = False


class AuthorizationPolicy:
    """Capability check against an agent identity.

    High-risk actions still go through the safety gate even when this allows.
    """

    def decide(self, identity: AgentIdentity, capability: str) -> PolicyDecision:
        if capability in identity.granted_capabilities:
            return PolicyDecision(allowed=True, reason="capability granted to identity")
        return PolicyDecision(
            allowed=False,
            reason=f"identity {identity.name} lacks capability {capability}",
        )
