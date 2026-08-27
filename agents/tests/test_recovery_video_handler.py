"""Prompt construction and event outcomes for the recovery-video handler.

No model and no network: the video client is a fake that records what it was asked for.
"""

from __future__ import annotations

from typing import Any

from eir_agents.recovery_video.handler import build_prompt, generate_recovery_video
from eir_shared.events import RecoveryEpisodeStarted, RecoveryVideoRequested


class FakeVideoClient:
    adapter_name = "fake_veo"
    available = True

    def __init__(self, *, ok: bool = True, cached: bool = False, error: str | None = None) -> None:
        self._ok = ok
        self._cached = cached
        self._error = error
        self.calls: list[dict[str, Any]] = []

    def generate(self, *, prompt: str, episode_id: str, force: bool = False) -> Any:
        self.calls.append({"prompt": prompt, "episode_id": episode_id, "force": force})

        class _Result:
            ok = self._ok
            video_url = "/api/v1/recovery/episode-1/video/" + "a" * 32 + ".mp4"
            storage_key = "clips/" + "a" * 32 + ".mp4"
            duration_seconds = 8.0
            model = "veo-test"
            cached = self._cached
            error = self._error

        return _Result()


class _Episodes:
    def __init__(self, events: list[Any]) -> None:
        self._events = events

    def list_events(self, episode_id: str) -> list[Any]:
        return self._events


def _requested(payload: dict[str, Any] | None = None) -> RecoveryVideoRequested:
    return RecoveryVideoRequested(episode_id="episode-1", payload=payload or {})


def _narration_of(prompt: str) -> str:
    """The single line the narrator is told to speak, pulled back out of the prompt."""
    return prompt.split('unhurried: "', 1)[1].split('"', 1)[0]


def test_narration_speaks_the_context_and_one_task() -> None:
    event = _requested(
        {"context": "Knee replacement recovery", "tasks": ["Walk daily", "Ice the knee"]}
    )

    prompt = build_prompt(event)
    narration = _narration_of(prompt)

    assert narration == "Knee replacement recovery. Walk daily. Your full plan is on screen."
    # The rest of the plan is not recited — it stays in the verified on-page text list.
    assert "Ice the knee" not in narration
    assert "No on-screen text" in prompt


def test_narration_fits_the_clip_length() -> None:
    event = _requested(
        {
            "context": "Total knee replacement recovery programme",
            "tasks": [
                "Walk for at least fifteen minutes every day as tolerated by your care team",
                "Ice the knee",
            ],
        }
    )

    narration = _narration_of(build_prompt(event, duration_seconds=8))

    # ~2 words per second: an 8-second clip gets 16 words, and a task too long to fit is
    # dropped in favour of the short framing line rather than being spoken at double speed.
    assert len(narration.split()) <= 16
    assert "fifteen minutes" not in narration


def test_longer_clips_get_a_larger_word_budget() -> None:
    event = _requested(
        {"context": "Knee recovery", "tasks": ["Walk for fifteen minutes each day as tolerated"]}
    )

    short = _narration_of(build_prompt(event, duration_seconds=4))
    long = _narration_of(build_prompt(event, duration_seconds=12))

    assert "fifteen minutes" not in short
    assert "fifteen minutes" in long


def test_narration_never_speaks_a_medication_task() -> None:
    event = _requested({"context": "Post-op", "tasks": ["Take prescribed medication"]})

    narration = _narration_of(build_prompt(event))

    assert "medication" not in narration.lower()
    assert narration == "Post-op. Your full plan is on screen."


def test_scene_follows_the_primary_task() -> None:
    walking = build_prompt(_requested({"context": "Knee recovery", "tasks": ["Walk daily"]}))
    calling = build_prompt(
        _requested({"context": "Knee recovery", "tasks": ["Report new symptoms"]})
    )

    assert "walking slowly" in walking
    assert "on the phone" in calling


def test_prompt_falls_back_to_generic_safe_template() -> None:
    narration = _narration_of(build_prompt(_requested()))

    assert narration.startswith("Post-procedure recovery")
    assert len(narration.split()) <= 16


def test_context_comes_from_the_episodes_started_event() -> None:
    started = RecoveryEpisodeStarted(
        episode_id="episode-1",
        patient_id="patient-synthetic-1",
        payload={"context": "Hip replacement recovery", "tasks": ["Walk daily"]},
    )
    client = FakeVideoClient()

    generate_recovery_video(
        _requested(),
        patient_id="patient-synthetic-1",
        video_client=client,
        episodes=_Episodes([started]),
    )

    assert "Hip replacement recovery" in client.calls[0]["prompt"]


def test_ready_event_carries_the_url_and_cache_flag() -> None:
    client = FakeVideoClient(cached=True)

    result = generate_recovery_video(
        _requested(), patient_id="patient-synthetic-1", video_client=client
    )

    assert len(result.next_events) == 1
    event = result.next_events[0]
    assert event.event_type == "RecoveryVideoReady"
    assert event.payload["video_url"].startswith("/api/v1/recovery/")
    assert event.payload["cached"] is True
    assert event.payload["generated_by"] == "fake_veo"
    assert "Reused an existing" in result.summary


def test_force_flag_is_passed_through_to_the_client() -> None:
    client = FakeVideoClient()

    generate_recovery_video(
        _requested({"force": True}), patient_id="patient-synthetic-1", video_client=client
    )

    assert client.calls[0]["force"] is True


def test_force_defaults_off_so_requests_can_hit_the_cache() -> None:
    client = FakeVideoClient()

    generate_recovery_video(_requested(), patient_id="patient-synthetic-1", video_client=client)

    assert client.calls[0]["force"] is False


def test_refusal_becomes_a_failed_event_not_an_exception() -> None:
    client = FakeVideoClient(ok=False, error="cooldown")

    result = generate_recovery_video(
        _requested({"force": True}), patient_id="patient-synthetic-1", video_client=client
    )

    event = result.next_events[0]
    assert event.event_type == "RecoveryVideoFailed"
    assert event.payload["reason"] == "cooldown"


def test_unavailable_client_degrades_to_text_only() -> None:
    class _Off:
        adapter_name = "video_unavailable"
        available = False

    result = generate_recovery_video(
        _requested(), patient_id="patient-synthetic-1", video_client=_Off()
    )

    event = result.next_events[0]
    assert event.event_type == "RecoveryVideoFailed"
    assert event.payload["reason"] == "video_generation_unavailable"
