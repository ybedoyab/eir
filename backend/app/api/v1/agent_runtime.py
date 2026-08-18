"""Protected tool boundary for managed Agent Runtime. Delegates to AppointmentService."""

from __future__ import annotations

from typing import Any

from eir_shared.appointments import SlotSearchParams
from eir_shared.auth import DemoRole
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.api.deps.agent_identity import AgentRuntimeAuth, bound_synthetic_user
from app.core.deps import get_container

router = APIRouter()


class RescheduleBody(BaseModel):
    synthetic_user_id: str
    slot_id: str = Field(min_length=1)


class CancelBody(BaseModel):
    synthetic_user_id: str
    reason: str = ""
    confirmed: bool = False


def _patient_claims(synthetic_user_id: str) -> dict[str, Any]:
    user_id = bound_synthetic_user(synthetic_user_id)
    return {"role": DemoRole.PATIENT.value, "patient_id": user_id}


@router.get("/appointments")
def list_appointments(
    _auth: AgentRuntimeAuth,
    synthetic_user_id: str = Query(...),
) -> list[dict]:
    claims = _patient_claims(synthetic_user_id)
    items = get_container().appointments.list_for_actor(
        role=claims["role"],
        patient_id=claims["patient_id"],
        target_patient_id=None,
    )
    return [item.model_dump(mode="json") for item in items]


@router.get("/appointments/availability")
def search_availability(
    _auth: AgentRuntimeAuth,
    synthetic_user_id: str = Query(...),
    specialty: str = "",
    time_of_day: str = "any",
    location_name: str = "",
    limit: int = 6,
) -> list[dict]:
    claims = _patient_claims(synthetic_user_id)
    location_id = ""
    if location_name:
        location_id = location_name
    params = SlotSearchParams(
        patient_id=str(claims["patient_id"]),
        specialty=specialty,
        location_id=location_id,
        time_of_day=time_of_day,
        limit=limit,
    )
    slots = get_container().appointments.search_slots(params)
    if location_name:
        wanted = location_name.lower()
        slots = [
            slot
            for slot in slots
            if wanted in slot.location_name.lower() or wanted in slot.location_id.lower()
        ]
    return [slot.model_dump(mode="json") for slot in slots]


@router.post("/appointments/{appointment_id}/reschedule")
def reschedule_appointment(
    appointment_id: str,
    body: RescheduleBody,
    _auth: AgentRuntimeAuth,
) -> dict:
    claims = _patient_claims(body.synthetic_user_id)
    try:
        appointment = get_container().appointments.reschedule(
            appointment_id=appointment_id,
            patient_id=str(claims["patient_id"]),
            new_slot_id=body.slot_id,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return appointment.model_dump(mode="json")


@router.post("/appointments/{appointment_id}/cancel")
def cancel_appointment(
    appointment_id: str,
    body: CancelBody,
    _auth: AgentRuntimeAuth,
) -> dict:
    claims = _patient_claims(body.synthetic_user_id)
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
