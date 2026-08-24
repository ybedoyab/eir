"""Regression tests for synthetic and Voximplant voice outreach. No paid PSTN calls."""

from __future__ import annotations

import json
from uuid import uuid4

from app.core.config import settings
from app.core.deps import get_container
from app.integrations.voice.providers import (
    SyntheticVoiceProvider,
    VoximplantVoiceProvider,
    voice_provider,
)
from app.main import app
from eir_agents.outreach.handler import handle_follow_up
from eir_shared.events import FollowUpDue, PatientResponded
from fastapi.testclient import TestClient

DEMO_PHONE = "+15555550199"
CALLER_ID = "+15555550100"


class FakeVoxAPI:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def call(self, method: str, **params):
        self.calls.append((method, params))
        if method == "StartScenarios":
            custom = json.loads(params["script_custom_data"])
            assert "eid" in custom
            assert "cid" in custom
            assert DEMO_PHONE not in params["script_custom_data"]
            assert CALLER_ID not in params["script_custom_data"]
            return {"result": {"media_session_access_url": "session-1"}}
        return {"result": {}}


def setup_function() -> None:
    get_container.cache_clear()
    get_container().seed()


def _headers(token: str = "voice-test-token") -> dict[str, str]:
    return {"X-EIR-Voice-Token": token, "Content-Type": "application/json"}


def test_synthetic_voice_provider_still_sync() -> None:
    provider = SyntheticVoiceProvider()
    assert provider.mode == "sync"
    assert provider.provider_name == "synthetic"


def test_synthetic_alex_conversation_reports_missed_medications() -> None:
    import asyncio

    result = asyncio.run(
        handle_follow_up(
            FollowUpDue(episode_id="ep-synthetic-alex"),
            patient_id="patient-synthetic-001",
            voice=SyntheticVoiceProvider(),
        )
    )
    responded = next(event for event in result.next_events if isinstance(event, PatientResponded))
    assert responded.payload["pain_score"] == 2
    assert responded.payload["medication_adherence"] == "no"


def test_voximplant_start_scenarios_custom_data(monkeypatch) -> None:
    api = FakeVoxAPI()
    provider = VoximplantVoiceProvider(
        api=api,
        rule_id=42,
        application_id=7,
        demo_phone_e164=DEMO_PHONE,
        caller_id_e164=CALLER_ID,
    )
    import asyncio

    result = asyncio.run(
        provider.start_outbound_call(
            to="synthetic:patient-synthetic-001",
            episode_id="ep-1",
            patient_id="patient-synthetic-001",
            metadata={"patient_display_name": "Alex"},
        )
    )
    assert result.mode == "async"
    assert result.conversation is None
    assert api.calls[0][0] == "StartScenarios"
    params = api.calls[0][1]
    assert params["rule_id"] == 42
    custom = json.loads(params["script_custom_data"])
    # "o" marks this as a StartScenarios launch, which is what lets the scenario's
    # Started handler tell an outbound dial from a browser leg's custom data.
    assert set(custom) <= {"eid", "cid", "n", "o"}
    assert custom["eid"] == "ep-1"
    assert custom["o"] == 1


def test_admin_credentials_not_used_by_runtime_factory(monkeypatch) -> None:
    monkeypatch.setenv("VOXIMPLANT_CREDENTIALS", "admin-should-not-be-read.json")
    try:
        voice_provider("voximplant", credentials_source="", rule_id="1")
        raise AssertionError("runtime must require VOXIMPLANT_RUNTIME_CREDENTIALS")
    except RuntimeError as exc:
        assert "VOXIMPLANT_RUNTIME_CREDENTIALS" in str(exc)


def test_production_voximplant_still_requires_phone_secrets() -> None:
    provider = VoximplantVoiceProvider(
        api=FakeVoxAPI(),
        rule_id=1,
        demo_phone_e164="",
        caller_id_e164="",
    )
    import asyncio

    try:
        asyncio.run(
            provider.start_outbound_call(
                to="synthetic:patient-synthetic-001",
                episode_id="ep-1",
                patient_id="patient-synthetic-001",
            )
        )
        raise AssertionError("production PSTN must require destination and caller ID")
    except RuntimeError as exc:
        assert "not configured" in str(exc)


def test_synthetic_only_restriction() -> None:
    provider = VoximplantVoiceProvider(
        api=FakeVoxAPI(),
        rule_id=1,
        demo_phone_e164=DEMO_PHONE,
        caller_id_e164=CALLER_ID,
    )
    import asyncio

    try:
        asyncio.run(
            provider.start_outbound_call(
                to="synthetic:patient-real-001",
                episode_id="ep-1",
                patient_id="patient-real-001",
            )
        )
        raise AssertionError("non-synthetic PSTN must be denied")
    except PermissionError:
        pass


def test_async_follow_up_does_not_create_patient_responded() -> None:
    import asyncio

    result = asyncio.run(
        handle_follow_up(
            FollowUpDue(episode_id="ep-async"),
            patient_id="patient-synthetic-001",
            voice=VoximplantVoiceProvider(
                api=FakeVoxAPI(),
                rule_id=9,
                demo_phone_e164=DEMO_PHONE,
                caller_id_e164=CALLER_ID,
            ),
        )
    )
    assert [event.event_type for event in result.next_events] == ["VoiceCallStarted"]
    assert not any(isinstance(event, PatientResponded) for event in result.next_events)


