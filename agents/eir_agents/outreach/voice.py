"""Voice channel adapter. Isolated from recovery business logic.

Later: Gemini Live / ADK streaming and/or an external telephony provider.
"""

from __future__ import annotations

from typing import Any, Protocol


class VoiceProvider(Protocol):
    async def start_outbound_call(
        self,
        *,
        to: str,
        episode_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> str: ...

    async def send_audio(self, call_id: str, audio: bytes) -> None: ...

    async def end_call(self, call_id: str) -> None: ...


class MockVoiceProvider:
    """Records calls in memory. Does not place real calls."""

    def __init__(self) -> None:
        self.calls: dict[str, dict[str, Any]] = {}
        self._seq = 0

    async def start_outbound_call(
        self,
        *,
        to: str,
        episode_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        self._seq += 1
        call_id = f"mock-call-{self._seq}"
        self.calls[call_id] = {
            "to": to,
            "episode_id": episode_id,
            "metadata": metadata or {},
            "audio_chunks": 0,
            "ended": False,
        }
        return call_id

    async def send_audio(self, call_id: str, audio: bytes) -> None:
        self.calls[call_id]["audio_chunks"] += 1
        self.calls[call_id]["last_audio_bytes"] = len(audio)

    async def end_call(self, call_id: str) -> None:
        self.calls[call_id]["ended"] = True
