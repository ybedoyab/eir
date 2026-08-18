from typing import Annotated, Any

from eir_shared.appointments import SlotSearchParams
from eir_shared.auth import DemoRole
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel

from app.api.deps.auth import require_patient_access, require_role
from app.core.deps import get_container

router = APIRouter()

PortalClaims = Annotated[
    dict[str, Any],
    Depends(require_role(DemoRole.PATIENT, DemoRole.CLINICIAN, DemoRole.OPERATIONS_ADMIN)),
]
PatientClaims = Annotated[dict[str, Any], Depends(require_patient_access)]


class BookAppointmentRequest(BaseModel):
    slot_id: str


class RescheduleAppointmentRequest(BaseModel):
    slot_id: str


class CancelAppointmentRequest(BaseModel):
    reason: str = ""
    confirmed: bool = False


class WaitlistRequestBody(BaseModel):
    appointment_id: str


@router.get("")
def list_appointments(
    claims: PortalClaims,
    patient_id: str | None = Query(default=None),
) -> list[dict]:
    service = get_container().appointments
    try:
        items = service.list_for_actor(
            role=claims["role"],
            patient_id=claims.get("patient_id"),
            target_patient_id=patient_id,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return [item.model_dump(mode="json") for item in items]


@router.get("/availability")
def search_availability(
    claims: PatientClaims,
    specialty: str = "",
    location_id: str = "",
    practitioner_id: str = "",
    time_of_day: str = "any",
    limit: int = 6,
) -> list[dict]:
    params = SlotSearchParams(
        patient_id=str(claims["patient_id"]),
        specialty=specialty,
        location_id=location_id,
        practitioner_id=practitioner_id,
        time_of_day=time_of_day,
        limit=limit,
    )
    slots = get_container().appointments.search_slots(params)
    return [slot.model_dump(mode="json") for slot in slots]


@router.post("")
def book_appointment(
    body: BookAppointmentRequest,
    claims: PatientClaims,
    idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
) -> dict:
    try:
        appointment = get_container().appointments.book(
            patient_id=str(claims["patient_id"]),
            slot_id=body.slot_id,
            idempotency_key=idempotency_key or "",
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return appointment.model_dump(mode="json")


@router.post("/{appointment_id}/reschedule")
def reschedule_appointment(
    appointment_id: str,
    body: RescheduleAppointmentRequest,
    claims: PatientClaims,
    idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
) -> dict:
    try:
        appointment = get_container().appointments.reschedule(
            appointment_id=appointment_id,
            patient_id=str(claims["patient_id"]),
            new_slot_id=body.slot_id,
            idempotency_key=idempotency_key or "",
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return appointment.model_dump(mode="json")


@router.post("/{appointment_id}/cancel")
def cancel_appointment(
    appointment_id: str,
    body: CancelAppointmentRequest,
    claims: PatientClaims,
) -> dict:
    try:
        appointment = get_container().appointments.cancel(
            appointment_id=appointment_id,
            patient_id=str(claims["patient_id"]),
            reason=body.reason,
            confirmed=body.confirmed,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return appointment.model_dump(mode="json")


@router.post("/waitlist")
def join_waitlist(
    body: WaitlistRequestBody,
    claims: PatientClaims,
) -> dict:
    try:
        request = get_container().appointments.waitlist(
            patient_id=str(claims["patient_id"]),
            appointment_id=body.appointment_id,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return request.model_dump(mode="json")


@router.get("/reminders")
def list_reminders(
    claims: PatientClaims,
) -> list[dict]:
    reminders = get_container().fhir.list_reminders(str(claims["patient_id"]))
    return [item.model_dump(mode="json") for item in reminders]
