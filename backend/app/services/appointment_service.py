"""Canonical appointment business rules."""

from __future__ import annotations

from eir_agents.records.fhir_client import FhirClient
from eir_shared.appointments import AppointmentView, SlotSearchParams, SlotView, WaitlistRequest
from eir_shared.auth import DemoRole


class AppointmentService:
    def __init__(self, fhir: FhirClient) -> None:
        self._fhir = fhir

    def list_for_actor(
        self,
        *,
        role: str,
        patient_id: str | None,
        target_patient_id: str | None = None,
    ) -> list[AppointmentView]:
        if role == DemoRole.PATIENT.value:
            if not patient_id:
                raise PermissionError("patient identity required")
            return self._fhir.list_appointments(patient_id)
        if role in {DemoRole.CLINICIAN.value, DemoRole.OPERATIONS_ADMIN.value}:
            if target_patient_id:
                return self._fhir.list_appointments(target_patient_id)
            return self._fhir.list_all_appointments()
        raise PermissionError("unsupported role")

    def get_for_actor(
        self,
        *,
        role: str,
        actor_patient_id: str | None,
        appointment_id: str,
    ) -> AppointmentView:
        appointment = self._fhir.get_appointment(appointment_id)
        if appointment is None:
            raise ValueError("appointment not found")
        if role == DemoRole.PATIENT.value and appointment.patient_id != actor_patient_id:
            raise PermissionError("appointment ownership mismatch")
        return appointment

    def search_slots(self, params: SlotSearchParams) -> list[SlotView]:
        return self._fhir.search_available_slots(params)

    def book(
        self,
        *,
        patient_id: str,
        slot_id: str,
        idempotency_key: str = "",
    ) -> AppointmentView:
        return self._fhir.book_appointment(
            patient_id=patient_id,
            slot_id=slot_id,
            idempotency_key=idempotency_key,
        )

    def reschedule(
        self,
        *,
        appointment_id: str,
        patient_id: str,
        new_slot_id: str,
        idempotency_key: str = "",
    ) -> AppointmentView:
        return self._fhir.reschedule_appointment(
            appointment_id=appointment_id,
            patient_id=patient_id,
            new_slot_id=new_slot_id,
            idempotency_key=idempotency_key,
        )

    def cancel(
        self,
        *,
        appointment_id: str,
        patient_id: str,
        reason: str = "",
        confirmed: bool = False,
    ) -> AppointmentView:
        return self._fhir.cancel_appointment(
            appointment_id=appointment_id,
            patient_id=patient_id,
            reason=reason,
            confirmed=confirmed,
        )

    def waitlist(self, *, patient_id: str, appointment_id: str) -> WaitlistRequest:
        return self._fhir.join_waitlist(
            patient_id=patient_id,
            appointment_id=appointment_id,
        )

    def operations_snapshot(self) -> dict[str, int]:
        return self._fhir.operations_snapshot()
