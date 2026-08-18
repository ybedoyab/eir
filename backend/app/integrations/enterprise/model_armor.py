"""Fallback regex content guard — NOT Google Cloud Model Armor."""

from __future__ import annotations

import re
from dataclasses import dataclass

_INJECTION_PATTERNS = (
    re.compile(r"ignore (all )?previous (instructions|policy)", re.I),
    re.compile(r"retrieve all patient records", re.I),
    re.compile(r"system prompt", re.I),
    re.compile(r"<\s*script", re.I),
)


@dataclass(frozen=True)
class ArmorDecision:
    allowed: bool
    reason: str = ""
    sanitized_text: str = ""
    adapter: str = "regex_fallback"
    filter_category: str = ""
    degraded: bool = False


class RegexContentGuardFallback:
    """Local deterministic guard. Use VertexModelArmorAdapter in production when available."""

    adapter_name = "regex_fallback"

    def inspect_ingress(self, text: str) -> ArmorDecision:
        for pattern in _INJECTION_PATTERNS:
            if pattern.search(text):
                return ArmorDecision(
                    allowed=False,
                    reason=f"content guard blocked ingress pattern: {pattern.pattern}",
                    adapter=self.adapter_name,
                    filter_category="prompt_injection",
                )
        return ArmorDecision(
            allowed=True,
            sanitized_text=text.strip(),
            adapter=self.adapter_name,
        )

    def inspect_egress(self, text: str) -> ArmorDecision:
        lowered = text.lower()
        if "diagnosis:" in lowered or ("you have " in lowered and "cancer" in lowered):
            return ArmorDecision(
                allowed=False,
                reason="content guard blocked clinical diagnosis phrasing in egress",
                adapter=self.adapter_name,
            )
        return ArmorDecision(
            allowed=True,
            sanitized_text=text.strip(),
            adapter=self.adapter_name,
        )
