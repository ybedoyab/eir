"""Central Gemini / Vertex / Enterprise configuration."""

from __future__ import annotations

import os
from typing import Any

from eir_shared.env import load_root_env

DEFAULT_GEMINI_MODEL = "gemini-3.5-flash"


def resolve_gemini_model(explicit: str | None = None) -> str:
    if explicit:
        return explicit
    load_root_env()
    return os.getenv("GEMINI_MODEL") or DEFAULT_GEMINI_MODEL


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def configure_genai_environment(
    *,
    use_vertexai: bool | None = None,
    use_enterprise: bool | None = None,
    project: str | None = None,
    location: str | None = None,
    api_key: str | None = None,
) -> None:
    """Apply official GOOGLE_GENAI_* env vars before creating genai / ADK clients."""
    load_root_env()
    vertex = use_vertexai if use_vertexai is not None else _env_bool("GOOGLE_GENAI_USE_VERTEXAI")
    enterprise = (
        use_enterprise if use_enterprise is not None else _env_bool("GOOGLE_GENAI_USE_ENTERPRISE")
    )
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "TRUE" if vertex else "FALSE"
    os.environ["GOOGLE_GENAI_USE_ENTERPRISE"] = "TRUE" if enterprise else "FALSE"
    if project:
        os.environ["GOOGLE_CLOUD_PROJECT"] = project
    if location:
        os.environ["GOOGLE_CLOUD_LOCATION"] = location
    if api_key:
        os.environ["GOOGLE_API_KEY"] = api_key


def genai_client_kwargs(
    *,
    api_key: str | None = None,
    project: str | None = None,
    location: str | None = None,
) -> dict[str, Any]:
    """Keyword args for ``google.genai.Client`` based on current env."""
    load_root_env()
    configure_genai_environment(project=project, location=location, api_key=api_key)
    if _env_bool("GOOGLE_GENAI_USE_VERTEXAI"):
        return {
            "vertexai": True,
            "project": project or os.getenv("GOOGLE_CLOUD_PROJECT") or "",
            "location": location or os.getenv("GOOGLE_CLOUD_LOCATION") or "us-central1",
        }
    key = api_key or os.getenv("GOOGLE_API_KEY") or ""
    return {"api_key": key}
