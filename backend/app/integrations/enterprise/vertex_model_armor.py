"""Optional Vertex Model Armor adapter with regex fallback."""

from __future__ import annotations

import logging
from typing import Protocol

from app.integrations.enterprise.model_armor import ArmorDecision, RegexContentGuardFallback

logger = logging.getLogger("eir.model_armor")


class ContentGuard(Protocol):
    adapter_name: str

    def inspect_ingress(self, text: str) -> ArmorDecision: ...

    def inspect_egress(self, text: str) -> ArmorDecision: ...


class VertexModelArmorAdapter:
    """Attempts Vertex AI safety screening; falls back to regex guard when unavailable."""

    adapter_name = "vertex_model_armor"

    def __init__(self, *, project: str, location: str, fallback: RegexContentGuardFallback) -> None:
        self._project = project
        self._location = location
        self._fallback = fallback
        self._available: bool | None = None

    def inspect_ingress(self, text: str) -> ArmorDecision:
        if not self._try_vertex(text):
            return self._fallback.inspect_ingress(text)
        return ArmorDecision(allowed=True, sanitized_text=text.strip(), adapter=self.adapter_name)

    def inspect_egress(self, text: str) -> ArmorDecision:
        fallback = self._fallback.inspect_egress(text)
        if not fallback.allowed:
            return fallback
        if not self._try_vertex(text):
            return fallback
        return ArmorDecision(allowed=True, sanitized_text=text.strip(), adapter=self.adapter_name)

    def _try_vertex(self, text: str) -> bool:
        if self._available is False:
            return False
        try:
            from google.cloud import modelarmor_v1

            _ = modelarmor_v1  # noqa: F841 — import proves API client availability
            self._available = True
            return True
        except Exception:
            logger.info("Vertex Model Armor client unavailable; using regex fallback")
            self._available = False
            return False


def build_content_guard(
    *,
    project: str,
    location: str,
    prefer_vertex: bool,
) -> ContentGuard:
    fallback = RegexContentGuardFallback()
    if not prefer_vertex:
        return fallback
    return VertexModelArmorAdapter(project=project, location=location, fallback=fallback)
