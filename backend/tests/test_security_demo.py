import pytest
from app.integrations.enterprise.security_demo import DEMO_MALICIOUS_PROMPT
from app.main import app
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_runtime_status_includes_model_armor_and_fleet(client: TestClient) -> None:
    response = client.get("/api/v1/runtime/status")
    assert response.status_code == 200
    body = response.json()
    assert "model_armor" in body
    assert "fleet" in body
    assert body["fleet"]["gemini_location"] == "global"


def test_security_screen_blocks_malicious_prompt(client: TestClient) -> None:
    response = client.post(
        "/api/v1/security/screen",
        json={"prompt": DEMO_MALICIOUS_PROMPT, "scenario": "prompt_injection"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["allowed"] is False
    assert body["filter_category"] == "prompt_injection"


def test_security_screen_allows_safe_prompt(client: TestClient) -> None:
    response = client.post(
        "/api/v1/security/screen",
        json={"prompt": "Routine soreness check-in", "scenario": "safe"},
    )
    assert response.status_code == 200
    assert response.json()["allowed"] is True
