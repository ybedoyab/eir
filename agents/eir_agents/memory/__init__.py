"""Agent memory adapters.

Re-exports eir_shared memory protocols. Swap InMemoryAgentMemory for Memory Bank later.
"""

from eir_shared.memory import AgentMemory, InMemoryAgentMemory, InMemoryEpisodeStore

__all__ = ["AgentMemory", "InMemoryAgentMemory", "InMemoryEpisodeStore"]
