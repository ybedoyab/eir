"""AdkApp entrypoint for Gemini Enterprise Agent Runtime."""

from __future__ import annotations

from typing import Any

from eir_agents.access.agent import build_patient_access_agent
from eir_agents.access.constants import GEMINI_MODEL, RUNTIME_DISPLAY_NAME

IDENTITY_TYPE = "AGENT_IDENTITY"
ENTRYPOINT_MODULE = "eir_agents.access.runtime_app"
ENTRYPOINT_OBJECT = "app"


def build_adk_app():
    from vertexai.agent_engines import AdkApp

    return AdkApp(agent=build_patient_access_agent(), enable_tracing=True)


def runtime_config() -> dict[str, str]:
    return {
        "model": GEMINI_MODEL,
        "identity_type": IDENTITY_TYPE,
        "framework": "google-adk",
        "display_name": RUNTIME_DISPLAY_NAME,
        "entrypoint_module": ENTRYPOINT_MODULE,
        "entrypoint_object": ENTRYPOINT_OBJECT,
    }


def __getattr__(name: str) -> Any:
    if name == ENTRYPOINT_OBJECT:
        return build_adk_app()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
