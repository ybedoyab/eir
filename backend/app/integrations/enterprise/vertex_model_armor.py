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
    """Attempts managed Model Armor when configured; otherwise uses regex fallback."""

    adapter_name = "vertex_model_armor"

    def __init__(self, *, project: str, location: str, fallback: RegexContentGuardFallback) -> None:
        self._project = project
        self._location = location
        self._fallback = fallback
        self._managed_checked = False
        self._managed_available = False

    def inspect_ingress(self, text: str) -> ArmorDecision:
        managed = self._inspect_managed(text)
        if managed is not None:
            return managed
        return self._fallback.inspect_ingress(text)

    def inspect_egress(self, text: str) -> ArmorDecision:
        fallback = self._fallback.inspect_egress(text)
        if not fallback.allowed:
            return fallback
        managed = self._inspect_managed(text)
        if managed is not None:
            return managed
        return fallback

    def _inspect_managed(self, text: str) -> ArmorDecision | None:
        if self._managed_checked and not self._managed_available:
            return None
        try:
            from google.cloud import modelarmor_v1  # noqa: F401
        except Exception:
            if not self._managed_checked:
                logger.info("Vertex Model Armor client unavailable; using regex fallback")
            self._managed_checked = True
            self._managed_available = False
            return None

        # Import success alone does not prove managed screening is configured.
        self._managed_checked = True
        self._managed_available = False
        logger.info(
            "Vertex Model Armor SDK present but managed inspection is not wired; "
            "using regex fallback"
        )
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
