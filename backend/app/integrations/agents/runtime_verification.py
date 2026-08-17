"""Runtime verification for ADK / Vertex enterprise configuration."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from eir_shared.gemini_config import (
    DEFAULT_GEMINI_MODEL,
    configure_genai_environment,
    genai_client_kwargs,
    resolve_gemini_model,
)

logger = logging.getLogger("eir.runtime_verification")


@dataclass(frozen=True)
class RuntimeVerification:
    model: str
    adk_invocation_succeeded: bool
    enterprise_endpoint_active: bool
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
    location: str,
    api_key: str,
    skip_probe: bool = False,
) -> RuntimeVerification:
    model = resolve_gemini_model()
    if skip_probe or adk_runner_mode == "direct":
        return RuntimeVerification(
            model=model,
            adk_invocation_succeeded=adk_runner_mode == "direct",
            enterprise_endpoint_active=False,
            adk_runner_mode=adk_runner_mode,
            adk_allow_direct_fallback=adk_allow_direct_fallback,
        )

    configure_genai_environment(
        use_vertexai=use_vertexai,
        use_enterprise=use_enterprise,
        project=project,
        location=location,
        api_key=api_key or None,
    )
    try:
        from google import genai

        client = genai.Client(**genai_client_kwargs(api_key=api_key or None))
        response = client.models.generate_content(
            model=model,
            contents="Reply with exactly: ok",
        )
        text = (response.text or "").strip().lower()
        if "ok" not in text and text != "ok":
            logger.warning("Gemini probe unexpected response: %s", response.text)
        return RuntimeVerification(
            model=model,
            adk_invocation_succeeded=True,
            enterprise_endpoint_active=use_vertexai,
            adk_runner_mode=adk_runner_mode,
            adk_allow_direct_fallback=adk_allow_direct_fallback,
        )
    except Exception as exc:
        logger.exception("Runtime verification probe failed")
        return RuntimeVerification(
            model=model or DEFAULT_GEMINI_MODEL,
            adk_invocation_succeeded=False,
            enterprise_endpoint_active=False,
            adk_runner_mode=adk_runner_mode,
            adk_allow_direct_fallback=adk_allow_direct_fallback,
            probe_error=str(exc),
        )
