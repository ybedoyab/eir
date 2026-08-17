"""Optional Agent Engine memory adapter with Firestore fallback."""

from __future__ import annotations

import logging
from typing import Any, Protocol

from app.integrations.enterprise.memory_bank import FirestoreAgentMemoryFallback

logger = logging.getLogger("eir.memory_bank")


class AgentMemoryStore(Protocol):
    adapter_name: str

    async def get(self, episode_id: str, agent_name: str, key: str) -> Any | None: ...

    async def set(self, episode_id: str, agent_name: str, key: str, value: Any) -> None: ...


class VertexAgentMemoryFallbackAdapter(FirestoreAgentMemoryFallback):
    """Uses Firestore until Agent Engine Memory Bank wiring is available in this project."""

    adapter_name = "firestore_fallback"


def build_agent_memory(
    *,
    firestore_client: Any | None,
    prefer_agent_engine: bool,
) -> AgentMemoryStore:
    if firestore_client is None:
        from eir_shared.memory import InMemoryAgentMemory

        store = InMemoryAgentMemory()
        store.adapter_name = "in_memory"  # type: ignore[attr-defined]
        return store  # type: ignore[return-value]
    if prefer_agent_engine:
        try:
            import vertexai  # noqa: F401

            logger.info(
                "Agent Engine memory API available; using Firestore fallback adapter for now"
            )
        except Exception:
            logger.info("Agent Engine memory unavailable; using Firestore fallback")
    return FirestoreAgentMemoryFallback(firestore_client)
