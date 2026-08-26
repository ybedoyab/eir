"""Browser-dialled voice sessions: authorization and one-time-key signing."""

from __future__ import annotations

import hashlib
import json

import pytest
from app.core.config import settings
from app.core.deps import get_container
from app.main import app
from app.services.voice_web_session import web_voice_domain, web_voice_login
from fastapi.testclient import TestClient

WEB_PASSWORD = "web-test-password"


def setup_function() -> None:
    get_container.cache_clear()
    get_container().seed()


@pytest.fixture
def web_voice(monkeypatch) -> None:
    monkeypatch.setattr(settings, "voximplant_account_name", "testaccount")
    monkeypatch.setattr(settings, "voximplant_application_name", "eir-recovery")
    monkeypatch.setattr(settings, "voximplant_web_user", "eir-preview-user")
    monkeypatch.setattr(settings, "voximplant_web_password", WEB_PASSWORD)
    monkeypatch.setattr(settings, "voximplant_web_number", "eir-checkin")


@pytest.fixture
def web_voice_off(monkeypatch) -> None:
    """The unconfigured deployment, pinned.

    A developer with browser voice working locally has these in the root .env,
    so the disabled-path tests have to state the absence rather than inherit it.
    """
    monkeypatch.setattr(settings, "voximplant_web_password", "")


