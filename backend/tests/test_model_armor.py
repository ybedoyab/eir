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


def test_managed_adapter_blocks_prompt_injection_match() -> None:
    adapter = VertexModelArmorAdapter(
        project="test-project",
        location="us-central1",
        template="eir-agent-guard",
        fallback=RegexContentGuardFallback(),
        fail_closed=True,
    )
    mock_result = MagicMock()
    mock_result.filter_match_state = "NO_MATCH_FOUND"
    pi = MagicMock()
    pi.match_state = "MATCH_FOUND"
    mock_result.filter_results = {"pi_and_jailbreak": pi}

    mock_response = MagicMock()
    mock_response.sanitization_result = mock_result

    with patch.object(adapter, "_client_instance") as client_factory:
        client_factory.return_value.sanitize_user_prompt.return_value = mock_response
        decision = adapter.inspect_ingress(DEMO_MALICIOUS_PROMPT)

    assert decision.allowed is False
    assert decision.adapter == "google_model_armor"
    assert decision.filter_category
    assert adapter.status()["last_screening_success"] is True
    assert adapter.status()["last_blocked"] is True


def test_managed_adapter_allows_clean_prompt() -> None:
    adapter = VertexModelArmorAdapter(
        project="test-project",
        location="us-central1",
        template="eir-agent-guard",
        fallback=RegexContentGuardFallback(),
        fail_closed=True,
    )
    mock_result = MagicMock()
    mock_result.filter_match_state = "NO_MATCH_FOUND"
    mock_result.filter_results = {}
    mock_result.sanitization_metadata = MagicMock(sanitized_text=DEMO_SAFE_PROMPT)

    mock_response = MagicMock()
    mock_response.sanitization_result = mock_result

    with patch.object(adapter, "_client_instance") as client_factory:
        client_factory.return_value.sanitize_user_prompt.return_value = mock_response
        decision = adapter.inspect_ingress(DEMO_SAFE_PROMPT)

    assert decision.allowed is True
    assert decision.adapter == "google_model_armor"
    assert adapter.status()["last_blocked"] is False


def test_managed_adapter_falls_back_on_api_error() -> None:
    adapter = VertexModelArmorAdapter(
        project="test-project",
        location="us-central1",
        template="eir-agent-guard",
        fallback=RegexContentGuardFallback(),
        fail_closed=True,
    )
    with patch.object(adapter, "_client_instance") as client_factory:
        client_factory.return_value.sanitize_user_prompt.side_effect = RuntimeError("api down")
        decision = adapter.inspect_ingress(DEMO_SAFE_PROMPT)

    assert decision.allowed is True
    assert decision.adapter == "regex_fallback"
    assert adapter.status()["last_screening_success"] is False


def test_security_demo_malicious_prompt_blocked_by_regex_fallback() -> None:
    guard = RegexContentGuardFallback()
    decision = screen_demo_prompt(guard, DEMO_MALICIOUS_PROMPT)
    assert decision.allowed is False
    assert decision.filter_category == "prompt_injection"
