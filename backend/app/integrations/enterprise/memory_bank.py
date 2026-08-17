"""Firestore-backed agent memory (Memory Bank stand-in)."""

from __future__ import annotations

from typing import Any


class FirestoreAgentMemory:
    """Persists per-agent memory in Firestore under ``agent_memory/{episode_id}``."""

    def __init__(self, client: Any) -> None:
        self._client = client
        self._collection = "agent_memory"

    def _doc(self, episode_id: str):
        return self._client.collection(self._collection).document(episode_id)

    async def get(self, episode_id: str, agent_name: str, key: str) -> Any | None:
        snapshot = self._doc(episode_id).get()
        if not snapshot.exists:
            return None
        agents = snapshot.to_dict().get("agents", {})
        return agents.get(agent_name, {}).get(key)

    async def set(self, episode_id: str, agent_name: str, key: str, value: Any) -> None:
        doc_ref = self._doc(episode_id)
        snapshot = doc_ref.get()
        data = snapshot.to_dict() if snapshot.exists else {"agents": {}}
        agents = dict(data.get("agents", {}))
        agent_data = dict(agents.get(agent_name, {}))
        agent_data[key] = value
        agents[agent_name] = agent_data
        doc_ref.set({"agents": agents}, merge=True)