def _login(client: TestClient, username: str) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": f"demo-{username}"},
    )
    assert response.status_code == 200
    return response.json()["token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _episode_for(client: TestClient, patient_id: str) -> str:
    boot = client.post("/api/v1/demo/bootstrap", json={"fast_forward": False})
    assert boot.status_code == 200
    episodes = client.get("/api/v1/recovery").json()
    for episode in episodes:
        if episode["patient_id"] == patient_id:
            return episode["id"]
    raise AssertionError(f"no seeded episode for {patient_id}")


def test_config_reports_disabled_without_password(web_voice_off) -> None:
    with TestClient(app) as client:
        body = client.get("/api/v1/voice/web-session").json()
    assert body["enabled"] is False
    assert body["transport"] == "webrtc"


def test_config_exposes_login_but_never_the_password(web_voice) -> None:
    with TestClient(app) as client:
        body = client.get("/api/v1/voice/web-session").json()
    assert body["enabled"] is True
    assert body["login"] == "eir-preview-user@eir-recovery.testaccount.voximplant.com"
    assert WEB_PASSWORD not in json.dumps(body)


def test_signed_hash_matches_voximplant_onetimekey_algorithm(web_voice) -> None:
    with TestClient(app) as client:
        token = _login(client, "alex")
        patient_id = client.get("/api/v1/auth/me", headers=_auth(token)).json()["patient_id"]
        episode_id = _episode_for(client, patient_id)
        response = client.post(
            "/api/v1/voice/web-session",
            headers=_auth(token),
            json={"episode_id": episode_id, "one_time_key": "key-abc"},
        )
    assert response.status_code == 200
    body = response.json()

    # The realm is the literal "voximplant.com", per Voximplant's onetimekey
    # spec -- not the application domain. Spelled out here rather than reusing
    # the implementation's own helper, so this test can actually disagree with
    # the code it checks.
    inner = hashlib.md5(f"eir-preview-user:voximplant.com:{WEB_PASSWORD}".encode()).hexdigest()
    assert body["hash"] == hashlib.md5(f"key-abc|{inner}".encode()).hexdigest()
    assert body["login"] == web_voice_login()
    assert WEB_PASSWORD not in json.dumps(body)


def test_hash_realm_is_not_the_application_domain(web_voice) -> None:
    """Regression: the app domain in the realm yields AuthResult 401 at login.

    Both hashes are well-formed hex, so only an explicit comparison catches the
    swap -- it is invisible until Voximplant rejects the login.
    """
    with TestClient(app) as client:
        token = _login(client, "alex")
        patient_id = client.get("/api/v1/auth/me", headers=_auth(token)).json()["patient_id"]
        episode_id = _episode_for(client, patient_id)
        body = client.post(
            "/api/v1/voice/web-session",
            headers=_auth(token),
            json={"episode_id": episode_id, "one_time_key": "key-abc"},
        ).json()

    wrong_inner = hashlib.md5(
        f"eir-preview-user:{web_voice_domain()}:{WEB_PASSWORD}".encode()
    ).hexdigest()
    assert body["hash"] != hashlib.md5(f"key-abc|{wrong_inner}".encode()).hexdigest()


def test_custom_data_carries_episode_and_no_transport_claim(web_voice) -> None:
    with TestClient(app) as client:
        token = _login(client, "alex")
        patient_id = client.get("/api/v1/auth/me", headers=_auth(token)).json()["patient_id"]
        episode_id = _episode_for(client, patient_id)
        body = client.post(
            "/api/v1/voice/web-session",
            headers=_auth(token),
            json={"episode_id": episode_id, "one_time_key": "key-abc"},
        ).json()

    custom = json.loads(body["custom_data"])
    assert custom["eid"] == episode_id
    assert custom["cid"] == body["correlation_id"]
    # The scenario forces the WebRTC transport on inbound legs. The browser must
    # not be able to claim a transport, so no "t"/"u" keys are sent.
    assert set(custom) == {"eid", "cid", "n"}
    assert len(body["custom_data"].encode("utf-8")) <= 200


def test_reauthorization_without_a_key_returns_no_hash(web_voice) -> None:
    """A registered client asking for a second check-in only needs custom data."""
    with TestClient(app) as client:
        token = _login(client, "alex")
        patient_id = client.get("/api/v1/auth/me", headers=_auth(token)).json()["patient_id"]
        episode_id = _episode_for(client, patient_id)
        body = client.post(
            "/api/v1/voice/web-session",
            headers=_auth(token),
            json={"episode_id": episode_id},
        ).json()
    assert body["hash"] == ""
    assert body["number"] == "eir-checkin"
    assert json.loads(body["custom_data"])["eid"] == episode_id


def test_correlation_id_is_fresh_per_session(web_voice) -> None:
    with TestClient(app) as client:
        token = _login(client, "alex")
        patient_id = client.get("/api/v1/auth/me", headers=_auth(token)).json()["patient_id"]
        episode_id = _episode_for(client, patient_id)
        payload = {"episode_id": episode_id, "one_time_key": "key-abc"}
        first = client.post("/api/v1/voice/web-session", headers=_auth(token), json=payload).json()
        second = client.post("/api/v1/voice/web-session", headers=_auth(token), json=payload).json()
    # A stable correlation id would make a second check-in look like a replay to
    # the callback's idempotency claim.
    assert first["correlation_id"] != second["correlation_id"]


def test_anonymous_caller_rejected(web_voice) -> None:
    with TestClient(app) as client:
        episode_id = _episode_for(client, "patient-synthetic-001")
        response = client.post(
            "/api/v1/voice/web-session",
            json={"episode_id": episode_id, "one_time_key": "key-abc"},
        )
    assert response.status_code == 401


def test_clinician_cannot_open_a_patient_voice_session(web_voice) -> None:
    with TestClient(app) as client:
        episode_id = _episode_for(client, "patient-synthetic-001")
        token = _login(client, "clinician")
        response = client.post(
            "/api/v1/voice/web-session",
            headers=_auth(token),
            json={"episode_id": episode_id, "one_time_key": "key-abc"},
        )
    assert response.status_code == 403


def test_patient_cannot_dial_another_patients_episode(web_voice) -> None:
    with TestClient(app) as client:
        token = _login(client, "alex")
        patient_id = client.get("/api/v1/auth/me", headers=_auth(token)).json()["patient_id"]
        created = client.post(
            "/api/v1/recovery",
            json={"patient_id": "patient-synthetic-002"},
        )
        assert created.status_code in {200, 201}
        other_episode = created.json()["id"]
        assert created.json()["patient_id"] != patient_id
        response = client.post(
            "/api/v1/voice/web-session",
            headers=_auth(token),
            json={"episode_id": other_episode, "one_time_key": "key-abc"},
        )
    assert response.status_code == 403


def test_disabled_when_password_is_unset(web_voice_off) -> None:
    with TestClient(app) as client:
        token = _login(client, "alex")
        patient_id = client.get("/api/v1/auth/me", headers=_auth(token)).json()["patient_id"]
        episode_id = _episode_for(client, patient_id)
        response = client.post(
            "/api/v1/voice/web-session",
            headers=_auth(token),
            json={"episode_id": episode_id, "one_time_key": "key-abc"},
        )
    assert response.status_code == 503
