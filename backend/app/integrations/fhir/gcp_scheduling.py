"""Cloud Healthcare FHIR R4 scheduling operations."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import httpx
from eir_shared.appointments import (
    AppointmentStatus,
    AppointmentView,
    SlotSearchParams,
    SlotStatus,
    SlotView,
)

logger = logging.getLogger("eir.fhir.scheduling")

_EIR_NS = "https://eir.local/scheduling"
_EXT_SYNTHETIC_PATIENT = f"{_EIR_NS}/synthetic-patient-id"
_EXT_SPECIALTY = f"{_EIR_NS}/specialty"
_EXT_SERVICE = f"{_EIR_NS}/service-name"
_EXT_PRACTITIONER_NAME = f"{_EIR_NS}/practitioner-name"
_EXT_PRACTITIONER_ID = f"{_EIR_NS}/practitioner-id"
_EXT_LOCATION_NAME = f"{_EIR_NS}/location-name"
_EXT_LOCATION_ID = f"{_EIR_NS}/location-id"
_EXT_APPOINTMENT_TYPE = f"{_EIR_NS}/appointment-type"
_EXT_IDEMPOTENCY = f"{_EIR_NS}/idempotency-key"
_EXT_CANCELLATION = f"{_EIR_NS}/cancellation-reason"


def _parse_dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _ext_string(resource: dict[str, Any], url: str) -> str | None:
    for item in resource.get("extension") or []:
        if item.get("url") == url:
            return item.get("valueString")
    return None


def _with_extensions(resource: dict[str, Any], **fields: str) -> dict[str, Any]:
    extensions = list(resource.get("extension") or [])
    existing = {item.get("url"): item for item in extensions if item.get("url")}
    mapping = {
        "synthetic_patient_id": _EXT_SYNTHETIC_PATIENT,
        "specialty": _EXT_SPECIALTY,
        "service_name": _EXT_SERVICE,
        "practitioner_name": _EXT_PRACTITIONER_NAME,
        "practitioner_id": _EXT_PRACTITIONER_ID,
        "location_name": _EXT_LOCATION_NAME,
        "location_id": _EXT_LOCATION_ID,
        "appointment_type": _EXT_APPOINTMENT_TYPE,
        "idempotency_key": _EXT_IDEMPOTENCY,
        "cancellation_reason": _EXT_CANCELLATION,
    }
    for key, value in fields.items():
        if not value:
            continue
        url = mapping[key]
        existing[url] = {"url": url, "valueString": value}
    resource["extension"] = list(existing.values())
    return resource


def _slot_refs(resource: dict[str, Any]) -> list[str]:
    refs: list[str] = []
    for item in resource.get("slot") or []:
        ref = (item or {}).get("reference")
        if isinstance(ref, str) and ref.startswith("Slot/"):
            refs.append(ref.split("/", 1)[1])
    return refs


def _participant_patient_id(resource: dict[str, Any]) -> str | None:
    synthetic = _ext_string(resource, _EXT_SYNTHETIC_PATIENT)
    if synthetic:
        return synthetic
    for participant in resource.get("participant") or []:
        ref = ((participant or {}).get("actor") or {}).get("reference", "")
        if isinstance(ref, str) and ref.startswith("Patient/"):
            return ref.split("/", 1)[1]
    return None


def appointment_view_from_fhir(resource: dict[str, Any]) -> AppointmentView | None:
    appointment_id = resource.get("id")
    patient_id = _participant_patient_id(resource)
    start = resource.get("start")
    end = resource.get("end")
    if not appointment_id or not patient_id or not start or not end:
        return None
    slot_id = _slot_refs(resource)[0] if _slot_refs(resource) else None
    try:
        status = AppointmentStatus(str(resource.get("status", "proposed")))
    except ValueError:
        status = AppointmentStatus.PROPOSED
    return AppointmentView(
        id=str(appointment_id),
        patient_id=str(patient_id),
        status=status,
        specialty=_ext_string(resource, _EXT_SPECIALTY) or "",
        service_name=_ext_string(resource, _EXT_SERVICE) or "",
        practitioner_name=_ext_string(resource, _EXT_PRACTITIONER_NAME) or "",
        practitioner_id=_ext_string(resource, _EXT_PRACTITIONER_ID) or "",
        location_name=_ext_string(resource, _EXT_LOCATION_NAME) or "",
        location_id=_ext_string(resource, _EXT_LOCATION_ID) or "",
        start=_parse_dt(str(start)),
        end=_parse_dt(str(end)),
        slot_id=slot_id,
        appointment_type=_ext_string(resource, _EXT_APPOINTMENT_TYPE) or "routine",
        cancellation_reason=_ext_string(resource, _EXT_CANCELLATION) or "",
    )


def slot_view_from_fhir(resource: dict[str, Any]) -> SlotView | None:
    slot_id = resource.get("id")
    schedule_ref = ((resource.get("schedule") or {}).get("reference") or "").split("/", 1)
    schedule_id = schedule_ref[1] if len(schedule_ref) == 2 else ""
    start = resource.get("start")
    end = resource.get("end")
    if not slot_id or not start or not end:
        return None
    try:
        status = SlotStatus(str(resource.get("status", "free")))
    except ValueError:
        status = SlotStatus.FREE
    return SlotView(
        id=str(slot_id),
        schedule_id=schedule_id,
        status=status,
        start=_parse_dt(str(start)),
        end=_parse_dt(str(end)),
        specialty=_ext_string(resource, _EXT_SPECIALTY) or "",
        service_name=_ext_string(resource, _EXT_SERVICE) or "",
        practitioner_name=_ext_string(resource, _EXT_PRACTITIONER_NAME) or "",
        practitioner_id=_ext_string(resource, _EXT_PRACTITIONER_ID) or "",
        location_name=_ext_string(resource, _EXT_LOCATION_NAME) or "",
        location_id=_ext_string(resource, _EXT_LOCATION_ID) or "",
        appointment_type=_ext_string(resource, _EXT_APPOINTMENT_TYPE) or "routine",
    )


class GcpSchedulingClient:
    def __init__(
        self,
        *,
        base_url: str,
        headers: Callable[[], dict[str, str]],
        patient_ref: Callable[[str], str | None],
    ) -> None:
        self._base = base_url
        self._headers = headers
        self._patient_ref = patient_ref
        self.reachable = True

    def _get_resource(self, resource_type: str, resource_id: str) -> dict[str, Any] | None:
        response = httpx.get(
            f"{self._base}/{resource_type}/{resource_id}",
            headers=self._headers(),
            timeout=20,
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()

    def _search(self, resource_type: str, params: dict[str, str]) -> list[dict[str, Any]]:
        response = httpx.get(
            f"{self._base}/{resource_type}",
            params=params,
            headers=self._headers(),
            timeout=20,
        )
        response.raise_for_status()
        entries = response.json().get("entry") or []
        return [item["resource"] for item in entries if item.get("resource")]

    def _transaction(self, bundle: dict[str, Any]) -> dict[str, Any]:
        response = httpx.post(
            self._base,
            headers=self._headers(),
            json=bundle,
            timeout=60,
        )
        if response.status_code in {409, 412}:
            raise ValueError("resource conflict")
        if response.status_code >= 400:
            detail = response.text[:500]
            raise RuntimeError(f"FHIR transaction failed ({response.status_code}): {detail}")
        return response.json() if response.content else {}

    def list_appointments(self, patient_id: str) -> list[AppointmentView]:
        patient_ref = self._patient_ref(patient_id)
        if patient_ref is None:
            return []
        resources = self._search("Appointment", {"patient": patient_ref})
        views: list[AppointmentView] = []
        for resource in resources:
            view = appointment_view_from_fhir(resource)
            if view is None:
                continue
            if view.patient_id not in {patient_id, patient_ref.split("/", 1)[-1]}:
                synthetic = _ext_string(resource, _EXT_SYNTHETIC_PATIENT)
                if synthetic != patient_id:
                    continue
            views.append(view)
        views.sort(key=lambda item: item.start)
        return views

    def list_all_appointments(self) -> list[AppointmentView]:
        resources = self._search("Appointment", {})
        views = [appointment_view_from_fhir(item) for item in resources]
        return [item for item in views if item is not None]

    def get_appointment(self, appointment_id: str) -> AppointmentView | None:
        resource = self._get_resource("Appointment", appointment_id)
        if resource is None:
            return None
        return appointment_view_from_fhir(resource)

    def search_available_slots(self, params: SlotSearchParams) -> list[SlotView]:
        now = datetime.now(UTC)
        query: dict[str, str] = {"status": SlotStatus.FREE.value}
        if params.start_date:
            query["start"] = f"ge{params.start_date.astimezone(UTC).isoformat()}"
        resources = self._search("Slot", query)
        candidates: list[SlotView] = []
        for resource in resources:
            view = slot_view_from_fhir(resource)
            if view is None or view.status != SlotStatus.FREE or view.start <= now:
                continue
            if params.specialty and params.specialty.lower() not in view.specialty.lower():
                continue
            if params.service_name and params.service_name.lower() not in view.service_name.lower():
                continue
            if params.location_id and view.location_id != params.location_id:
                continue
            if params.practitioner_id and view.practitioner_id != params.practitioner_id:
                continue
            if params.end_date and view.start.date() > params.end_date.date():
                continue
            if params.time_of_day == "morning" and view.start.hour >= 12:
                continue
            if params.time_of_day == "afternoon" and view.start.hour < 12:
                continue
            candidates.append(view)
        candidates.sort(key=lambda item: item.start)
        return candidates[: max(1, min(params.limit, 12))]

    def _find_by_idempotency(self, key: str) -> AppointmentView | None:
        resources = self._search("Appointment", {})
        for resource in resources:
            if _ext_string(resource, _EXT_IDEMPOTENCY) == key:
                return appointment_view_from_fhir(resource)
        return None

    def book_appointment(
        self,
        *,
        patient_id: str,
        slot_id: str,
        idempotency_key: str = "",
    ) -> AppointmentView:
        key = idempotency_key or f"book:{patient_id}:{slot_id}"
        existing = self._find_by_idempotency(key)
        if existing:
            return existing
        patient_ref = self._patient_ref(patient_id)
        if patient_ref is None:
            raise ValueError("patient not found")
        slot = self._get_resource("Slot", slot_id)
        if slot is None or slot.get("status") != SlotStatus.FREE.value:
            raise ValueError("slot is not available")
        slot_view = slot_view_from_fhir(slot)
        if slot_view is None:
            raise ValueError("slot is not available")
        appointment_id = f"appt-{uuid4().hex[:10]}"
        appointment = {
            "resourceType": "Appointment",
            "id": appointment_id,
            "status": AppointmentStatus.BOOKED.value,
            "start": slot.get("start"),
            "end": slot.get("end"),
            "slot": [{"reference": f"Slot/{slot_id}"}],
            "participant": [
                {"actor": {"reference": patient_ref}, "status": "accepted"},
            ],
        }
        if slot_view.practitioner_id:
            appointment["participant"].append(
                {
                    "actor": {"reference": f"Practitioner/{slot_view.practitioner_id}"},
                    "status": "accepted",
                }
            )
        _with_extensions(
            appointment,
            synthetic_patient_id=patient_id,
            specialty=slot_view.specialty,
            service_name=slot_view.service_name,
            practitioner_name=slot_view.practitioner_name,
            practitioner_id=slot_view.practitioner_id,
            location_name=slot_view.location_name,
            location_id=slot_view.location_id,
            appointment_type=slot_view.appointment_type,
            idempotency_key=key,
        )
        busy_slot = dict(slot)
        busy_slot["status"] = SlotStatus.BUSY.value
        version = ((slot.get("meta") or {}).get("versionId")) or ""
        bundle = {
            "resourceType": "Bundle",
            "type": "transaction",
            "entry": [
                {
                    "resource": busy_slot,
                    "request": {
                        "method": "PUT",
                        "url": f"Slot/{slot_id}",
                        **({"ifMatch": f'W/"{version}"'} if version else {}),
                    },
                },
                {
                    "resource": appointment,
                    "request": {"method": "PUT", "url": f"Appointment/{appointment_id}"},
                },
            ],
        }
        self._transaction(bundle)
        found = self.get_appointment(appointment_id)
        if found is None:
            raise RuntimeError("appointment create verification failed")
        return found

    def reschedule_appointment(
        self,
        *,
        appointment_id: str,
        patient_id: str,
        new_slot_id: str,
        idempotency_key: str = "",
    ) -> AppointmentView:
        key = idempotency_key or f"reschedule:{appointment_id}:{new_slot_id}"
        existing = self._find_by_idempotency(key)
        if existing:
            return existing
        appointment = self._get_resource("Appointment", appointment_id)
        if appointment is None:
            raise ValueError("appointment not found")
        owner = _participant_patient_id(appointment)
        if owner != patient_id:
            raise PermissionError("appointment ownership mismatch")
        if appointment.get("status") not in {
            AppointmentStatus.BOOKED.value,
            AppointmentStatus.PENDING.value,
            AppointmentStatus.PROPOSED.value,
        }:
            raise ValueError("appointment cannot be rescheduled")
        new_slot = self._get_resource("Slot", new_slot_id)
        if new_slot is None or new_slot.get("status") != SlotStatus.FREE.value:
            raise ValueError("new slot is not available")
        new_view = slot_view_from_fhir(new_slot)
        if new_view is None:
            raise ValueError("new slot is not available")
        entries: list[dict[str, Any]] = []
        old_slot_ids = _slot_refs(appointment)
        for old_slot_id in old_slot_ids:
            old_slot = self._get_resource("Slot", old_slot_id)
            if old_slot is None:
                continue
            released = dict(old_slot)
            released["status"] = SlotStatus.FREE.value
            version = ((old_slot.get("meta") or {}).get("versionId")) or ""
            entries.append(
                {
                    "resource": released,
                    "request": {
                        "method": "PUT",
                        "url": f"Slot/{old_slot_id}",
                        **({"ifMatch": f'W/"{version}"'} if version else {}),
                    },
                }
            )
        busy_slot = dict(new_slot)
        busy_slot["status"] = SlotStatus.BUSY.value
        new_version = ((new_slot.get("meta") or {}).get("versionId")) or ""
        entries.append(
            {
                "resource": busy_slot,
                "request": {
                    "method": "PUT",
                    "url": f"Slot/{new_slot_id}",
                    **({"ifMatch": f'W/"{new_version}"'} if new_version else {}),
                },
            }
        )
        updated = dict(appointment)
        updated["status"] = AppointmentStatus.BOOKED.value
        updated["start"] = new_slot.get("start")
        updated["end"] = new_slot.get("end")
        updated["slot"] = [{"reference": f"Slot/{new_slot_id}"}]
        _with_extensions(
            updated,
            specialty=new_view.specialty,
            service_name=new_view.service_name,
            practitioner_name=new_view.practitioner_name,
            practitioner_id=new_view.practitioner_id,
            location_name=new_view.location_name,
            location_id=new_view.location_id,
            appointment_type=new_view.appointment_type,
            idempotency_key=key,
        )
        appt_version = ((appointment.get("meta") or {}).get("versionId")) or ""
        entries.append(
            {
                "resource": updated,
                "request": {
                    "method": "PUT",
                    "url": f"Appointment/{appointment_id}",
                    **({"ifMatch": f'W/"{appt_version}"'} if appt_version else {}),
                },
            }
        )
        self._transaction({"resourceType": "Bundle", "type": "transaction", "entry": entries})
        found = self.get_appointment(appointment_id)
        if found is None:
            raise RuntimeError("appointment reschedule verification failed")
        return found

    def cancel_appointment(
        self,
        *,
        appointment_id: str,
        patient_id: str,
        reason: str = "",
        confirmed: bool = False,
    ) -> AppointmentView:
        if not confirmed:
            raise ValueError("cancellation requires explicit confirmation")
        appointment = self._get_resource("Appointment", appointment_id)
        if appointment is None:
            raise ValueError("appointment not found")
        owner = _participant_patient_id(appointment)
        if owner != patient_id:
            raise PermissionError("appointment ownership mismatch")
        if appointment.get("status") == AppointmentStatus.CANCELLED.value:
            return appointment_view_from_fhir(appointment)  # type: ignore[return-value]
        entries: list[dict[str, Any]] = []
        for slot_id in _slot_refs(appointment):
            slot = self._get_resource("Slot", slot_id)
            if slot is None:
                continue
            released = dict(slot)
            released["status"] = SlotStatus.FREE.value
            version = ((slot.get("meta") or {}).get("versionId")) or ""
            entries.append(
                {
                    "resource": released,
                    "request": {
                        "method": "PUT",
                        "url": f"Slot/{slot_id}",
                        **({"ifMatch": f'W/"{version}"'} if version else {}),
                    },
                }
            )
        updated = dict(appointment)
        updated["status"] = AppointmentStatus.CANCELLED.value
        _with_extensions(updated, cancellation_reason=reason[:240])
        appt_version = ((appointment.get("meta") or {}).get("versionId")) or ""
        entries.append(
            {
                "resource": updated,
                "request": {
                    "method": "PUT",
                    "url": f"Appointment/{appointment_id}",
                    **({"ifMatch": f'W/"{appt_version}"'} if appt_version else {}),
                },
            }
        )
        self._transaction({"resourceType": "Bundle", "type": "transaction", "entry": entries})
        found = self.get_appointment(appointment_id)
        if found is None:
            raise RuntimeError("appointment cancel verification failed")
        return found

    def operations_snapshot(self) -> dict[str, int]:
        appointments = self.list_all_appointments()
        slots = self._search("Slot", {"status": SlotStatus.FREE.value})
        today = datetime.now(UTC).date()
        week = today + timedelta(days=7)
        return {
            "today_appointments": len(
                [item for item in appointments if item.start.date() == today]
            ),
            "next_7_days": len(
                [
                    item
                    for item in appointments
                    if item.status != AppointmentStatus.CANCELLED
                    and today <= item.start.date() <= week
                ]
            ),
            "open_slots": len(slots),
            "rescheduled_today": 0,
            "cancelled_today": len(
                [item for item in appointments if item.status == AppointmentStatus.CANCELLED]
            ),
        }