def test_callback_invalid_token_rejected(monkeypatch) -> None:
    monkeypatch.setattr(settings, "voximplant_callback_token", "voice-test-token")
    with TestClient(app) as client:
        boot = client.post("/api/v1/demo/bootstrap", json={"fast_forward": False})
        episode_id = boot.json()["episode_id"]
        denied = client.post(
            "/api/v1/voice/voximplant/callback",
            headers=_headers("wrong"),
            json={
                "episode_id": episode_id,
                "correlation_id": str(uuid4()),
                "state": "CALL_COMPLETED",
                "pain_score": 8,
                "reported_issue": True,
            },
        )
        assert denied.status_code == 401


def test_completed_callback_publishes_patient_responded(monkeypatch) -> None:
    monkeypatch.setattr(settings, "voximplant_callback_token", "voice-test-token")
    with TestClient(app) as client:
        boot = client.post("/api/v1/demo/bootstrap", json={"fast_forward": False})
        episode_id = boot.json()["episode_id"]
        correlation = str(uuid4())
        completed = client.post(
            "/api/v1/voice/voximplant/callback",
            headers=_headers(),
            json={
                "episode_id": episode_id,
                "correlation_id": correlation,
                "state": "CALL_COMPLETED",
                "call_id": "call-1",
                "pain_score": 8,
                "reported_issue": True,
                "issue_summary": "new swelling near incision",
                "symptoms_worsening": True,
                "medication_adherence": "unknown",
                "patient_requests_clinician": False,
                "call_outcome": "completed",
                "transcript": (
                    "EIR: How is your pain from 0 to 10?\n"
                    "Patient: It is an 8 and the swelling is worse."
                ),
            },
        )
        assert completed.status_code == 200
        body = completed.json()
        assert body["duplicate"] is False
        assert "PatientResponded" in body["published"]
        events = client.get(f"/api/v1/recovery/{episode_id}/events").json()
        types = [item["event_type"] for item in events]
        assert "VoiceCallCompleted" in types
        assert "PatientResponded" in types
        assert "RiskEscalated" in types
        assert "HumanReviewRequested" in types
        assert "AdherenceConcernDetected" not in types
        payloads = json.dumps(events)
        assert DEMO_PHONE not in payloads
        assert CALLER_ID not in payloads
        responded = next(item for item in events if item["event_type"] == "PatientResponded")
        completed_event = next(
            item for item in events if item["event_type"] == "VoiceCallCompleted"
        )
        assert responded["payload"]["pain_score"] == 8
        assert "transcript" not in responded["payload"]
        assert "transcript" not in completed_event["payload"]
        assert "issue_summary" in responded["payload"]


def test_callback_adherence_no_on_critical_medication_escalates(monkeypatch) -> None:
    monkeypatch.setattr(settings, "voximplant_callback_token", "voice-test-token")
    with TestClient(app) as client:
        boot = client.post("/api/v1/demo/bootstrap", json={"fast_forward": False})
        episode_id = boot.json()["episode_id"]
        completed = client.post(
            "/api/v1/voice/voximplant/callback",
            headers=_headers(),
            json={
                "episode_id": episode_id,
                "correlation_id": str(uuid4()),
                "state": "CALL_COMPLETED",
                "pain_score": 2,
                "reported_issue": False,
                "issue_summary": "Feeling better",
                "medication_adherence": "no",
                "call_outcome": "completed",
            },
        )
        assert completed.status_code == 200
        events = client.get(f"/api/v1/recovery/{episode_id}/events").json()
        types = [item["event_type"] for item in events]
        assert "AdherenceConcernDetected" in types
        assert "RiskEscalated" in types
        assert "HumanReviewRequested" in types
        episode = client.get(f"/api/v1/recovery/{episode_id}").json()
        assert "adherence" in episode["assigned_agents"]
        assert episode["status"] == "ESCALATED"


def test_callback_adherence_no_on_non_critical_does_not_escalate(monkeypatch) -> None:
    monkeypatch.setattr(settings, "voximplant_callback_token", "voice-test-token")
    with TestClient(app) as client:
        created = client.post(
            "/api/v1/recovery",
            json={"patient_id": "patient-synthetic-002"},
        )
        episode_id = created.json()["id"]
        completed = client.post(
            "/api/v1/voice/voximplant/callback",
            headers=_headers(),
            json={
                "episode_id": episode_id,
                "correlation_id": str(uuid4()),
                "state": "CALL_COMPLETED",
                "pain_score": 2,
                "reported_issue": False,
                "medication_adherence": "no",
                "call_outcome": "completed",
            },
        )
        assert completed.status_code == 200
        events = client.get(f"/api/v1/recovery/{episode_id}/events").json()
        types = [item["event_type"] for item in events]
        assert "AdherenceConcernDetected" in types
        assert "RiskEscalated" not in types
        episode = client.get(f"/api/v1/recovery/{episode_id}").json()
        assert episode["status"] != "ESCALATED"


