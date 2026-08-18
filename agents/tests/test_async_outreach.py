import asyncio

from eir_agents.outreach.handler import handle_follow_up
from eir_agents.outreach.voice import VoiceLaunchResult
from eir_shared.events import FollowUpDue, PatientResponded, VoiceCallStarted


class AsyncVoiceProvider:
    provider_name = "voximplant"
    mode = "async"

    async def start_outbound_call(self, **kwargs):
        assert kwargs["patient_id"].startswith("patient-synthetic-")
        return VoiceLaunchResult(
            call_id="call-async",
            correlation_id="corr-async",
            provider="voximplant",
            mode="async",
            metadata={"gemini_live_model": "gemini-live-2.5-flash-native-audio"},
        )

    async def send_audio(self, call_id: str, audio: bytes) -> None:
        return None

    async def end_call(self, call_id: str) -> None:
        raise AssertionError("async provider must not wait for the conversation")


def test_async_outreach_does_not_emit_patient_responded() -> None:
    event = FollowUpDue(episode_id="ep-async")
    result = asyncio.run(
        handle_follow_up(
            event,
            patient_id="patient-synthetic-001",
            voice=AsyncVoiceProvider(),
        )
    )
    types = [item.event_type for item in result.next_events]
    assert types == ["VoiceCallStarted"]
    assert isinstance(result.next_events[0], VoiceCallStarted)
    assert not any(isinstance(item, PatientResponded) for item in result.next_events)
    assert result.episode_status == "ACTIVE"
    payload = result.next_events[0].payload
    assert "destination" not in payload
    assert payload["provider"] == "voximplant"
