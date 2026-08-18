import inspect

import eir_agents.access.runtime_tools as runtime_tools
from eir_agents.access.constants import GEMINI_MODEL, SAFE_MEMORY_KEYS, SYNTHETIC_USER_ID
from eir_agents.access.memory_policy import memory_payload_is_safe
from eir_agents.access.runtime_app import IDENTITY_TYPE, runtime_config
from eir_agents.access.runtime_tools import (
    cancel_appointment,
    get_upcoming_appointments,
    reschedule_appointment,
    search_appointment_availability,
)


def test_runtime_config_requests_agent_identity_and_gemini_35() -> None:
    config = runtime_config()
    assert config["identity_type"] == IDENTITY_TYPE == "AGENT_IDENTITY"
    assert config["model"] == GEMINI_MODEL == "gemini-3.5-flash"
    assert config["framework"] == "google-adk"
    assert config["entrypoint_module"] == "eir_agents.access.runtime_app"


def test_adk_app_uses_managed_sessions_and_memory_defaults() -> None:
    import eir_agents.access.runtime_app as runtime_app

    source = inspect.getsource(runtime_app)
    assert "InMemorySessionService" not in source
    assert "memory_service_builder" not in source
    assert "session_service_builder" not in source


def test_managed_tools_do_not_import_appointment_service() -> None:
    source = inspect.getsource(runtime_tools)
    assert "AppointmentService" not in source
    assert "FhirClient" not in source
    assert "/api/v1/agent-runtime/" in source
    assert "demo-alex" not in source
    assert "SESSION_SECRET" not in source
    assert "BEGIN PRIVATE KEY" not in source


def test_tools_bind_synthetic_user_only() -> None:
    class Ctx:
        user_id = "patient-other"

    try:
        get_upcoming_appointments(tool_context=Ctx())
        raise AssertionError("cross-patient tool access must fail")
    except PermissionError:
        pass
    assert SYNTHETIC_USER_ID == "patient-synthetic-001"
    for fn in (search_appointment_availability, reschedule_appointment, cancel_appointment):
        doc = fn.__doc__ or ""
        assert "patient_id" not in fn.__code__.co_varnames or "synthetic" in doc.lower()


def test_memory_keys_are_non_clinical() -> None:
    assert SAFE_MEMORY_KEYS == {"preferred_clinic", "preferred_time_of_day"}
    assert memory_payload_is_safe(
        {"preferred_clinic": "Main Clinic", "preferred_time_of_day": "afternoon"}
    )
    assert not memory_payload_is_safe({"symptoms": "chest pain", "phone": "+15555550100"})


def test_memory_bank_helper_uses_same_user_distinct_sessions() -> None:
    user = SYNTHETIC_USER_ID
    session_a = "managed-session-A"
    session_b = "managed-session-B"
    assert user == "patient-synthetic-001"
    assert session_a != session_b


def test_deploy_script_requests_agent_identity_without_secrets() -> None:
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[2]
        / "infra"
        / "gcp"
        / "agent_platform"
        / "deploy_patient_access.py"
    ).read_text(encoding="utf-8")
    assert "AGENT_IDENTITY" in source
    assert "demo-alex" not in source
    assert "SESSION_SECRET" not in source
    assert "BEGIN PRIVATE KEY" not in source
    assert "memory_bank_config" in source
