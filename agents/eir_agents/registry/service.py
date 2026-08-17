"""Local agent registry.

Looks up agents by capability, not by Python class. Later this maps to
Gemini Enterprise Agent Registry.
"""

from eir_shared.registry import AgentDescriptor


class AgentRegistry:
    def __init__(self) -> None:
        self._agents: list[AgentDescriptor] = []

    def register(self, descriptor: AgentDescriptor) -> None:
        self._agents.append(descriptor)

    def find_by_capability(self, capability: str) -> AgentDescriptor | None:
        for descriptor in self._agents:
            if capability in descriptor.capabilities:
                return descriptor
        return None

    def list_agents(self) -> list[AgentDescriptor]:
        return list(self._agents)
