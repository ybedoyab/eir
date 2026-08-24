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


def expand_fhir_resources(payload: Any) -> list[dict[str, Any]]:
    """Unwrap a Bundle, a JSON list, or a single resource into resources."""
    if payload is None:
        return []
    if isinstance(payload, list):
        resources: list[dict[str, Any]] = []
        for item in payload:
            resources.extend(expand_fhir_resources(item))
        return resources
    if not isinstance(payload, dict):
        return []
    resource_type = str(payload.get("resourceType") or "")
    if resource_type == "Bundle":
        resources = []
        for entry in payload.get("entry") or []:
            if isinstance(entry, dict):
                resources.extend(expand_fhir_resources(entry.get("resource")))
        return resources
    if resource_type:
        return [payload]
    return []
