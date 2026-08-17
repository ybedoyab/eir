"""Google Cloud Healthcare FHIR R4 adapter.

Falls back to LocalFhirClient when the store is unreachable.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from eir_agents.records.fhir_client import LocalFhirClient

logger = logging.getLogger("eir.fhir")


class GoogleHealthcareFhirClient:
    def __init__(
        self,
        *,
        project: str,
        location: str,
        dataset: str,
        store: str,
        fallback: LocalFhirClient | None = None,
    ) -> None:
        self._base = (
            f"https://healthcare.googleapis.com/v1/projects/{project}/locations/{location}"
            f"/datasets/{dataset}/fhirStores/{store}/fhir"
        )
        self._fallback = fallback or LocalFhirClient()

    def _headers(self) -> dict[str, str]:
        import google.auth
        import google.auth.transport.requests

        credentials, _project = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-healthcare"]
        )
        credentials.refresh(google.auth.transport.requests.Request())
        return {
            "Authorization": f"Bearer {credentials.token}",
            "Content-Type": "application/fhir+json",
        }

    def _get(self, path: str) -> dict[str, Any] | None:
        try:
            response = httpx.get(f"{self._base}/{path}", headers=self._headers(), timeout=10)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()
        except Exception:
            logger.warning("Healthcare API read failed for %s; using local fixtures", path)
            return None

    def _search(self, resource_type: str, patient_id: str) -> list[dict[str, Any]]:
        try:
            response = httpx.get(
                f"{self._base}/{resource_type}",
                params={"patient": f"Patient/{patient_id}"},
                headers=self._headers(),
                timeout=10,
            )
            response.raise_for_status()
            entries = response.json().get("entry") or []
            return [item.get("resource") for item in entries if item.get("resource")]
        except Exception:
            logger.warning(
                "Healthcare API search failed for %s; using local fixtures", resource_type
            )
            return []

    def get_patient(self, patient_id: str) -> dict[str, Any] | None:
        return self._get(f"Patient/{patient_id}") or self._fallback.get_patient(patient_id)

    def get_encounters(self, patient_id: str) -> list[dict[str, Any]]:
        return self._search("Encounter", patient_id) or self._fallback.get_encounters(patient_id)

    def get_medications(self, patient_id: str) -> list[dict[str, Any]]:
        return self._search("MedicationRequest", patient_id) or self._fallback.get_medications(
            patient_id
        )

    def get_care_plan(self, patient_id: str) -> dict[str, Any] | None:
        found = self._search("CarePlan", patient_id)
        if found:
            return found[0]
        return self._fallback.get_care_plan(patient_id)

    def get_observations(self, patient_id: str) -> list[dict[str, Any]]:
        found = self._search("Observation", patient_id)
        return found or self._fallback.get_observations(patient_id)

    def append_follow_up_observation(self, observation: dict[str, Any]) -> dict[str, Any]:
        try:
            response = httpx.post(
                f"{self._base}/Observation",
                headers=self._headers(),
                json=observation,
                timeout=10,
            )
            response.raise_for_status()
            return response.json()
        except Exception:
            logger.warning("Healthcare API write failed; storing observation locally")
            return self._fallback.append_follow_up_observation(observation)
