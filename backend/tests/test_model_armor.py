from unittest.mock import MagicMock, patch

from app.integrations.enterprise.model_armor import RegexContentGuardFallback
from app.integrations.enterprise.security_demo import (
    DEMO_MALICIOUS_PROMPT,
    DEMO_SAFE_PROMPT,
    screen_demo_prompt,
)
from app.integrations.enterprise.vertex_model_armor import (
    VertexModelArmorAdapter,
    build_content_guard,
    managed_model_armor_available,
)
from eir_agents.safety.handler import SafetyGate
from eir_shared.capabilities import Capability
from eir_shared.identity import AgentIdentity


def _adapter() -> VertexModelArmorAdapter:
    return VertexModelArmorAdapter(
        project="test-project",
        location="us-central1",
        template="eir-agent-guard",
        fallback=RegexContentGuardFallback(),
    )


def _managed_response(*, match: bool) -> MagicMock:
    mock_result = MagicMock()
    mock_result.filter_match_state = "MATCH_FOUND" if match else "NO_MATCH_FOUND"
    if match:
        pi = MagicMock()
        pi.match_state = "MATCH_FOUND"
        mock_result.filter_results = {"pi_and_jailbreak": pi}
    else:
        mock_result.filter_results = {}
        mock_result.sanitization_metadata = MagicMock(sanitized_text=DEMO_SAFE_PROMPT)
    mock_response = MagicMock()
    mock_response.sanitization_result = mock_result
    return mock_response


def test_managed_model_armor_sdk_available_after_install() -> None:
    assert managed_model_armor_available() is True


def test_build_content_guard_uses_regex_when_not_preferred() -> None:
    guard = build_content_guard(
        project="test-project",
        location="us-central1",
        template="eir-agent-guard",
        prefer_managed=False,
    )
    assert guard.adapter_name == "regex_fallback"
    assert guard.status()["mode"] == "fallback"
    assert guard.status()["configured"] is False


def test_managed_adapter_blocks_prompt_injection_match() -> None:
    adapter = _adapter()
    with patch.object(adapter, "_client_instance") as client_factory:
        client_factory.return_value.sanitize_user_prompt.return_value = _managed_response(
            match=True
        )
        decision = adapter.inspect_ingress(DEMO_MALICIOUS_PROMPT)

    assert decision.allowed is False
    assert decision.adapter == "google_model_armor"
    assert decision.filter_category
    assert adapter.status()["mode"] == "managed"
    assert adapter.status()["last_screening_success"] is True
    assert adapter.status()["last_decision_adapter"] == "google_model_armor"
    assert adapter.status()["last_blocked"] is True


def test_managed_adapter_allows_clean_prompt() -> None:
    adapter = _adapter()
    with patch.object(adapter, "_client_instance") as client_factory:
        client_factory.return_value.sanitize_user_prompt.return_value = _managed_response(
            match=False
        )
        decision = adapter.inspect_ingress(DEMO_SAFE_PROMPT)

    assert decision.allowed is True
    assert decision.adapter == "google_model_armor"
    assert adapter.status()["mode"] == "managed"
    assert adapter.status()["last_blocked"] is False


def test_managed_adapter_returns_to_managed_after_degraded_call() -> None:
    adapter = _adapter()
    with patch.object(adapter, "_client_instance") as client_factory:
        client_factory.return_value.sanitize_user_prompt.side_effect = RuntimeError("api down")
        degraded = adapter.inspect_ingress(DEMO_SAFE_PROMPT)
        assert degraded.degraded is True
        assert adapter.status()["mode"] == "degraded"
        client_factory.return_value.sanitize_user_prompt.side_effect = None
        client_factory.return_value.sanitize_user_prompt.return_value = _managed_response(
            match=False
        )
        recovered = adapter.inspect_ingress(DEMO_SAFE_PROMPT)

    assert recovered.adapter == "google_model_armor"
    assert adapter.status()["mode"] == "managed"
    assert adapter.status()["last_screening_success"] is True
    assert adapter.status()["last_decision_adapter"] == "google_model_armor"


def test_managed_adapter_falls_back_on_api_error() -> None:
    adapter = _adapter()
    with patch.object(adapter, "_client_instance") as client_factory:
        client_factory.return_value.sanitize_user_prompt.side_effect = RuntimeError("api down")
        decision = adapter.inspect_ingress(DEMO_SAFE_PROMPT)

    assert decision.allowed is True
    assert decision.adapter == "regex_fallback"
    assert decision.degraded is True
    assert adapter.status()["mode"] == "degraded"
    assert adapter.status()["last_screening_success"] is False


def test_patient_contact_may_use_regex_when_managed_unavailable() -> None:
    adapter = _adapter()
    with patch.object(adapter, "_client_instance") as client_factory:
        client_factory.return_value.sanitize_user_prompt.side_effect = RuntimeError("api down")
        gate = SafetyGate(armor=adapter)
        decision = gate.authorize(
            identity=AgentIdentity(
                name="outreach",
                granted_capabilities=[Capability.PATIENT_CONTACT],
            ),
            capability=Capability.PATIENT_CONTACT,
            context={"event_type": "FollowUpDue", "payload": {"note": "routine check-in"}},
        )
    assert decision.allowed is True
    assert decision.requires_human_approval is False


def test_sensitive_write_does_not_proceed_when_managed_unavailable() -> None:
    adapter = _adapter()
    with patch.object(adapter, "_client_instance") as client_factory:
        client_factory.return_value.sanitize_user_prompt.side_effect = RuntimeError("api down")
        gate = SafetyGate(armor=adapter)
        decision = gate.authorize(
            identity=AgentIdentity(
                name="records",
                granted_capabilities=[Capability.OBSERVATION_WRITE],
            ),
            capability=Capability.OBSERVATION_WRITE,
            context={"event_type": "PatientResponded", "payload": {"note": "routine observation"}},
        )
    assert decision.allowed is True
    assert decision.requires_human_approval is True
    assert "managed Model Armor unavailable" in decision.reason


def test_managed_adapter_blocks_numeric_filter_match_state() -> None:
    adapter = _adapter()
    mock_result = MagicMock()
    mock_result.filter_match_state = 2
    mock_result.filter_results = {}
    mock_response = MagicMock()
    mock_response.sanitization_result = mock_result
    with patch.object(adapter, "_client_instance") as client_factory:
        client_factory.return_value.sanitize_user_prompt.return_value = mock_response
        decision = adapter.inspect_ingress(DEMO_MALICIOUS_PROMPT)
    assert decision.allowed is False
    assert decision.adapter == "google_model_armor"
    from app.integrations.enterprise.vertex_model_armor import _match_state_is_hit
    from google.cloud.modelarmor_v1.types import FilterMatchState

    assert _match_state_is_hit(FilterMatchState.MATCH_FOUND) is True
    assert _match_state_is_hit(2) is True
    assert _match_state_is_hit(FilterMatchState.NO_MATCH_FOUND) is False
    assert _match_state_is_hit(1) is False


def test_security_demo_malicious_prompt_blocked_by_regex_fallback() -> None:
    guard = RegexContentGuardFallback()
    decision = screen_demo_prompt(guard, DEMO_MALICIOUS_PROMPT)
    assert decision.allowed is False
    assert decision.filter_category == "prompt_injection"
