from datetime import UTC, datetime

from app.core.deps import get_container
from app.main import app
from app.repositories.runtime_telemetry import InMemoryAdkRuntimeTelemetryStore
from app.services.follow_up_scheduler import FollowUpScheduler
from app.services.recovery_service import RecoveryService
from eir_shared.runtime_telemetry import AdkInvocationTelemetry
from fastapi.testclient import TestClient


def setup_function() -> None:
    get_container.cache_clear()
    get_container().seed()


def test_demo_bootstrap_schedules_future_follow_up() -> None:
    with TestClient(app) as client:
        response = client.post("/api/v1/demo/bootstrap", json={"fast_forward": False})
        assert response.status_code == 200
        body = response.json()
        assert body["patient_id"] == "patient-synthetic-001"
        assert body["patient_name"] == "Alex Rivera"
        assert body["monitoring"] is True
        assert body["fast_forwarded"] is False
        due = datetime.fromisoformat(body["next_follow_up_at"].replace("Z", "+00:00"))
        assert due > datetime.now(UTC)
        events = client.get(f"/api/v1/recovery/{body['episode_id']}/events").json()
        assert [item["event_type"] for item in events] == ["RecoveryEpisodeStarted"]


def test_demo_advance_uses_scheduler_not_direct_trigger(monkeypatch) -> None:
    calls: list[str] = []

    def boom(self, episode_id: str):  # noqa: ARG001
        raise AssertionError("demo advance must not call RecoveryService.trigger_follow_up")

    monkeypatch.setattr(RecoveryService, "trigger_follow_up", boom)
    original = FollowUpScheduler.advance_episode

    def wrapped(self, episode_id: str, *, now: datetime | None = None):
        calls.append(episode_id)
        return original(self, episode_id, now=now)

    monkeypatch.setattr(FollowUpScheduler, "advance_episode", wrapped)

    with TestClient(app) as client:
        boot = client.post("/api/v1/demo/bootstrap", json={"fast_forward": False})
        episode_id = boot.json()["episode_id"]
        advanced = client.post(f"/api/v1/demo/advance-follow-up/{episode_id}")
        assert advanced.status_code == 200
        body = advanced.json()
        assert body["advanced"] is True
        assert body["event"] == "FollowUpDue"
        assert calls == [episode_id]

        events = client.get(f"/api/v1/recovery/{episode_id}/events").json()
        assert "FollowUpDue" in [item["event_type"] for item in events]

        again = client.post(f"/api/v1/demo/advance-follow-up/{episode_id}")
        assert again.status_code == 200
        assert again.json()["advanced"] is False


def test_demo_advance_rejects_non_synthetic_episode() -> None:
    container = get_container()
    episode, _started = RecoveryService(container.episodes).create_episode(
        patient_id="patient-not-synthetic",
    )
    with TestClient(app) as client:
        response = client.post(f"/api/v1/demo/advance-follow-up/{episode.id}")
        assert response.status_code == 403


def test_demo_duplicate_prompt_injection_and_concerning() -> None:
    with TestClient(app) as client:
        boot = client.post("/api/v1/demo/bootstrap", json={"fast_forward": False})
        episode_id = boot.json()["episode_id"]

        first_attack = client.post(f"/api/v1/security/demo/prompt-injection/{episode_id}")
        assert first_attack.status_code == 200
        second_attack = client.post(f"/api/v1/security/demo/prompt-injection/{episode_id}")
        assert second_attack.status_code == 409

        first_signal = client.post(f"/api/v1/demo/concerning-signal/{episode_id}")
        assert first_signal.status_code == 200
        second_signal = client.post(f"/api/v1/demo/concerning-signal/{episode_id}")
        assert second_signal.status_code == 409


def test_runtime_history_filters_by_episode_id() -> None:
    store = InMemoryAdkRuntimeTelemetryStore()
    store.record(
        AdkInvocationTelemetry(
            timestamp="2026-08-18T00:00:00Z",
            service="eir-worker",
            model="gemini-3.5-flash",
            model_location="global",
            capability="patient.contact",
            agent_name="outreach_agent",
            episode_id="ep-demo",
            trace_id="trace-demo",
            tools_invoked=["conduct_outreach"],
            success=True,
            used_direct_fallback=False,
        )
    )
    store.record(
        AdkInvocationTelemetry(
            timestamp="2026-08-18T00:00:01Z",
            service="eir-worker",
            model="gemini-3.5-flash",
            model_location="global",
            capability="risk.assess",
            agent_name="risk_agent",
            episode_id="ep-other",
            trace_id="trace-other",
            tools_invoked=["assess_patient_response"],
            success=True,
            used_direct_fallback=False,
        )
    )
    filtered = store.history(limit=25, episode_id="ep-demo")
    assert len(filtered) == 1
    assert filtered[0]["agent_name"] == "outreach_agent"
    unfiltered = store.history(limit=25)
    assert len(unfiltered) == 2

    container = get_container()
    container.adk_telemetry.record(
        AdkInvocationTelemetry(
            timestamp="2026-08-18T00:00:00Z",
            service="eir-worker",
            model="gemini-3.5-flash",
            model_location="global",
            capability="patient.contact",
            agent_name="outreach_agent",
            episode_id="ep-api",
            trace_id="trace-api",
            tools_invoked=["conduct_outreach"],
            success=True,
            used_direct_fallback=False,
        )
    )
    container.adk_telemetry.record(
        AdkInvocationTelemetry(
            timestamp="2026-08-18T00:00:01Z",
            service="eir-worker",
            model="gemini-3.5-flash",
            model_location="global",
            capability="risk.assess",
            agent_name="risk_agent",
            episode_id="ep-noise",
            trace_id="trace-noise",
            tools_invoked=["assess_patient_response"],
            success=True,
            used_direct_fallback=False,
        )
    )
    with TestClient(app) as client:
        scoped = client.get("/api/v1/runtime/history?limit=25&episode_id=ep-api")
        assert scoped.status_code == 200
        items = scoped.json()["items"]
        assert len(items) == 1
        assert items[0]["episode_id"] == "ep-api"
        global_history = client.get("/api/v1/runtime/history?limit=25")
        assert len(global_history.json()["items"]) >= 2
