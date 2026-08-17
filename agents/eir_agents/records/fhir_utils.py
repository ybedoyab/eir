"""Small helpers for synthetic FHIR fixtures."""

from __future__ import annotations

from typing import Any

REPORTED_ISSUE_URL = "https://eir.local/extensions/reported-issue"


def reported_issue_from_observation(observation: dict[str, Any]) -> bool:
    for extension in observation.get("extension") or []:
        url = str(extension.get("url") or "")
        if url.endswith("reported-issue") or url == REPORTED_ISSUE_URL:
            return bool(extension.get("valueBoolean"))
    return False


def pain_score_from_observation(observation: dict[str, Any], *, default: int = 2) -> int:
    value = observation.get("valueInteger")
    if value is None:
        return default
    return int(value)
