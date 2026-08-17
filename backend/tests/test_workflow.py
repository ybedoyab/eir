from app.core.deps import get_container
from app.main import app
from fastapi.testclient import TestClient


def setup_function() -> None:
    get_container.cache_clear()
    get_container().seed()


def test_follow_up_loop_keeps_low_risk_waiting() -> None:
    with TestClient(app) as client:
        created = client.post(
            "/api/v1/recovery",
            json={"patient_id": "patient-synthetic-001"},
        )
        assert created.status_code == 201
        episode_id = created.json()["id"]
        assert created.json()["status"] == "ACTIVE"

        follow_up = client.post(f"/api/v1/recovery/{episode_id}/follow-up")
        assert follow_up.status_code == 200

        episode = client.get(f"/api/v1/recovery/{episode_id}").json()
        assert episode["status"] == "WAITING"
        assert episode["risk_level"] == "LOW"
        assert "outreach" in episode["assigned_agents"]

        events = client.get(f"/api/v1/recovery/{episode_id}/events").json()
        types = [item["event_type"] for item in events]
        assert "RecoveryEpisodeStarted" in types
        assert "FollowUpDue" in types
        assert "PatientResponded" in types
        assert "RiskEscalated" not in types

        traces = client.get("/api/v1/traces").json()
        assert any(item["episode_id"] == episode_id for item in traces)


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
        review_id = pending[0]["id"]

        resolved = client.post(
            f"/api/v1/reviews/{review_id}/resolve",
            json={"note": "clinician reviewed synthetic follow-up"},
        )
        assert resolved.status_code == 200
        assert resolved.json()["status"] == "resolved"

        resumed = client.get(f"/api/v1/recovery/{episode_id}").json()
        assert resumed["status"] == "ACTIVE"
