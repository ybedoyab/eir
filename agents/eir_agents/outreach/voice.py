"""Voice channel adapter. Isolated from recovery business logic.

Synthetic providers complete in-process. Real PSTN is asynchronous:
start_outbound_call returns immediately; PatientResponded arrives later
via the authenticated Voximplant callback.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol
from uuid import uuid4

VoiceMode = Literal["sync", "async"]


@dataclass
class VoiceLaunchResult:
    call_id: str
    correlation_id: str
    provider: str
    mode: VoiceMode
    conversation: list[dict[str, str]] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class VoiceProvider(Protocol):
    provider_name: str
    mode: VoiceMode

    async def start_outbound_call(
        self,
        *,
        to: str,
        episode_id: str,
        patient_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> VoiceLaunchResult: ...

    async def send_audio(self, call_id: str, audio: bytes) -> None: ...

    async def end_call(self, call_id: str) -> None: ...


class MockVoiceProvider:
    """Records calls in memory. Does not place real calls."""

    provider_name = "mock"
    mode: VoiceMode = "sync"

    def __init__(self) -> None:
        self.calls: dict[str, dict[str, Any]] = {}
        self._seq = 0

    async def start_outbound_call(
        self,
        *,
        to: str,
        episode_id: str,
        patient_id: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> VoiceLaunchResult:
        self._seq += 1
        call_id = f"mock-call-{self._seq}"
        correlation_id = str(uuid4())
        payload = {
            "to": to,
            "episode_id": episode_id,
            "patient_id": patient_id,
            "metadata": metadata or {},
            "audio_chunks": 0,
            "ended": False,
            "correlation_id": correlation_id,
        }
        self.calls[call_id] = payload
        return VoiceLaunchResult(
            call_id=call_id,
            correlation_id=correlation_id,
            provider=self.provider_name,
            mode=self.mode,
            conversation=payload.get("conversation"),
        )

    async def send_audio(self, call_id: str, audio: bytes) -> None:
        self.calls[call_id]["audio_chunks"] += 1
        self.calls[call_id]["last_audio_bytes"] = len(audio)

    async def end_call(self, call_id: str) -> None:
        self.calls[call_id]["ended"] = True
