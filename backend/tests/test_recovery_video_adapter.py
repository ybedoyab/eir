"""Storage, caching and quota behaviour for the Veo adapter.

Never calls live Vertex: the Veo invocation itself is stubbed, so what is under test is the
part that decides *whether* to call it and *where* the bytes land (plan §15.3).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from app.integrations.video.veo import (
    ADHOC_PREFIX,
    CACHED_PREFIX,
    LocalVideoStorage,
    StoreBackedVideoQuota,
    UnavailableVideoClient,
    VeoVideoAdapter,
    build_video_client,
    storage_key,
)
from app.repositories.scheduler_idempotency import InMemorySchedulerIdempotencyStore
from app.repositories.video_budget import InMemoryDailyVideoBudget


class _StubVeo(VeoVideoAdapter):
    """Adapter with the network call replaced by a counter."""

    def __init__(self, storage, quota=None, **kwargs):
        super().__init__(
            client_kwargs={},
            model="veo-test",
            max_wait_seconds=5,
            storage=storage,
            quota=quota,
            **kwargs,
        )
        self.calls = 0

    def _invoke_veo(self, prompt: str) -> bytes:
        self.calls += 1
        return f"mp4-bytes-{self.calls}".encode()


@pytest.fixture
def storage(tmp_path: Path) -> LocalVideoStorage:
    return LocalVideoStorage(tmp_path / "recovery_videos")


def _quota(cooldown: int = 0, daily_limit: int = 100) -> StoreBackedVideoQuota:
    return StoreBackedVideoQuota(
        claims=InMemorySchedulerIdempotencyStore(),
        counter=InMemoryDailyVideoBudget(),
        cooldown_seconds=cooldown,
        daily_limit=daily_limit,
    )


def test_identical_prompts_share_one_clip_across_episodes(storage: LocalVideoStorage) -> None:
    adapter = _StubVeo(storage, quota=_quota())

    first = adapter.generate(prompt="walk daily", episode_id="episode-1")
    second = adapter.generate(prompt="walk daily", episode_id="episode-2")

    assert first.ok and second.ok
    assert adapter.calls == 1, "second episode must reuse the stored clip, not call Veo again"
    assert first.cached is False
    assert second.cached is True
    assert first.storage_key == second.storage_key
    assert first.storage_key.startswith(CACHED_PREFIX)
    # The shared object is served under whichever episode asked for it.
    assert second.video_url.startswith("/api/v1/recovery/episode-2/video/")


def test_different_prompts_do_not_collide(storage: LocalVideoStorage) -> None:
    adapter = _StubVeo(storage, quota=_quota())

    first = adapter.generate(prompt="walk daily", episode_id="episode-1")
    second = adapter.generate(prompt="rest and hydrate", episode_id="episode-1")

    assert adapter.calls == 2
    assert first.storage_key != second.storage_key


def test_force_bypasses_cache_and_keeps_one_adhoc_clip(storage: LocalVideoStorage) -> None:
    adapter = _StubVeo(storage, quota=_quota())

    adapter.generate(prompt="walk daily", episode_id="episode-1")
    forced_one = adapter.generate(prompt="walk daily", episode_id="episode-1", force=True)
    forced_two = adapter.generate(prompt="walk daily", episode_id="episode-1", force=True)

    assert adapter.calls == 3, "each forced regeneration must really call Veo"
    assert forced_one.storage_key.startswith(f"{ADHOC_PREFIX}episode-1/")
    assert forced_two.storage_key != forced_one.storage_key
    # Pruned on write: the superseded ad-hoc clip is gone, so forcing cannot accumulate.
    assert storage.read(forced_one.storage_key) is None
    assert storage.read(forced_two.storage_key) is not None


def test_forcing_one_episode_leaves_another_episodes_clip_alone(
    storage: LocalVideoStorage,
) -> None:
    adapter = _StubVeo(storage, quota=_quota())

    kept = adapter.generate(prompt="walk daily", episode_id="episode-1", force=True)
    adapter.generate(prompt="walk daily", episode_id="episode-2", force=True)

    assert storage.read(kept.storage_key) is not None


def test_cooldown_refuses_a_second_generation(storage: LocalVideoStorage) -> None:
    adapter = _StubVeo(storage, quota=_quota(cooldown=3600))

    first = adapter.generate(prompt="walk daily", episode_id="episode-1", force=True)
    second = adapter.generate(prompt="walk daily", episode_id="episode-1", force=True)

    assert first.ok
    assert second.ok is False
    assert second.error == "cooldown"
    assert adapter.calls == 1


def test_cache_hits_are_free_of_quota(storage: LocalVideoStorage) -> None:
    quota = _quota(cooldown=3600)
    adapter = _StubVeo(storage, quota=quota)

    adapter.generate(prompt="walk daily", episode_id="episode-1")
    # A different episode inside the cooldown window still gets its video, because reusing a
    # stored clip costs nothing to protect.
    reused = adapter.generate(prompt="walk daily", episode_id="episode-2")

    assert reused.ok and reused.cached is True
    assert quota.describe()["used_today"] == 1


def test_daily_limit_is_a_hard_ceiling(storage: LocalVideoStorage) -> None:
    quota = _quota(daily_limit=2)
    adapter = _StubVeo(storage, quota=quota)

    for index in range(2):
        assert adapter.generate(
            prompt=f"plan {index}", episode_id=f"episode-{index}", force=True
        ).ok

    refused = adapter.generate(prompt="plan 3", episode_id="episode-3", force=True)

    assert refused.ok is False
    assert refused.error == "daily_limit_reached"
    assert adapter.calls == 2
    assert quota.describe()["used_today"] == 2


def test_status_reports_storage_and_remaining_budget(storage: LocalVideoStorage) -> None:
    adapter = _StubVeo(storage, quota=_quota(cooldown=60, daily_limit=25))
    adapter.generate(prompt="walk daily", episode_id="episode-1")

    status = adapter.status()

    assert status["configured"] is True
    assert status["storage"]["backend"] == "local"
    assert status["quota"] == {
        "cooldown_seconds": 60,
        "daily_limit": 25,
        "used_today": 1,
    }
    assert status["last_success"] is True


def test_read_round_trips_through_url_filename(storage: LocalVideoStorage) -> None:
    adapter = _StubVeo(storage, quota=_quota())
    result = adapter.generate(prompt="walk daily", episode_id="episode-1")
    filename = result.video_url.rsplit("/", 1)[-1]

    assert adapter.read(episode_id="episode-1", filename=filename) == b"mp4-bytes-1"


@pytest.mark.parametrize(
    "episode_id,filename",
    [
        ("episode-1", "../../etc/passwd"),
        ("episode-1", "abc.mp4"),  # too short to be one of our digests
        ("../escape", "adhoc-" + "a" * 32 + ".mp4"),
        ("episode-1", "a" * 32 + ".mp4.exe"),
    ],
)
def test_untrusted_paths_are_rejected(episode_id: str, filename: str) -> None:
    assert storage_key(episode_id, filename) is None


def test_storage_key_maps_cached_and_adhoc_names() -> None:
    digest = "a" * 32
    assert storage_key("episode-1", f"{digest}.mp4") == f"{CACHED_PREFIX}{digest}.mp4"
    assert (
        storage_key("episode-1", f"adhoc-{digest}.mp4")
        == f"{ADHOC_PREFIX}episode-1/adhoc-{digest}.mp4"
    )


def test_disabled_build_returns_the_honest_fallback(tmp_path: Path) -> None:
    client = build_video_client(
        enabled=False,
        client_kwargs={},
        model="veo-test",
        max_wait_seconds=5,
        bucket_name="",
        local_dir=tmp_path,
    )

    assert isinstance(client, UnavailableVideoClient)
    assert client.available is False
    result = client.generate(prompt="anything", episode_id="episode-1")
    assert result.ok is False
    assert result.error == "recovery_video_disabled"
    assert client.status()["mode"] == "fallback"
