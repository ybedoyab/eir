from app.core.deps import get_container
from app.domain.patients.models import Patient
from app.main import app
from fastapi.testclient import TestClient


def setup_function() -> None:
    get_container.cache_clear()
    container = get_container()
    container.patients.save(
        Patient(
            id="patient-synthetic-001",
            name="Alex Rivera",
            date_of_birth="1988-04-12",
            preferred_language="en",
            preferred_contact_channel="voice",
        )
    )


def test_create_recovery_episode() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/recovery",
            json={"patient_id": "patient-synthetic-001"},
        )
        assert response.status_code == 201
        body = response.json()
        assert body["patient_id"] == "patient-synthetic-001"
        assert body["status"] == "ACTIVE"
        assert body["risk_level"] == "LOW"
        assert body["id"]

        listed = client.get("/api/v1/recovery")
        assert listed.status_code == 200
        assert any(item["id"] == body["id"] for item in listed.json())

        fetched = client.get(f"/api/v1/recovery/{body['id']}")
        assert fetched.status_code == 200
        assert fetched.json()["status"] == "ACTIVE"

    bus = get_container().event_bus
    assert any(event.event_type == "RecoveryEpisodeStarted" for event in bus.published)