def test_duplicate_callback_is_idempotent(monkeypatch) -> None:
    monkeypatch.setattr(settings, "voximplant_callback_token", "voice-test-token")
    with TestClient(app) as client:
        boot = client.post("/api/v1/demo/bootstrap", json={"fast_forward": False})
        episode_id = boot.json()["episode_id"]
        correlation = str(uuid4())
        payload = {
            "episode_id": episode_id,
            "correlation_id": correlation,
            "state": "CALL_COMPLETED",
            "pain_score": 8,
            "reported_issue": True,
            "issue_summary": "swelling",
            "call_outcome": "completed",
        }
        first = client.post("/api/v1/voice/voximplant/callback", headers=_headers(), json=payload)
        second = client.post("/api/v1/voice/voximplant/callback", headers=_headers(), json=payload)
        assert first.status_code == 200
        assert second.status_code == 200
        assert second.json()["duplicate"] is True
        events = client.get(f"/api/v1/recovery/{episode_id}/events").json()
        responded = [item for item in events if item["event_type"] == "PatientResponded"]
        assert len(responded) == 1


def test_voice_context_returns_alex_medications(monkeypatch) -> None:
    monkeypatch.setattr(settings, "voximplant_callback_token", "voice-test-token")
    with TestClient(app) as client:
        boot = client.post("/api/v1/demo/bootstrap", json={"fast_forward": False})
        episode_id = boot.json()["episode_id"]
        denied = client.get(f"/api/v1/voice/context?episode_id={episode_id}")
        assert denied.status_code == 401
        response = client.get(
            f"/api/v1/voice/context?episode_id={episode_id}",
            headers=_headers(),
        )
        assert response.status_code == 200
        skus = {item["sku"] for item in response.json()["medications"]}
        assert "MED-ENOX-40" in skus
        assert "MED-PARA-500" in skus


def test_callback_per_medication_taken_false_marks_adherence_no(monkeypatch) -> None:
    monkeypatch.setattr(settings, "voximplant_callback_token", "voice-test-token")
    with TestClient(app) as client:
        boot = client.post("/api/v1/demo/bootstrap", json={"fast_forward": False})
        episode_id = boot.json()["episode_id"]
        completed = client.post(
            "/api/v1/voice/voximplant/callback",
            headers=_headers(),
            json={
                "episode_id": episode_id,
                "correlation_id": str(uuid4()),
                "state": "CALL_COMPLETED",
                "pain_score": 2,
                "reported_issue": False,
                "medication_adherence": "yes",
                "medications": [
                    {"sku": "MED-ENOX-40", "taken": False},
                    {"sku": "MED-PARA-500", "taken": True},
                ],
                "call_outcome": "completed",
            },
        )
        assert completed.status_code == 200
        events = client.get(f"/api/v1/recovery/{episode_id}/events").json()
        responded = next(item for item in events if item["event_type"] == "PatientResponded")
        assert responded["payload"]["medication_adherence"] == "no"
        assert "AdherenceConcernDetected" in [item["event_type"] for item in events]


def test_failed_call_does_not_publish_patient_responded(monkeypatch) -> None:
    monkeypatch.setattr(settings, "voximplant_callback_token", "voice-test-token")
    with TestClient(app) as client:
        boot = client.post("/api/v1/demo/bootstrap", json={"fast_forward": False})
        episode_id = boot.json()["episode_id"]
        failed = client.post(
            "/api/v1/voice/voximplant/callback",
            headers=_headers(),
            json={
                "episode_id": episode_id,
                "correlation_id": str(uuid4()),
                "state": "NO_ANSWER",
                "failure_reason": "no_answer",
            },
        )
        assert failed.status_code == 200
        events = client.get(f"/api/v1/recovery/{episode_id}/events").json()
        types = [item["event_type"] for item in events]
        assert "VoiceCallFailed" in types
        assert "PatientResponded" not in types


def test_callback_rejects_non_synthetic_episode(monkeypatch) -> None:
    monkeypatch.setattr(settings, "voximplant_callback_token", "voice-test-token")
    container = get_container()
    from app.services.recovery_service import RecoveryService

    episode, _started = RecoveryService(container.episodes).create_episode(
        patient_id="patient-not-synthetic",
    )
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/voice/voximplant/callback",
            headers=_headers(),
            json={
                "episode_id": episode.id,
                "correlation_id": str(uuid4()),
                "state": "CALL_COMPLETED",
                "pain_score": 2,
                "reported_issue": False,
            },
        )
        assert response.status_code == 403


def test_runtime_status_exposes_voice_honestly() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/runtime/status")
        assert response.status_code == 200
        voice = response.json()["fleet"]["voice"]
        assert voice["active_provider"] == "mock"
        assert voice["admin_credentials_used_at_runtime"] is False
        assert voice["synthetic_patients_only"] is True
        assert voice["voice_transport"] == "pstn"
        assert "destination" not in voice
        assert DEMO_PHONE not in json.dumps(voice)
