"""Long-running workflow state.

Recovery Episodes are persistent workflows, not request-scoped jobs.
Local implementations are in-memory; replace with Agent Runtime + Memory Bank.

TODO: EpisodeStore adapter for Agent Runtime / Firestore / Cloud SQL.
TODO: AgentMemory adapter for Gemini Enterprise Memory Bank.
"""

from __future__ import annotations

from typing import Any, Protocol


class EpisodeStore(Protocol):
    """Durable Recovery Episode workflow state (days/weeks)."""

    async def get(self, episode_id: str) -> dict[str, Any] | None: ...

    async def save(self, episode_id: str, state: dict[str, Any]) -> None: ...


class AgentMemory(Protocol):
    """Per-agent / per-episode memory distinct from episode workflow state."""

    async def get(self, episode_id: str, agent_name: str, key: str) -> Any | None: ...

    async def set(self, episode_id: str, agent_name: str, key: str, value: Any) -> None: ...


class InMemoryEpisodeStore:
    def __init__(self) -> None:
        self._items: dict[str, dict[str, Any]] = {}

    async def get(self, episode_id: str) -> dict[str, Any] | None:
        state = self._items.get(episode_id)
        return dict(state) if state is not None else None

    async def save(self, episode_id: str, state: dict[str, Any]) -> None:
        self._items[episode_id] = dict(state)


class InMemoryAgentMemory:
    def __init__(self) -> None:
        self._items: dict[tuple[str, str, str], Any] = {}

    async def get(self, episode_id: str, agent_name: str, key: str) -> Any | None:
        return self._items.get((episode_id, agent_name, key))

    async def set(self, episode_id: str, agent_name: str, key: str, value: Any) -> None:
        self._items[(episode_id, agent_name, key)] = value
