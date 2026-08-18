from app.api.deps.agent_identity import normalize_principal, principals_from_claims
from app.main import app
from fastapi.testclient import TestClient


def test_agent_runtime_appointments_use_backend_service() -> None:
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/agent-runtime/appointments",
            params={"synthetic_user_id": "patient-synthetic-001"},
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)


def test_agent_runtime_rejects_other_patient_ids() -> None:
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/agent-runtime/appointments",
            params={"synthetic_user_id": "patient-synthetic-999"},
        )
        assert response.status_code == 403


def test_health_flags_are_not_true_from_local_catalog() -> None:
    with TestClient(app) as client:
        flags = client.get("/health").json()["adapters"]["platform_verification"]
        assert flags["managed_agent_runtime_verified"] is False
        assert flags["managed_registry_verified"] is False
        assert flags["managed_memory_bank_verified"] is False
        assert flags["managed_agent_identity_verified"] is False
        body = client.get("/api/v1/agents").json()
        names = [item.get("name") or item.get("id") for item in body]
        assert any("patient" in str(name).lower() for name in names if name)
        assert flags["managed_registry_verified"] is False


def test_runtime_status_exposes_platform_block() -> None:
    with TestClient(app) as client:
        body = client.get("/api/v1/runtime/status").json()
        assert "platform" in body["fleet"]
        assert body["fleet"]["platform"]["managed_registry_verified"] is False


def test_agent_identity_principal_normalization() -> None:
    raw = (
        "agents.global.project-658898892127.system.id.goog/resources/"
        "aiplatform/projects/1/locations/us-central1/reasoningEngines/2"
    )
    assert normalize_principal(raw).startswith("principal://")
    claims = {"email": "agent@example.com", "sub": raw}
    principals = principals_from_claims(claims)
    assert "agent@example.com" in principals
    assert normalize_principal(raw) in principals
