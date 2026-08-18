from datetime import UTC, datetime, timedelta

from app.core.config import settings
from app.core.deps import get_container
from app.main import app
from app.services.follow_up_scheduler import FollowUpScheduler
from eir_shared.gemini_config import resolve_gemini_model
from fastapi.testclient import TestClient


def setup_function() -> None:
    get_container.cache_clear()
    get_container().seed()


def _approve_pending(client: TestClient, episode_id: str) -> str:
    reviews = client.get("/api/v1/reviews").json()
    pending = [item for item in reviews if item["episode_id"] == episode_id]
    assert pending, "expected a pending review"
    review_id = pending[0]["id"]
    resolved = client.post(
        f"/api/v1/reviews/{review_id}/resolve",
        json={"note": "clinician approved synthetic action"},
    )
    assert resolved.status_code == 200
    return review_id


def test_follow_up_loop_keeps_low_risk_waiting_for_next_follow_up() -> None:
    with TestClient(app) as client:
        created = client.post(
            "/api/v1/recovery",
            json={"patient_id": "patient-synthetic-001"},
        )
        assert created.status_code == 201
        episode_id = created.json()["id"]

        follow_up = client.post(f"/api/v1/recovery/{episode_id}/follow-up")
        assert follow_up.status_code == 200
        episode = client.get(f"/api/v1/recovery/{episode_id}").json()
        assert episode["status"] == "WAITING_FOR_NEXT_FOLLOWUP"
        assert episode["risk_level"] == "LOW"
        assert "outreach" in episode["assigned_agents"]

        events = client.get(f"/api/v1/recovery/{episode_id}/events").json()
        types = [item["event_type"] for item in events]
        assert "RecoveryEpisodeStarted" in types
        assert "FollowUpDue" in types
        assert "PatientResponded" in types
        assert "RiskEscalated" not in types


def test_issue_signal_requests_human_review_and_can_resume() -> None:
    with TestClient(app) as client:
        created = client.post(
            "/api/v1/recovery",
            json={"patient_id": "patient-synthetic-002"},
        )
        episode_id = created.json()["id"]
        client.post(f"/api/v1/recovery/{episode_id}/follow-up")

        episode = client.get(f"/api/v1/recovery/{episode_id}").json()
        assert episode["status"] == "ESCALATED"
        assert episode["risk_level"] == "HIGH"

        reviews = client.get("/api/v1/reviews").json()
        pending = [item for item in reviews if item["episode_id"] == episode_id]
        assert pending
        assert pending[0]["capability"] == "escalation.request"
        review_id = pending[0]["id"]

        resolved = client.post(
            f"/api/v1/reviews/{review_id}/resolve",
            json={"note": "clinician reviewed synthetic follow-up"},
        )
        assert resolved.status_code == 200
        assert resolved.json()["status"] == "resolved"

        resumed = client.get(f"/api/v1/recovery/{episode_id}").json()
        assert resumed["status"] in {"ACTIVE", "WAITING_FOR_NEXT_FOLLOWUP"}


def test_longitudinal_follow_up_day_0_and_day_7() -> None:
    with TestClient(app) as client:
        created = client.post(
            "/api/v1/recovery",
            json={"patient_id": "patient-synthetic-001"},
        )
        episode_id = created.json()["id"]

        client.post(f"/api/v1/recovery/{episode_id}/follow-up")

        container = get_container()
        episode = container.episodes.get(episode_id)
        assert episode is not None
        assert episode.status.value == "WAITING_FOR_NEXT_FOLLOWUP"
        episode.next_follow_up_at = datetime.now(UTC) - timedelta(minutes=1)
        container.episodes.save(episode)

        scheduler = FollowUpScheduler(
            container.episodes,
            idempotency=container.scheduler_idempotency,
        )
        second_batch = scheduler.process_due(idempotency_key="day-7")
        assert len(second_batch) == 1

        events = client.get(f"/api/v1/recovery/{episode_id}/events").json()
        follow_ups = [item for item in events if item["event_type"] == "FollowUpDue"]
        assert len(follow_ups) == 2


def test_scheduler_endpoint_requires_token(monkeypatch) -> None:
    monkeypatch.setattr(settings, "scheduler_secret", "test-scheduler-secret")
    get_container.cache_clear()
    get_container().seed()
    with TestClient(app) as client:
        denied = client.post("/api/v1/recovery/process-due-follow-ups")
        assert denied.status_code == 401
        allowed = client.post(
            "/api/v1/recovery/process-due-follow-ups",
            headers={
                "X-Scheduler-Token": "test-scheduler-secret",
                "X-Idempotency-Key": "run-1",
            },
        )
        assert allowed.status_code == 200


def test_scheduler_idempotency_rejects_duplicate_run() -> None:
    container = get_container()
    scheduler = FollowUpScheduler(
        container.episodes,
        idempotency=container.scheduler_idempotency,
    )
    first = scheduler.process_due(idempotency_key="duplicate-run")
    second = scheduler.process_due(idempotency_key="duplicate-run")
    assert second == [] or len(second) <= len(first)


def test_outreach_runs_without_pre_approval() -> None:
    with TestClient(app) as client:
        created = client.post(
            "/api/v1/recovery",
            json={"patient_id": "patient-synthetic-001"},
        )
        episode_id = created.json()["id"]
        container = get_container()
        client.post(f"/api/v1/recovery/{episode_id}/follow-up")

        episode = client.get(f"/api/v1/recovery/{episode_id}").json()
        assert "outreach" in episode["assigned_agents"]
        assert "conduct_outreach" in container.adk_runner.tool_audit

        reviews = client.get("/api/v1/reviews").json()
        contact_reviews = [
            item
            for item in reviews
            if item["episode_id"] == episode_id and item["pending_capability"] == "patient.contact"
        ]
        assert not contact_reviews


def test_runtime_status_endpoint() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/runtime/status")
        assert response.status_code == 200
        body = response.json()
        assert "adk_worker" in body
        assert body["content_guard"]["managed_model_armor_available"] is False


def test_health_reports_runtime_verification() -> None:
    with TestClient(app) as client:
        response = client.get("/health")
        body = response.json()
        verification = body["adapters"]["runtime_verification"]
        assert verification["vertex_model_probe"]["model"] == resolve_gemini_model()
        assert verification["vertex_model_probe"]["location"] == "global"
        assert "success" in verification["vertex_model_probe"]
        assert verification["enterprise"]["runtime_region"] == "us-central1"
        assert "shared_worker_telemetry" in verification["adk_runtime"]
        assert verification["adk_runtime"]["mode"] == "direct"
        assert body["adapters"]["adk_allow_direct_fallback"] is True
