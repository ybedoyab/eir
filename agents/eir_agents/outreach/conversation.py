"""Parse structured signals from synthetic patient conversations."""

from __future__ import annotations

import re
from typing import Any


def signals_from_conversation(
    conversation: list[dict[str, Any]],
) -> tuple[bool, int | None]:
    patient_text = " ".join(
        str(item.get("text", ""))
        for item in conversation
        if str(item.get("role", "")).lower() == "patient"
    ).lower()
    if not patient_text:
        return False, None

    reported_issue = any(
        token in patient_text
        for token in ("swelling", "fever", "bleeding", "worse", "concern", "issue")
    )
    pain_score = None
    match = re.search(r"\b([0-9]|10)\b", patient_text)
    if match:
        pain_score = int(match.group(1))
    return reported_issue, pain_score
