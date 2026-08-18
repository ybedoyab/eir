from app.main import app
from fastapi.testclient import TestClient


def test_health() -> None:
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["adapters"]["event_bus"] == "memory"
        assert body["adapters"]["episode_store"] == "memory"
        assert body["adapters"]["fhir_mode"] == "local"
        assert body["adapters"]["otel"]["capture_message_content_in_spans"] is False
        flags = body["adapters"]["platform_verification"]
        assert flags["managed_agent_runtime_verified"] is False
        assert flags["managed_model_armor_verified"] is False
        assert flags["otel_cloud_trace_verified"] is False
