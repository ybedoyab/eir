"""FHIR access protocol.

Local implementation reads synthetic fixtures under mocks/fhir/{patient_id}/.
Google Cloud Healthcare API lives in backend.integrations.fhir and falls back
to this client.
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

    def create_appointment(
        self,
        *,
        patient_id: str,
        episode_id: str,
        reason: str,
    ) -> dict[str, Any]: ...


def _default_mocks_dir() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "mocks" / "fhir"
        if candidate.is_dir():
            return candidate
    return Path("mocks/fhir")


class LocalFhirClient:
    _FILES = {
        "patient": "patient.json",
        "encounter": "encounter.json",
        "medication": "medication-request.json",
        "observation": "observation.json",
        "care_plan": "care-plan.json",
    }

    def __init__(self, mocks_dir: Path | None = None) -> None:
        self.mocks_dir = mocks_dir or _default_mocks_dir()
        self._appended: list[dict[str, Any]] = []
        self._appointments: list[dict[str, Any]] = []

    def _patient_dir(self, patient_id: str) -> Path | None:
        candidate = self.mocks_dir / patient_id
        if candidate.is_dir():
            return candidate
        return None

    def _load(self, patient_id: str, filename: str) -> dict[str, Any] | None:
        patient_dir = self._patient_dir(patient_id)
        if patient_dir is None:
            return None
        path = patient_dir / filename
        if not path.is_file():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def _matches_patient(self, resource: dict[str, Any], patient_id: str) -> bool:
        if resource.get("id") == patient_id:
            return True
        subject = (resource.get("subject") or {}).get("reference", "")
        return patient_id in subject

    def get_patient(self, patient_id: str) -> dict[str, Any] | None:
        resource = self._load(patient_id, self._FILES["patient"])
        if resource is None:
            return None
        return resource if self._matches_patient(resource, patient_id) else None

    def get_encounters(self, patient_id: str) -> list[dict[str, Any]]:
        resource = self._load(patient_id, self._FILES["encounter"])
        if resource is None:
            return []
        if self._matches_patient(resource, patient_id):
            return [resource]
        return []

    def get_medications(self, patient_id: str) -> list[dict[str, Any]]:
        resource = self._load(patient_id, self._FILES["medication"])
        if resource is None:
            return []
        if self._matches_patient(resource, patient_id):
            return [resource]
        return []

    def get_care_plan(self, patient_id: str) -> dict[str, Any] | None:
        resource = self._load(patient_id, self._FILES["care_plan"])
        if resource is None:
            return None
        return resource if self._matches_patient(resource, patient_id) else None

    def get_observations(self, patient_id: str) -> list[dict[str, Any]]:
        resource = self._load(patient_id, self._FILES["observation"])
        if resource is None:
            return []
        if self._matches_patient(resource, patient_id):
            return [resource]
        return []

    def append_follow_up_observation(self, observation: dict[str, Any]) -> dict[str, Any]:
        stored = dict(observation)
        stored.setdefault("id", f"synthetic-obs-{len(self._appended) + 1}")
        self._appended.append(stored)
        return stored

    def create_appointment(
        self,
        *,
        patient_id: str,
        episode_id: str,
        reason: str,
    ) -> dict[str, Any]:
        from uuid import uuid4

        appointment_id = f"synthetic-appt-{uuid4().hex[:8]}"
        resource = {
            "resourceType": "Appointment",
            "id": appointment_id,
            "status": "proposed",
            "description": reason,
            "participant": [
                {
                    "actor": {"reference": f"Patient/{patient_id}"},
                    "status": "needs-action",
                }
            ],
            "extension": [
                {
                    "url": "https://eir.local/recovery-episode",
                    "valueString": episode_id,
                }
            ],
        }
        self._appointments.append(resource)
        return resource
