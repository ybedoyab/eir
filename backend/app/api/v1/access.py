from typing import Annotated, Any

from eir_shared.auth import DemoRole
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.deps.auth import optional_claims, require_patient_access, require_role
from app.core.deps import get_container

router = APIRouter()


class CreateAccessSessionRequest(BaseModel):
    channel: str = "web"


class AccessMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


@router.post("/sessions")
def create_session(
    body: CreateAccessSessionRequest,
    claims: Annotated[dict[str, Any] | None, Depends(optional_claims)] = None,
) -> dict:
    patient_id = claims.get("patient_id") if claims else None
    session = get_container().access.create_session(
        patient_id=patient_id,
        channel=body.channel,
    )
    return session.model_dump(mode="json")


@router.get("/sessions/{session_id}")
def get_session(
    session_id: str,
    claims: Annotated[dict[str, Any] | None, Depends(optional_claims)] = None,
) -> dict:
    session = get_container().access.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if claims and claims.get("role") == DemoRole.PATIENT.value:
        if session.patient_id and session.patient_id != claims.get("patient_id"):
            raise HTTPException(status_code=403, detail="Session access denied")
    return session.model_dump(mode="json")


@router.post("/sessions/{session_id}/message")
def post_message(
    session_id: str,
    body: AccessMessageRequest,
    claims: Annotated[dict[str, Any], Depends(require_patient_access)],
) -> dict:
    try:
        return get_container().access.handle_message(
            session_id,
            body.message,
            patient_id=claims.get("patient_id"),
            role=claims.get("role", DemoRole.PATIENT.value),
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


PatientOrAdmin = Annotated[
    dict[str, Any],
    Depends(require_role(DemoRole.PATIENT, DemoRole.OPERATIONS_ADMIN)),
]


@router.get("/voice-tools")
def voice_tool_contract(_claims: PatientOrAdmin) -> dict:
    return {
        "description": "Gemini Live voice tools call authenticated EIR backend endpoints.",
        "tools": [
            "get_upcoming_appointments",
            "search_appointment_availability",
            "book_appointment",
            "reschedule_appointment",
            "cancel_appointment",
            "request_human_handoff",
        ],
        "endpoints": {
            "get_upcoming_appointments": "GET /api/v1/appointments",
            "search_appointment_availability": "GET /api/v1/appointments/availability",
            "book_appointment": "POST /api/v1/appointments",
            "reschedule_appointment": "POST /api/v1/appointments/{id}/reschedule",
            "cancel_appointment": "POST /api/v1/appointments/{id}/cancel",
            "request_human_handoff": "POST /api/v1/access/sessions/{id}/message",
        },
    }
