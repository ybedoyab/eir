"""Firestore-backed operational scheduling state (waitlist, reminders)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from eir_shared.appointments import AppointmentReminder, AppointmentView, WaitlistRequest


class InMemoryOperationalSchedulingStore:
    def __init__(self) -> None:
        self._waitlist: list[dict[str, Any]] = []
        self._reminders: list[dict[str, Any]] = []

    def join_waitlist(
        self,
        *,
        patient_id: str,
        appointment: AppointmentView,
    ) -> WaitlistRequest:
        request = WaitlistRequest(
            id=f"waitlist-{uuid4().hex[:8]}",
            patient_id=patient_id,
            appointment_id=appointment.id,
            specialty=appointment.specialty,
        )
        self._waitlist.append(request.model_dump(mode="json"))
        return request

    def list_waitlist(self, patient_id: str | None = None) -> list[WaitlistRequest]:
        items = [WaitlistRequest.model_validate(item) for item in self._waitlist]
        if patient_id:
            return [item for item in items if item.patient_id == patient_id]
        return items

    def schedule_reminder(self, appointment: AppointmentView) -> AppointmentReminder:
        reminder_time = appointment.start - timedelta(hours=24)
        if reminder_time <= datetime.now(UTC):
            reminder_time = datetime.now(UTC) + timedelta(minutes=5)
        reminder = AppointmentReminder(
            id=f"reminder-{uuid4().hex[:8]}",
            appointment_id=appointment.id,
            patient_id=appointment.patient_id,
            scheduled_for=reminder_time,
        )
        self._reminders.append(reminder.model_dump(mode="json"))
        return reminder

    def list_reminders(self, patient_id: str | None = None) -> list[AppointmentReminder]:
        items = [AppointmentReminder.model_validate(item) for item in self._reminders]
        if patient_id:
            return [item for item in items if item.patient_id == patient_id]
        return items


class FirestoreOperationalSchedulingStore:
    def __init__(self, client: Any) -> None:
        self._waitlist = client.collection("eir_waitlist")
        self._reminders = client.collection("eir_reminders")

    def join_waitlist(
        self,
        *,
        patient_id: str,
        appointment: AppointmentView,
    ) -> WaitlistRequest:
        request = WaitlistRequest(
            id=f"waitlist-{uuid4().hex[:8]}",
            patient_id=patient_id,
            appointment_id=appointment.id,
            specialty=appointment.specialty,
        )
        self._waitlist.document(request.id).set(request.model_dump(mode="json"))
        return request

    def list_waitlist(self, patient_id: str | None = None) -> list[WaitlistRequest]:
        if patient_id:
            docs = self._waitlist.where("patient_id", "==", patient_id).stream()
        else:
            docs = self._waitlist.stream()
        return [WaitlistRequest.model_validate(doc.to_dict() or {}) for doc in docs]

    def schedule_reminder(self, appointment: AppointmentView) -> AppointmentReminder:
        reminder_time = appointment.start - timedelta(hours=24)
        if reminder_time <= datetime.now(UTC):
            reminder_time = datetime.now(UTC) + timedelta(minutes=5)
        reminder = AppointmentReminder(
            id=f"reminder-{uuid4().hex[:8]}",
            appointment_id=appointment.id,
            patient_id=appointment.patient_id,
            scheduled_for=reminder_time,
        )
        self._reminders.document(reminder.id).set(reminder.model_dump(mode="json"))
        return reminder

    def list_reminders(self, patient_id: str | None = None) -> list[AppointmentReminder]:
        if patient_id:
            docs = self._reminders.where("patient_id", "==", patient_id).stream()
        else:
            docs = self._reminders.stream()
        return [AppointmentReminder.model_validate(doc.to_dict() or {}) for doc in docs]
