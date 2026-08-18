"""Tests for ADK OpenTelemetry bootstrap."""

from app.integrations.enterprise import adk_otel
from app.integrations.enterprise.adk_otel import otel_configured, setup_adk_otel


def setup_function() -> None:
    adk_otel._configured = False


def test_setup_adk_otel_disabled() -> None:
    assert setup_adk_otel(service_name="eir-test", project_id="eir-ata", enabled=False) is False
    assert otel_configured() is False
