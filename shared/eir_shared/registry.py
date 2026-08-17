"""Agent descriptor used by the local registry (later: Gemini Enterprise Agent Registry)."""

from enum import StrEnum

from pydantic import BaseModel, Field


class AgentRiskLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AgentDescriptor(BaseModel):
    name: str
    version: str = "0.1.0"
    capabilities: list[str] = Field(default_factory=list)
    risk_level: AgentRiskLevel = AgentRiskLevel.LOW
    description: str = ""
