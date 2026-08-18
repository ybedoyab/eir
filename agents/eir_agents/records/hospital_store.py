"""Synthetic hospital scheduling store backed by mocks/hospital fixtures."""

from __future__ import annotations

import json
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

from eir_shared.appointments import (
    AppointmentReminder,
    AppointmentStatus,
    AppointmentView,
    SlotSearchParams,
    SlotStatus,
    SlotView,
    WaitlistRequest,
)


def _default_hospital_dir() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "mocks" / "hospital"
        if candidate.is_dir():
            return candidate
    return Path("mocks/hospital")


def _parse_dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _slot_view(raw: dict[str, Any]) -> SlotView:
    return SlotView(
        id=str(raw["id"]),
        schedule_id=str(raw["schedule_id"]),
        status=SlotStatus(str(raw["status"])),
        start=_parse_dt(str(raw["start"])),
        end=_parse_dt(str(raw["end"])),
        specialty=str(raw["specialty"]),
        service_name=str(raw["service_name"]),
        practitioner_name=str(raw["practitioner_name"]),
        practitioner_id=str(raw["practitioner_id"]),
        location_name=str(raw["location_name"]),
        location_id=str(raw["location_id"]),
        appointment_type=str(raw.get("appointment_type", "routine")),
    )


def _appointment_view(raw: dict[str, Any]) -> AppointmentView:
    return AppointmentView(
        id=str(raw["id"]),
        patient_id=str(raw["patient_id"]),
        status=AppointmentStatus(str(raw["status"])),
        specialty=str(raw["specialty"]),
        service_name=str(raw["service_name"]),
        practitioner_name=str(raw["practitioner_name"]),
        practitioner_id=str(raw.get("practitioner_id", "")),
        location_name=str(raw["location_name"]),
        location_id=str(raw.get("location_id", "")),
        start=_parse_dt(str(raw["start"])),
        end=_parse_dt(str(raw["end"])),
        slot_id=raw.get("slot_id"),
        appointment_type=str(raw.get("appointment_type", "routine")),
        cancellation_reason=str(raw.get("cancellation_reason", "")),
    )


