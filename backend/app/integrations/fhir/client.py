"""Google Cloud Healthcare FHIR R4 adapter.

Falls back to LocalFhirClient only when the store is unreachable, or when
`fallback_on_miss` is true (empty store during local demo). A successful
empty search does not impersonate synthetic fixtures unless that flag is on.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from eir_agents.records.fhir_client import LocalFhirClient

logger = logging.getLogger("eir.fhir")
_SYNTHETIC_ID_SYSTEM = "https://eir.local/synthetic-patients"


class GoogleHealthcareFhirClient:
    def __init__(
        self,
        *,
        project: str,
        location: str,
        dataset: str,
        store: str,
        fallback: LocalFhirClient | None = None,
        fallback_on_miss: bool = True,
    ) -> None:
        self._base = (
            f"https://healthcare.googleapis.com/v1/projects/{project}/locations/{location}"
            f"/datasets/{dataset}/fhirStores/{store}/fhir"
        )
        self._fallback = fallback or LocalFhirClient()
        self._fallback_on_miss = fallback_on_miss
        self.reachable: bool | None = None

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

    def _use_fallback(self) -> bool:
        if self.reachable is False:
            return True
        return self._fallback_on_miss

    def _get(self, path: str) -> dict[str, Any] | None:
        try:
            response = httpx.get(f"{self._base}/{path}", headers=self._headers(), timeout=10)
            if response.status_code == 404:
                self.reachable = True
                return None
            response.raise_for_status()
            self.reachable = True
            return response.json()
        except Exception:
            self.reachable = False
            logger.warning("Healthcare API read failed for %s; using local fixtures", path)
            return None

    def _resolve_patient(self, patient_id: str) -> dict[str, Any] | None:
        found = self._get(f"Patient/{patient_id}")
        if found is not None:
            return found
        try:
            response = httpx.get(
                f"{self._base}/Patient",
                params={"identifier": f"{_SYNTHETIC_ID_SYSTEM}|{patient_id}"},
                headers=self._headers(),
                timeout=10,
            )
            response.raise_for_status()
            self.reachable = True
            entries = response.json().get("entry") or []
            if entries:
                resource = entries[0].get("resource")
                if isinstance(resource, dict):
                    return resource
        except Exception:
            self.reachable = False
            logger.warning("Healthcare API patient search failed for %s", patient_id)
        return None

    def _patient_ref(self, patient_id: str) -> str | None:
        patient = self._resolve_patient(patient_id)
        if patient is None:
            return None
        server_id = patient.get("id")
        if not server_id:
            return None
        return f"Patient/{server_id}"

    def _search(self, resource_type: str, patient_id: str) -> list[dict[str, Any]] | None:
        patient_ref = self._patient_ref(patient_id)
        if patient_ref is None:
            return None
        try:
            response = httpx.get(
                f"{self._base}/{resource_type}",
                params={"patient": patient_ref},
                headers=self._headers(),
                timeout=10,
            )
            response.raise_for_status()
            self.reachable = True
            entries = response.json().get("entry") or []
            return [item.get("resource") for item in entries if item.get("resource")]
        except Exception:
            self.reachable = False
            logger.warning(
                "Healthcare API search failed for %s; using local fixtures", resource_type
            )
            return None

    def upsert_resource(self, resource: dict[str, Any]) -> dict[str, Any]:
        resource_type = resource.get("resourceType")
        resource_id = resource.get("id")
        if not resource_type or not resource_id:
            raise ValueError("FHIR resource needs resourceType and id")
        headers = self._headers()
        target = f"{self._base}/{resource_type}/{resource_id}"
        existing = httpx.get(target, headers=headers, timeout=20)
        if existing.status_code == 404:
            response = httpx.post(
                f"{self._base}/{resource_type}",
                headers=headers,
                json=resource,
                timeout=20,
            )
        else:
            existing.raise_for_status()
            response = httpx.put(target, headers=headers, json=resource, timeout=20)
        if response.status_code >= 400:
            detail = response.text[:500]
            raise RuntimeError(f"FHIR upsert failed ({response.status_code}): {detail}")
        self.reachable = True
        return response.json() if response.content else resource

    def get_patient(self, patient_id: str) -> dict[str, Any] | None:
        found = self._resolve_patient(patient_id)
        if found is not None:
            return found
        if self._use_fallback():
            return self._fallback.get_patient(patient_id)
        return None

    def get_encounters(self, patient_id: str) -> list[dict[str, Any]]:
        found = self._search("Encounter", patient_id)
        if found:
            return found
        if found == [] and not self._use_fallback():
            return []
        if self._use_fallback():
            return self._fallback.get_encounters(patient_id)
        return []

    def get_medications(self, patient_id: str) -> list[dict[str, Any]]:
        found = self._search("MedicationRequest", patient_id)
        if found:
            return found
        if found == [] and not self._use_fallback():
            return []
        if self._use_fallback():
            return self._fallback.get_medications(patient_id)
        return []

    def get_care_plan(self, patient_id: str) -> dict[str, Any] | None:
        found = self._search("CarePlan", patient_id)
        if found:
            return found[0]
        if found == [] and not self._use_fallback():
            return None
        if self._use_fallback():
            return self._fallback.get_care_plan(patient_id)
        return None

    def get_observations(self, patient_id: str) -> list[dict[str, Any]]:
        found = self._search("Observation", patient_id)
        if found:
            return found
        if found == [] and not self._use_fallback():
            return []
        if self._use_fallback():
            return self._fallback.get_observations(patient_id)
        return []

    def append_follow_up_observation(self, observation: dict[str, Any]) -> dict[str, Any]:
        try:
            response = httpx.post(
                f"{self._base}/Observation",
                headers=self._headers(),
                json=observation,
                timeout=10,
            )
            response.raise_for_status()
            self.reachable = True
            return response.json()
        except Exception:
            self.reachable = False
            logger.warning("Healthcare API write failed; storing observation locally")
            return self._fallback.append_follow_up_observation(observation)
