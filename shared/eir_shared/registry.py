"""Agent descriptor used by the local registry (later: Gemini Enterprise Agent Registry)."""

from enum import StrEnum

from pydantic import BaseModel, Field


class AgentRiskLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AgentHealthStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


class AgentLifecycle(StrEnum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    DISABLED = "disabled"


class AgentDescriptor(BaseModel):
    name: str
    version: str = "0.1.0"
    capabilities: list[str] = Field(default_factory=list)
    risk_level: AgentRiskLevel = AgentRiskLevel.LOW
    description: str = ""
    health_status: AgentHealthStatus = AgentHealthStatus.HEALTHY
    lifecycle: AgentLifecycle = AgentLifecycle.ACTIVE
    fallback_agent: str | None = None
    granted_capabilities: list[str] = Field(default_factory=list)

    def effective_grants(self) -> list[str]:
        return self.granted_capabilities or list(self.capabilities)

    def is_available(self) -> bool:
        return (
            self.lifecycle == AgentLifecycle.ACTIVE
            and self.health_status != AgentHealthStatus.UNAVAILABLE
        )
