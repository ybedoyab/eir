"""Parse structured signals from synthetic patient conversations."""

from __future__ import annotations

import re
from typing import Any


def _adherence_from_text(patient_text: str) -> str | None:
    if not any(
        token in patient_text
        for token in ("medication", "medications", "tablet", "tablets", "dose", "pills")
    ):
        return None
    negative = (
        "not been taking",
        "haven't been taking",
        "have not been taking",
        "not taking",
        "stopped taking",
        "haven't taken",
        "have not taken",
        "missed",
    )
    if any(token in patient_text for token in negative):
        return "no"
    if any(token in patient_text for token in ("taking", "taken", "yes")):
        return "yes"
    return "unknown"


def signals_from_conversation(
    conversation: list[dict[str, Any]],
) -> tuple[bool, int | None, str | None]:
    patient_text = " ".join(
        str(item.get("text", ""))
        for item in conversation
        if str(item.get("role", "")).lower() == "patient"
    ).lower()
    if not patient_text:
        return False, None, None

    reported_issue = any(
        token in patient_text
        for token in ("swelling", "fever", "bleeding", "worse", "concern", "issue")
    )
    pain_score = None
    match = re.search(r"\b([0-9]|10)\b", patient_text)
    if match:
        pain_score = int(match.group(1))
    return reported_issue, pain_score, _adherence_from_text(patient_text)
