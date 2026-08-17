"""FHIR access protocol.

Local implementation reads synthetic fixtures. Google Cloud Healthcare API
lives in backend.integrations.fhir and falls back to this client.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol


class FhirClient(Protocol):
    def get_patient(self, patient_id: str) -> dict[str, Any] | None: ...

    def get_encounters(self, patient_id: str) -> list[dict[str, Any]]: ...

    def get_medications(self, patient_id: str) -> list[dict[str, Any]]: ...

    def get_care_plan(self, patient_id: str) -> dict[str, Any] | None: ...

    def get_observations(self, patient_id: str) -> list[dict[str, Any]]: ...

    def append_follow_up_observation(self, observation: dict[str, Any]) -> dict[str, Any]: ...


def _default_mocks_dir() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "mocks" / "fhir"
        if candidate.is_dir():
            return candidate
    return Path("mocks/fhir")


class LocalFhirClient:
    def __init__(self, mocks_dir: Path | None = None) -> None:
        self.mocks_dir = mocks_dir or _default_mocks_dir()
        self._appended: list[dict[str, Any]] = []

    def _load(self, filename: str) -> dict[str, Any]:
        path = self.mocks_dir / filename
        return json.loads(path.read_text(encoding="utf-8"))

    def _matches_patient(self, resource: dict[str, Any], patient_id: str) -> bool:
        if resource.get("id") == patient_id:
            return True
        subject = (resource.get("subject") or {}).get("reference", "")
        return patient_id in subject

    def get_patient(self, patient_id: str) -> dict[str, Any] | None:
        resource = self._load("patient.json")
        if resource.get("id") == patient_id:
            return resource
        return None

    def get_encounters(self, patient_id: str) -> list[dict[str, Any]]:
        resource = self._load("encounter.json")
        subject = (resource.get("subject") or {}).get("reference", "")
        if patient_id in subject or resource.get("subject", {}).get("id") == patient_id:
            return [resource]
        return []

    def get_medications(self, patient_id: str) -> list[dict[str, Any]]:
        resource = self._load("medication-request.json")
        subject = (resource.get("subject") or {}).get("reference", "")
        if patient_id in subject:
            return [resource]
        return []

    def get_care_plan(self, patient_id: str) -> dict[str, Any] | None:
        resource = self._load("care-plan.json")
        if self._matches_patient(resource, patient_id):
            return resource
        return None

    def get_observations(self, patient_id: str) -> list[dict[str, Any]]:
        resource = self._load("observation.json")
        if self._matches_patient(resource, patient_id):
            return [resource]
        return []

    def append_follow_up_observation(self, observation: dict[str, Any]) -> dict[str, Any]:
        stored = dict(observation)
        stored.setdefault("id", f"synthetic-obs-{len(self._appended) + 1}")
        self._appended.append(stored)
        return stored
