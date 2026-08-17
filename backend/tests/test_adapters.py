from pathlib import Path

from app.core.config import settings
from app.core.deps import get_container
from app.domain.recovery.models import RecoveryEpisode
from app.integrations.fhir.client import GoogleHealthcareFhirClient
from app.integrations.messaging.pubsub import CompositeEventBus
from app.repositories.file_store import (
    FileRecoveryEpisodeRepository,
    FileReviewRepository,
    JsonEpisodeStore,
)
from app.repositories.recovery_repository import InMemoryRecoveryEpisodeRepository
from app.repositories.review_repository import HumanReview, InMemoryReviewRepository
from eir_agents.outreach.llm import TemplateFollowUpSummarizer
from eir_agents.records.fhir_client import LocalFhirClient
from eir_shared.event_bus import InMemoryEventBus
from eir_shared.events import FollowUpDue
from eir_shared.memory import InMemoryEpisodeStore


def setup_function() -> None:
    get_container.cache_clear()


def test_file_episode_repository_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "episodes.json"
    repo = FileRecoveryEpisodeRepository(path)
    episode = RecoveryEpisode(id="ep-1", patient_id="patient-synthetic-001")
    repo.save(episode)
    repo.append_event(episode.id, FollowUpDue(episode_id=episode.id))

    reloaded = FileRecoveryEpisodeRepository(path)
    found = reloaded.get("ep-1")
    assert found is not None
    assert found.patient_id == "patient-synthetic-001"
    events = reloaded.list_events("ep-1")
    assert events[0].event_type == "FollowUpDue"


def test_file_review_repository_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "reviews.json"
    repo = FileReviewRepository(path)
    repo.save(
        HumanReview(
            id="rev-1",
            episode_id="ep-1",
            reason="synthetic escalation",
            capability="escalation.request",
            agent_name="escalation",
        )
    )
    reloaded = FileReviewRepository(path)
    found = reloaded.get("rev-1")
    assert found is not None
    assert found.episode_id == "ep-1"


async def test_json_episode_store_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "episode-store.json"
    store = JsonEpisodeStore(path)
    await store.save("ep-1", {"last_event": "FollowUpDue"})
    reloaded = JsonEpisodeStore(path)
    assert await reloaded.get("ep-1") == {"last_event": "FollowUpDue"}


async def test_composite_bus_mirrors_and_dispatches() -> None:
    local = InMemoryEventBus()
    received: list[str] = []
    mirrored: list[str] = []

    class FakeSink:
        async def publish(self, event) -> None:
            mirrored.append(event.event_type)

    async def handler(event) -> None:
        received.append(event.event_type)

    bus = CompositeEventBus(local, FakeSink())
    bus.subscribe("FollowUpDue", handler)
    await bus.publish(FollowUpDue(episode_id="ep-1"))
    assert received == ["FollowUpDue"]
    assert mirrored == ["FollowUpDue"]


async def test_composite_bus_keeps_local_dispatch_if_sink_fails() -> None:
    local = InMemoryEventBus()
    received: list[str] = []

    class BrokenSink:
        async def publish(self, event) -> None:
            raise RuntimeError("pubsub down")

    async def handler(event) -> None:
        received.append(event.event_type)

    bus = CompositeEventBus(local, BrokenSink())
    bus.subscribe("FollowUpDue", handler)
    await bus.publish(FollowUpDue(episode_id="ep-1"))
    assert received == ["FollowUpDue"]


def test_gcp_fhir_falls_back_when_http_fails(monkeypatch) -> None:
    client = GoogleHealthcareFhirClient(
        project="eir-ata",
        location="us-central1",
        dataset="eir",
        store="fhir-r4",
        fallback=LocalFhirClient(),
    )
    monkeypatch.setattr(client, "_headers", lambda: {"Authorization": "Bearer test"})

    def boom(*_args, **_kwargs):
        raise RuntimeError("offline")

    monkeypatch.setattr("httpx.get", boom)
    patient = client.get_patient("patient-synthetic-001")
    assert patient is not None
    assert patient["id"] == "patient-synthetic-001"


def test_pytest_keeps_local_adapters_even_if_env_asks_for_gcp(monkeypatch) -> None:
    monkeypatch.setattr(settings, "episode_store", "file")
    monkeypatch.setattr(settings, "event_bus", "pubsub")
    monkeypatch.setattr(settings, "fhir_mode", "gcp")
    monkeypatch.setattr(settings, "outreach_llm", True)
    get_container.cache_clear()
    container = get_container()
    assert isinstance(container.episodes, InMemoryRecoveryEpisodeRepository)
    assert isinstance(container.reviews, InMemoryReviewRepository)
    assert isinstance(container.episode_store, InMemoryEpisodeStore)
    assert isinstance(container.event_bus, InMemoryEventBus)
    assert isinstance(container.runtime.fhir, LocalFhirClient)
    assert isinstance(container.runtime.summarizer, TemplateFollowUpSummarizer)
    get_container.cache_clear()
