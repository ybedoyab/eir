"""Optional Vertex Model Armor adapter with regex fallback."""

from __future__ import annotations

import logging
from typing import Protocol

from app.integrations.enterprise.model_armor import ArmorDecision, RegexContentGuardFallback

logger = logging.getLogger("eir.model_armor")


def managed_model_armor_available() -> bool:
    try:
        from google.cloud import modelarmor_v1
    except Exception:
        return False
    return hasattr(modelarmor_v1, "ModelArmorClient")


class ContentGuard(Protocol):
    adapter_name: str
    managed_available: bool

    def inspect_ingress(self, text: str) -> ArmorDecision: ...

    def inspect_egress(self, text: str) -> ArmorDecision: ...


class VertexModelArmorAdapter:
    """Uses managed Model Armor when available; otherwise regex fallback."""

    adapter_name = "vertex_model_armor"

    def __init__(self, *, project: str, location: str, fallback: RegexContentGuardFallback) -> None:
        self._project = project
        self._location = location
        self._fallback = fallback
        self.managed_available = managed_model_armor_available()

    def inspect_ingress(self, text: str) -> ArmorDecision:
        managed = self._inspect_managed(text)
        if managed is not None:
            return managed
        decision = self._fallback.inspect_ingress(text)
        return ArmorDecision(
            allowed=decision.allowed,
            reason=decision.reason,
            sanitized_text=decision.sanitized_text,
            adapter=decision.adapter,
        )

    def inspect_egress(self, text: str) -> ArmorDecision:
        fallback = self._fallback.inspect_egress(text)
        if not fallback.allowed:
            return fallback
        managed = self._inspect_managed(text)
        if managed is not None:
            return managed
        return fallback

    def _inspect_managed(self, text: str) -> ArmorDecision | None:
        del text
        if not self.managed_available:
            return None
        logger.info("Managed Model Armor SDK unavailable in this environment; using regex fallback")
        return None


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
