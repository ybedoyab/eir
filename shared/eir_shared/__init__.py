"""Shared EIR contracts: events, capabilities, and local adapters."""

from eir_shared.capabilities import Capability
from eir_shared.event_bus import EventBus, InMemoryEventBus
from eir_shared.identity import AgentIdentity, AuthorizationPolicy, PolicyDecision
from eir_shared.memory import AgentMemory, EpisodeStore, InMemoryAgentMemory, InMemoryEpisodeStore
from eir_shared.observability import StructuredLogger, WorkflowTrace
from eir_shared.registry import AgentDescriptor, AgentRiskLevel

__all__ = [
    "AgentDescriptor",
    "AgentIdentity",
    "AgentMemory",
    "AgentRiskLevel",
    "AuthorizationPolicy",
    "Capability",
    "EpisodeStore",
    "EventBus",
    "InMemoryAgentMemory",
    "InMemoryEpisodeStore",
    "InMemoryEventBus",
    "PolicyDecision",
    "StructuredLogger",
    "WorkflowTrace",
]
