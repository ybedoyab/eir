from pathlib import Path

from app.core.config import settings
from app.core.deps import get_container
from app.domain.recovery.models import RecoveryEpisode
from app.integrations.fhir.client import GoogleHealthcareFhirClient
from app.integrations.messaging.pubsub import CompositeEventBus, decode_pubsub_payload
from app.repositories.file_store import (
    FileRecoveryEpisodeRepository,
    FileReviewRepository,
    FileStructuredLogger,
    JsonEpisodeStore,
)
from app.repositories.firestore_store import (
    FirestoreEpisodeStore,
    FirestoreRecoveryEpisodeRepository,
    FirestoreReviewRepository,
)
from app.repositories.recovery_repository import InMemoryRecoveryEpisodeRepository
from app.repositories.review_repository import HumanReview, InMemoryReviewRepository
from eir_agents.outreach.llm import TemplateFollowUpSummarizer
from eir_agents.records.fhir_client import LocalFhirClient
from eir_shared.event_bus import InMemoryEventBus
from eir_shared.events import FollowUpDue
from eir_shared.memory import InMemoryEpisodeStore
from eir_shared.observability import WorkflowTrace


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


class _FakeResponse:
    def __init__(self, status_code: int = 200, payload: dict | None = None) -> None:
        self.status_code = status_code
        self._payload = payload if payload is not None else {}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"http {self.status_code}")

    def json(self) -> dict:
        return self._payload


def test_gcp_fhir_empty_store_skips_fixtures_when_fallback_disabled(monkeypatch) -> None:
    client = GoogleHealthcareFhirClient(
        project="eir-ata",
        location="us-central1",
        dataset="eir",
        store="fhir-r4",
        fallback=LocalFhirClient(),
        fallback_on_miss=False,
    )
    monkeypatch.setattr(client, "_headers", lambda: {"Authorization": "Bearer test"})

    def fake_get(url: str, **_kwargs):
        if "/Patient/" in url:
            return _FakeResponse(404)
        return _FakeResponse(200, {"entry": []})

    monkeypatch.setattr("httpx.get", fake_get)
    assert client.get_patient("patient-synthetic-001") is None
    assert client.get_encounters("patient-synthetic-001") == []
    assert client.reachable is True


def test_decode_pubsub_payload_roundtrip() -> None:
    event = FollowUpDue(episode_id="ep-1")
    decoded = decode_pubsub_payload(event.model_dump_json().encode("utf-8"))
    assert decoded.event_type == "FollowUpDue"
    assert decoded.episode_id == "ep-1"


def test_file_structured_logger_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "traces.json"
    logger = FileStructuredLogger("eir-test", path)
    logger.emit(
        WorkflowTrace(
            workflow_id="ep-1",
            episode_id="ep-1",
            trace_id="tr-1",
            agent_name="outreach",
            event_type="FollowUpDue",
            status="delegated",
        )
    )
    reloaded = FileStructuredLogger("eir-test", path)
    assert reloaded.records[0].trace_id == "tr-1"


class _FakeSnapshot:
    def __init__(self, data: dict | None) -> None:
        self._data = data
        self.exists = data is not None

    def to_dict(self) -> dict | None:
        return dict(self._data) if self._data is not None else None


class _FakeDocument:
    def __init__(self, store: dict, doc_id: str) -> None:
        self._store = store
        self._id = doc_id

    def get(self) -> _FakeSnapshot:
        return _FakeSnapshot(self._store.get(self._id))

    def set(self, data: dict, merge: bool = False) -> None:
        if merge and self._id in self._store:
            self._store[self._id] = {**self._store[self._id], **data}
        else:
            self._store[self._id] = dict(data)


class _FakeCollection:
    def __init__(self) -> None:
        self._store: dict[str, dict] = {}

    def document(self, doc_id: str) -> _FakeDocument:
        return _FakeDocument(self._store, doc_id)

    def stream(self):
        return [_FakeSnapshot(value) for value in self._store.values()]


class _FakeFirestore:
    def __init__(self) -> None:
        self._cols: dict[str, _FakeCollection] = {}

    def collection(self, name: str) -> _FakeCollection:
        return self._cols.setdefault(name, _FakeCollection())


def test_firestore_episode_repository_roundtrip() -> None:
    client = _FakeFirestore()
    repo = FirestoreRecoveryEpisodeRepository(client)
    episode = RecoveryEpisode(id="ep-1", patient_id="patient-synthetic-001")
    repo.save(episode)
    repo.append_event(episode.id, FollowUpDue(episode_id=episode.id))
    found = repo.get("ep-1")
    assert found is not None
    assert found.patient_id == "patient-synthetic-001"
    assert repo.list_events("ep-1")[0].event_type == "FollowUpDue"


async def test_firestore_episode_store_and_reviews() -> None:
    client = _FakeFirestore()
    store = FirestoreEpisodeStore(client)
    await store.save("ep-1", {"last_event": "FollowUpDue"})
    assert await store.get("ep-1") == {"last_event": "FollowUpDue"}
    reviews = FirestoreReviewRepository(client)
    reviews.save(
        HumanReview(
            id="rev-1",
            episode_id="ep-1",
            reason="synthetic escalation",
            capability="escalation.request",
            agent_name="escalation",
        )
    )
    assert reviews.get("rev-1") is not None
    assert reviews.for_episode("ep-1")[0].id == "rev-1"
