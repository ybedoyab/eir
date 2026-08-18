"""Runtime verification for Vertex model access and ADK configuration."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from eir_shared.gemini_config import (
    DEFAULT_GEMINI_MODEL,
    configure_genai_environment,
    genai_client_kwargs,
    resolve_gemini_location,
    resolve_gemini_model,
)

logger = logging.getLogger("eir.runtime_verification")


@dataclass(frozen=True)
class RuntimeVerification:
    model: str
    gemini_location: str
    infra_location: str
    vertex_model_probe_success: bool
    vertex_configured: bool
    enterprise_configured: bool
    managed_agent_runtime_verified: bool
    adk_runner_mode: str
    adk_allow_direct_fallback: bool
    probe_error: str | None = None


def verify_runtime(
    *,
    adk_runner_mode: str,
    adk_allow_direct_fallback: bool,
    use_vertexai: bool,
    use_enterprise: bool,
    project: str,
    infra_location: str,
    gemini_location: str,
    api_key: str,
    skip_probe: bool = False,
) -> RuntimeVerification:
    model = resolve_gemini_model()
    gemini_location = gemini_location or resolve_gemini_location()
    if skip_probe or adk_runner_mode == "direct":
        return RuntimeVerification(
            model=model,
            gemini_location=gemini_location,
            infra_location=infra_location,
            vertex_model_probe_success=adk_runner_mode == "direct",
            vertex_configured=use_vertexai,
            enterprise_configured=use_enterprise,
            managed_agent_runtime_verified=False,
            adk_runner_mode=adk_runner_mode,
            adk_allow_direct_fallback=adk_allow_direct_fallback,
        )

    configure_genai_environment(
        use_vertexai=use_vertexai,
        use_enterprise=use_enterprise,
        project=project,
        infra_location=infra_location,
        api_key=api_key or None,
    )
    try:
        from google import genai

        client = genai.Client(
            **genai_client_kwargs(
                api_key=api_key or None,
                project=project,
                location=gemini_location,
            )
        )
        response = client.models.generate_content(
            model=model,
            contents="Reply with exactly: ok",
        )
        text = (response.text or "").strip().lower()
        if "ok" not in text and text != "ok":
            logger.warning("Gemini probe unexpected response: %s", response.text)
        return RuntimeVerification(
            model=model,
            gemini_location=gemini_location,
            infra_location=infra_location,
            vertex_model_probe_success=True,
            vertex_configured=use_vertexai,
            enterprise_configured=use_enterprise,
            managed_agent_runtime_verified=False,
            adk_runner_mode=adk_runner_mode,
            adk_allow_direct_fallback=adk_allow_direct_fallback,
        )
    except Exception as exc:
        logger.exception("Runtime verification probe failed")
        return RuntimeVerification(
            model=model or DEFAULT_GEMINI_MODEL,
            gemini_location=gemini_location,
            infra_location=infra_location,
            vertex_model_probe_success=False,
            vertex_configured=use_vertexai,
            enterprise_configured=use_enterprise,
            managed_agent_runtime_verified=False,
            adk_runner_mode=adk_runner_mode,
            adk_allow_direct_fallback=adk_allow_direct_fallback,
            probe_error=str(exc),
        )
