"""Enterprise Agent Registry adapter."""

from __future__ import annotations

from eir_agents.registry.service import AgentRegistry
from eir_shared.registry import AgentDescriptor, AgentHealthStatus


class EnterpriseAgentRegistry:
    """Wraps the local registry with health, lifecycle, and fallback routing."""

    def __init__(self, registry: AgentRegistry) -> None:
        self._registry = registry

    def register(self, descriptor: AgentDescriptor) -> None:
        self._registry.register(descriptor)

    def find_by_capability(self, capability: str) -> AgentDescriptor | None:
        descriptor = self._registry.find_by_capability(capability)
        if descriptor is None or not descriptor.is_available():
            return self._fallback_for(capability, exclude=descriptor.name if descriptor else None)
        if descriptor.health_status == AgentHealthStatus.DEGRADED and descriptor.fallback_agent:
            fallback = self._registry.list_agents()
            for candidate in fallback:
                if candidate.name == descriptor.fallback_agent and candidate.is_available():
                    if capability in candidate.capabilities:
                        return candidate
        return descriptor

    def list_agents(self) -> list[AgentDescriptor]:
        return self._registry.list_agents()

    def _fallback_for(self, capability: str, *, exclude: str | None) -> AgentDescriptor | None:
        for descriptor in self._registry.list_agents():
            if descriptor.name == exclude:
                continue
            if capability in descriptor.capabilities and descriptor.is_available():
                return descriptor
        return None
