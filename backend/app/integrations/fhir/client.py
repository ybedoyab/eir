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

from app.integrations.fhir.gcp_scheduling import GcpSchedulingClient
from app.repositories.operational_store import InMemoryOperationalSchedulingStore

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
        operational_store: Any | None = None,
    ) -> None:
        self._base = (
            f"https://healthcare.googleapis.com/v1/projects/{project}/locations/{location}"
            f"/datasets/{dataset}/fhirStores/{store}/fhir"
        )
        self._fallback = fallback or LocalFhirClient()
        self._fallback_on_miss = fallback_on_miss
        self._operational = operational_store or InMemoryOperationalSchedulingStore()
        self.reachable: bool | None = None
        self._scheduling: GcpSchedulingClient | None = None

    @property
    def _gcp_scheduling(self) -> GcpSchedulingClient:
        if self._scheduling is None:
            self._scheduling = GcpSchedulingClient(
                base_url=self._base,
                headers=self._headers,
                patient_ref=self._patient_ref,
            )
        return self._scheduling

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

    def create_appointment(
        self,
        *,
        patient_id: str,
        episode_id: str,
        reason: str,
    ) -> dict[str, Any]:
        patient = self._resolve_patient(patient_id)
        if patient and patient.get("id"):
            patient_ref = f"Patient/{patient['id']}"
        else:
            patient_ref = f"Patient/{patient_id}"
        resource = {
            "resourceType": "Appointment",
            "status": "proposed",
            "description": reason,
            "participant": [{"actor": {"reference": patient_ref}, "status": "needs-action"}],
            "extension": [
                {
                    "url": "https://eir.local/recovery-episode",
                    "valueString": episode_id,
                }
            ],
        }
        try:
            response = httpx.post(
                f"{self._base}/Appointment",
                headers=self._headers(),
                json=resource,
                timeout=20,
            )
            response.raise_for_status()
            self.reachable = True
            return response.json()
        except Exception:
            self.reachable = False
            logger.warning("Healthcare API appointment create failed; using local fallback")
            return self._fallback.create_appointment(
                patient_id=patient_id,
                episode_id=episode_id,
                reason=reason,
            )

    def list_appointments(self, patient_id: str):
        if self._use_fallback():
            return self._fallback.list_appointments(patient_id)
        try:
            return self._gcp_scheduling.list_appointments(patient_id)
        except Exception:
            self.reachable = False
            logger.exception("Healthcare API appointment list failed")
            if self._fallback_on_miss:
                return self._fallback.list_appointments(patient_id)
            raise

    def get_appointment(self, appointment_id: str):
        if self._use_fallback():
            return self._fallback.get_appointment(appointment_id)
        try:
            return self._gcp_scheduling.get_appointment(appointment_id)
        except Exception:
            self.reachable = False
            logger.exception("Healthcare API appointment read failed")
            if self._fallback_on_miss:
                return self._fallback.get_appointment(appointment_id)
            raise

    def search_available_slots(self, params):
        if self._use_fallback():
            return self._fallback.search_available_slots(params)
        try:
            return self._gcp_scheduling.search_available_slots(params)
        except Exception:
            self.reachable = False
            logger.exception("Healthcare API slot search failed")
            if self._fallback_on_miss:
                return self._fallback.search_available_slots(params)
            raise

    def book_appointment(self, *, patient_id: str, slot_id: str, idempotency_key: str = ""):
        if self._use_fallback():
            return self._fallback.book_appointment(
                patient_id=patient_id,
                slot_id=slot_id,
                idempotency_key=idempotency_key,
            )
        try:
            booked = self._gcp_scheduling.book_appointment(
                patient_id=patient_id,
                slot_id=slot_id,
                idempotency_key=idempotency_key,
            )
            self._operational.schedule_reminder(booked)
            return booked
        except ValueError:
            raise
        except Exception:
            self.reachable = False
            logger.exception("Healthcare API booking failed")
            if self._fallback_on_miss:
                return self._fallback.book_appointment(
                    patient_id=patient_id,
                    slot_id=slot_id,
                    idempotency_key=idempotency_key,
                )
            raise

    def reschedule_appointment(
        self,
        *,
        appointment_id: str,
        patient_id: str,
        new_slot_id: str,
        idempotency_key: str = "",
    ):
        if self._use_fallback():
            return self._fallback.reschedule_appointment(
                appointment_id=appointment_id,
                patient_id=patient_id,
                new_slot_id=new_slot_id,
                idempotency_key=idempotency_key,
            )
        try:
            updated = self._gcp_scheduling.reschedule_appointment(
                appointment_id=appointment_id,
                patient_id=patient_id,
                new_slot_id=new_slot_id,
                idempotency_key=idempotency_key,
            )
            self._operational.schedule_reminder(updated)
            return updated
        except (ValueError, PermissionError):
            raise
        except Exception:
            self.reachable = False
            logger.exception("Healthcare API reschedule failed")
            if self._fallback_on_miss:
                return self._fallback.reschedule_appointment(
                    appointment_id=appointment_id,
                    patient_id=patient_id,
                    new_slot_id=new_slot_id,
                    idempotency_key=idempotency_key,
                )
            raise

    def cancel_appointment(
        self,
        *,
        appointment_id: str,
        patient_id: str,
        reason: str = "",
        confirmed: bool = False,
    ):
        if self._use_fallback():
            return self._fallback.cancel_appointment(
                appointment_id=appointment_id,
                patient_id=patient_id,
                reason=reason,
                confirmed=confirmed,
            )
        try:
            return self._gcp_scheduling.cancel_appointment(
                appointment_id=appointment_id,
                patient_id=patient_id,
                reason=reason,
                confirmed=confirmed,
            )
        except (ValueError, PermissionError):
            raise
        except Exception:
            self.reachable = False
            logger.exception("Healthcare API cancel failed")
            if self._fallback_on_miss:
                return self._fallback.cancel_appointment(
                    appointment_id=appointment_id,
                    patient_id=patient_id,
                    reason=reason,
                    confirmed=confirmed,
                )
            raise

    def join_waitlist(self, *, patient_id: str, appointment_id: str):
        if self._use_fallback():
            return self._fallback.join_waitlist(
                patient_id=patient_id,
                appointment_id=appointment_id,
            )
        appointment = self.get_appointment(appointment_id)
        if appointment is None:
            raise ValueError("appointment not found")
        if appointment.patient_id != patient_id:
            raise PermissionError("appointment ownership mismatch")
        return self._operational.join_waitlist(patient_id=patient_id, appointment=appointment)

    def list_waitlist(self, patient_id: str | None = None):
        if self._use_fallback():
            return self._fallback.list_waitlist(patient_id)
        return self._operational.list_waitlist(patient_id)

    def list_reminders(self, patient_id: str | None = None):
        if self._use_fallback():
            return self._fallback.list_reminders(patient_id)
        return self._operational.list_reminders(patient_id)

    def list_all_appointments(self):
        if self._use_fallback():
            return self._fallback.list_all_appointments()
        try:
            return self._gcp_scheduling.list_all_appointments()
        except Exception:
            self.reachable = False
            logger.exception("Healthcare API appointment list-all failed")
            if self._fallback_on_miss:
                return self._fallback.list_all_appointments()
            raise

    def operations_snapshot(self):
        if self._use_fallback():
            return self._fallback.operations_snapshot()
        try:
            return self._gcp_scheduling.operations_snapshot()
        except Exception:
            self.reachable = False
            logger.exception("Healthcare API operations snapshot failed")
            if self._fallback_on_miss:
                return self._fallback.operations_snapshot()
            raise