class HospitalSchedulingStore:
    def __init__(self, hospital_dir: Path | None = None) -> None:
        self._dir = hospital_dir or _default_hospital_dir()
        self._lock = threading.RLock()
        from eir_shared.demo_hospital import build_appointments, build_slots

        self._slots = build_slots()
        self._appointments = build_appointments(self._slots)
        self._waitlist = self._load_list("waitlist.json")
        self._reminders = self._load_list("reminders.json")
        self._idempotency: dict[str, str] = {}

    def _load_list(self, filename: str) -> list[dict[str, Any]]:
        path = self._dir / filename
        if not path.is_file():
            return []
        return json.loads(path.read_text(encoding="utf-8"))

    def list_appointments(self, patient_id: str) -> list[AppointmentView]:
        with self._lock:
            return [
                _appointment_view(item)
                for item in self._appointments
                if item.get("patient_id") == patient_id
            ]

    def list_all_appointments(self) -> list[AppointmentView]:
        with self._lock:
            return [_appointment_view(item) for item in self._appointments]

    def get_appointment(self, appointment_id: str) -> AppointmentView | None:
        with self._lock:
            for item in self._appointments:
                if item.get("id") == appointment_id:
                    return _appointment_view(item)
        return None

    def search_available_slots(self, params: SlotSearchParams) -> list[SlotView]:
        now = datetime.now(UTC)
        with self._lock:
            candidates = [
                _slot_view(item)
                for item in self._slots
                if item.get("status") == SlotStatus.FREE.value
            ]
        filtered: list[SlotView] = []
        for slot in candidates:
            if slot.start <= now:
                continue
            if params.specialty and params.specialty.lower() not in slot.specialty.lower():
                continue
            if params.service_name and params.service_name.lower() not in slot.service_name.lower():
                continue
            if params.location_id and slot.location_id != params.location_id:
                continue
            if params.practitioner_id and slot.practitioner_id != params.practitioner_id:
                continue
            if params.start_date and slot.start.date() < params.start_date.date():
                continue
            if params.end_date and slot.start.date() > params.end_date.date():
                continue
            if params.time_of_day == "morning" and slot.start.hour >= 12:
                continue
            if params.time_of_day == "afternoon" and slot.start.hour < 12:
                continue
            filtered.append(slot)
        filtered.sort(key=lambda item: item.start)
        return filtered[: max(1, min(params.limit, 12))]

    def book_appointment(
        self,
        *,
        patient_id: str,
        slot_id: str,
        idempotency_key: str = "",
    ) -> AppointmentView:
        key = idempotency_key or f"book:{patient_id}:{slot_id}"
        with self._lock:
            existing_id = self._idempotency.get(key)
            if existing_id:
                found = self.get_appointment(existing_id)
                if found:
                    return found
            slot = self._find_slot(slot_id)
            if slot is None or slot.get("status") != SlotStatus.FREE.value:
                raise ValueError("slot is not available")
            appointment_id = f"appt-{uuid4().hex[:10]}"
            appointment = {
                "id": appointment_id,
                "patient_id": patient_id,
                "status": AppointmentStatus.BOOKED.value,
                "specialty": slot["specialty"],
                "service_name": slot["service_name"],
                "practitioner_id": slot["practitioner_id"],
                "practitioner_name": slot["practitioner_name"],
                "location_id": slot["location_id"],
                "location_name": slot["location_name"],
                "start": slot["start"],
                "end": slot["end"],
                "slot_id": slot_id,
                "appointment_type": slot.get("appointment_type", "routine"),
            }
            slot["status"] = SlotStatus.BUSY.value
            self._appointments.append(appointment)
            self._idempotency[key] = appointment_id
            self._schedule_reminder(appointment)
            return _appointment_view(appointment)

    def reschedule_appointment(
        self,
        *,
        appointment_id: str,
        patient_id: str,
        new_slot_id: str,
        idempotency_key: str = "",
    ) -> AppointmentView:
        key = idempotency_key or f"reschedule:{appointment_id}:{new_slot_id}"
        with self._lock:
            existing_id = self._idempotency.get(key)
            if existing_id:
                found = self.get_appointment(existing_id)
                if found:
                    return found
            appointment = self._find_appointment(appointment_id)
            if appointment is None:
                raise ValueError("appointment not found")
            if appointment.get("patient_id") != patient_id:
                raise PermissionError("appointment ownership mismatch")
            if appointment.get("status") not in {
                AppointmentStatus.BOOKED.value,
                AppointmentStatus.PENDING.value,
                AppointmentStatus.PROPOSED.value,
            }:
                raise ValueError("appointment cannot be rescheduled")
            new_slot = self._find_slot(new_slot_id)
            if new_slot is None or new_slot.get("status") != SlotStatus.FREE.value:
                raise ValueError("new slot is not available")
            old_slot_id = appointment.get("slot_id")
            if old_slot_id:
                old_slot = self._find_slot(str(old_slot_id))
                if old_slot is not None:
                    old_slot["status"] = SlotStatus.FREE.value
            new_slot["status"] = SlotStatus.BUSY.value
            appointment["slot_id"] = new_slot_id
            appointment["start"] = new_slot["start"]
            appointment["end"] = new_slot["end"]
            appointment["status"] = AppointmentStatus.BOOKED.value
            self._idempotency[key] = appointment_id
            self._schedule_reminder(appointment)
            return _appointment_view(appointment)

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
        with self._lock:
            appointment = self._find_appointment(appointment_id)
            if appointment is None:
                raise ValueError("appointment not found")
            if appointment.get("patient_id") != patient_id:
                raise PermissionError("appointment ownership mismatch")
            if appointment.get("status") == AppointmentStatus.CANCELLED.value:
                return _appointment_view(appointment)
            slot_id = appointment.get("slot_id")
            if slot_id:
                slot = self._find_slot(str(slot_id))
                if slot is not None:
                    slot["status"] = SlotStatus.FREE.value
                    self._notify_waitlist_for_slot(str(slot_id))
            appointment["status"] = AppointmentStatus.CANCELLED.value
            appointment["cancellation_reason"] = reason[:240]
            return _appointment_view(appointment)

    def join_waitlist(
        self,
        *,
        patient_id: str,
        appointment_id: str,
    ) -> WaitlistRequest:
        appointment = self.get_appointment(appointment_id)
        if appointment is None:
            raise ValueError("appointment not found")
        if appointment.patient_id != patient_id:
            raise PermissionError("appointment ownership mismatch")
        request = WaitlistRequest(
            id=f"waitlist-{uuid4().hex[:8]}",
            patient_id=patient_id,
            appointment_id=appointment_id,
            specialty=appointment.specialty,
        )
        with self._lock:
            self._waitlist.append(request.model_dump(mode="json"))
        return request

    def list_waitlist(self, patient_id: str | None = None) -> list[WaitlistRequest]:
        with self._lock:
            items = [WaitlistRequest.model_validate(item) for item in self._waitlist]
        if patient_id:
            return [item for item in items if item.patient_id == patient_id]
        return items

    def list_reminders(self, patient_id: str | None = None) -> list[AppointmentReminder]:
        with self._lock:
            items = [AppointmentReminder.model_validate(item) for item in self._reminders]
        if patient_id:
            return [item for item in items if item.patient_id == patient_id]
        return items

    def operations_snapshot(self) -> dict[str, int]:
        appointments = self.list_all_appointments()
        free_slots = len([item for item in self._slots if item.get("status") == "free"])
        today = datetime.now(UTC).date()
        today_appts = len([item for item in appointments if item.start.date() == today])
        week = today + timedelta(days=7)
        next_7 = len(
            [
                item
                for item in appointments
                if item.status != AppointmentStatus.CANCELLED and today <= item.start.date() <= week
            ]
        )
        rescheduled = len([key for key in self._idempotency if key.startswith("reschedule:")])
        cancelled = len(
            [item for item in appointments if item.status == AppointmentStatus.CANCELLED]
        )
        return {
            "today_appointments": today_appts,
            "next_7_days": next_7,
            "open_slots": free_slots,
            "rescheduled_today": rescheduled,
            "cancelled_today": cancelled,
            "waitlist_requests": len(self._waitlist),
        }

    def _find_slot(self, slot_id: str) -> dict[str, Any] | None:
        for item in self._slots:
            if item.get("id") == slot_id:
                return item
        return None

    def _find_appointment(self, appointment_id: str) -> dict[str, Any] | None:
        for item in self._appointments:
            if item.get("id") == appointment_id:
                return item
        return None

    def _schedule_reminder(self, appointment: dict[str, Any]) -> None:
        start = _parse_dt(str(appointment["start"]))
        reminder_time = start - timedelta(hours=24)
        if reminder_time <= datetime.now(UTC):
            reminder_time = datetime.now(UTC) + timedelta(minutes=5)
        reminder = AppointmentReminder(
            id=f"reminder-{uuid4().hex[:8]}",
            appointment_id=str(appointment["id"]),
            patient_id=str(appointment["patient_id"]),
            scheduled_for=reminder_time,
        )
        self._reminders.append(reminder.model_dump(mode="json"))

    def _notify_waitlist_for_slot(self, slot_id: str) -> None:
        slot = self._find_slot(slot_id)
        if slot is None:
            return
        specialty = str(slot.get("specialty", ""))
        for item in self._waitlist:
            if item.get("status") != "active":
                continue
            if item.get("specialty") != specialty:
                continue
            item["status"] = "notified"
            item["candidate_slot_id"] = slot_id
