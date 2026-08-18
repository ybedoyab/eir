"""AdkApp entrypoint for Gemini Enterprise Agent Runtime."""

from __future__ import annotations

from vertexai.agent_engines import AdkApp

from eir_agents.access.agent import build_patient_access_agent
from eir_agents.access.constants import GEMINI_MODEL, RUNTIME_DISPLAY_NAME

IDENTITY_TYPE = "AGENT_IDENTITY"
ENTRYPOINT_MODULE = "eir_agents.access.runtime_app"
ENTRYPOINT_OBJECT = "app"


def build_adk_app() -> AdkApp:
    return AdkApp(agent=build_patient_access_agent(), enable_tracing=True)


app = build_adk_app()


def runtime_config() -> dict[str, str]:
    return {
        "model": GEMINI_MODEL,
        "identity_type": IDENTITY_TYPE,
        "framework": "google-adk",
        "display_name": RUNTIME_DISPLAY_NAME,
        "entrypoint_module": ENTRYPOINT_MODULE,
        "entrypoint_object": ENTRYPOINT_OBJECT,
    }
