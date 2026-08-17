"""Model Armor ingress/egress checks (deterministic stand-in)."""

from __future__ import annotations

import re
from dataclasses import dataclass

_INJECTION_PATTERNS = (
    re.compile(r"ignore (all )?previous instructions", re.I),
    re.compile(r"system prompt", re.I),
    re.compile(r"<\s*script", re.I),
)


@dataclass(frozen=True)
class ArmorDecision:
    allowed: bool
    reason: str = ""
    sanitized_text: str = ""


class ModelArmor:
    """Blocks obvious prompt-injection patterns on workflow ingress/egress."""

    def inspect_ingress(self, text: str) -> ArmorDecision:
        for pattern in _INJECTION_PATTERNS:
            if pattern.search(text):
                return ArmorDecision(
                    allowed=False,
                    reason=f"model armor blocked ingress pattern: {pattern.pattern}",
                )
        return ArmorDecision(allowed=True, sanitized_text=text.strip())

    def inspect_egress(self, text: str) -> ArmorDecision:
        if "diagnosis:" in text.lower() or "you have " in text.lower() and "cancer" in text.lower():
            return ArmorDecision(
                allowed=False,
                reason="model armor blocked clinical diagnosis phrasing in egress",
            )
        return ArmorDecision(allowed=True, sanitized_text=text.strip())
