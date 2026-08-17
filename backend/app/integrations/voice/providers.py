"""Voice channel adapters."""

from __future__ import annotations

from typing import Any

from eir_agents.outreach.voice import MockVoiceProvider


class SyntheticVoiceProvider(MockVoiceProvider):
    """Structured synthetic conversation stub — NOT Gemini Live telephony."""

    async def start_outbound_call(
        self,
        *,
        to: str,
        episode_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        call_id = await super().start_outbound_call(
            to=to,
            episode_id=episode_id,
            metadata=metadata,
        )
        patient_id = to.removeprefix("synthetic:")
        self.calls[call_id]["provider"] = "synthetic-voice"
        self.calls[call_id]["conversation"] = _synthetic_conversation(patient_id)
        return call_id


def _synthetic_conversation(patient_id: str) -> list[dict[str, str]]:
    if patient_id.endswith("002"):
        return [
            {"role": "agent", "text": "How is your pain today on a scale of 0-10?"},
            {"role": "patient", "text": "It is an 8 and I noticed swelling near the incision."},
        ]
    return [
        {"role": "agent", "text": "How is your pain today on a scale of 0-10?"},
        {"role": "patient", "text": "About a 2, recovery is going fine."},
    ]


def voice_provider(name: str) -> MockVoiceProvider | SyntheticVoiceProvider:
    if name in {"gemini", "synthetic"}:
        return SyntheticVoiceProvider()
    return MockVoiceProvider()
