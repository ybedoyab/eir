"""Configure Google ADK OpenTelemetry export for Cloud Trace/Logging."""

from __future__ import annotations

import logging
import os

logger = logging.getLogger("eir.adk_otel")

_configured = False


def setup_adk_otel(*, service_name: str, project_id: str, enabled: bool = True) -> bool:
    global _configured
    if _configured or not enabled:
        return _configured

    os.environ.setdefault("OTEL_SERVICE_NAME", service_name)
    os.environ.setdefault("ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS", "false")
    os.environ.setdefault("OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT", "NO_CONTENT")

    try:
        import google.auth
        from google.adk.telemetry.google_cloud import get_gcp_exporters, get_gcp_resource
        from google.adk.telemetry.setup import maybe_set_otel_providers
    except ImportError:
        logger.warning("ADK GCP telemetry extras unavailable; skipping OpenTelemetry setup")
        return False

    try:
        credentials, resolved_project = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        project = project_id or resolved_project
        hooks = get_gcp_exporters(
            enable_cloud_tracing=True,
            enable_cloud_metrics=True,
            enable_cloud_logging=True,
            google_auth=(credentials, project),
        )
        maybe_set_otel_providers(
            otel_hooks_to_setup=[hooks],
            otel_resource=get_gcp_resource(project),
        )
        try:
            from opentelemetry.instrumentation.google_genai import GoogleGenAiSdkInstrumentor

            GoogleGenAiSdkInstrumentor().instrument()
        except ImportError:
            logger.info("GenAI OTel instrumentor not installed")
        _configured = True
        logger.info("ADK OpenTelemetry configured for %s", service_name)
        return True
    except Exception:
        logger.exception("Failed to configure ADK OpenTelemetry")
        return False


def otel_configured() -> bool:
    return _configured
