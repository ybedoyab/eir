"""Patient Access ADK tools — HTTP to eir-api only. No FHIR and no duplicated scheduling logic."""

from __future__ import annotations

import os
from typing import Any

import httpx

from eir_agents.access.constants import (
    ALLOWED_SYNTHETIC_USERS,
    DEFAULT_API_BASE_URL,
    SYNTHETIC_USER_ID,
)

_TIMEOUT = 30.0


def _api_base() -> str:
    return os.environ.get("EIR_API_BASE_URL", DEFAULT_API_BASE_URL).rstrip("/")


def _audience() -> str:
    return os.environ.get("EIR_API_AUDIENCE", _api_base())


def _identity_token() -> str:
    from google.auth.transport.requests import Request
    from google.oauth2 import id_token

    return id_token.fetch_id_token(Request(), _audience())


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_identity_token()}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _bound_user_id(tool_context: Any | None = None) -> str:
    user_id = SYNTHETIC_USER_ID
    if tool_context is not None:
        invocation = getattr(tool_context, "_invocation_context", None)
        candidate = getattr(tool_context, "user_id", None) or getattr(invocation, "user_id", None)
        session = getattr(tool_context, "session", None) or getattr(invocation, "session", None)
        if not candidate and session is not None:
            candidate = getattr(session, "user_id", None)
        if candidate:
            user_id = str(candidate)
    if user_id not in ALLOWED_SYNTHETIC_USERS:
        raise PermissionError("managed Patient Access tools cannot address that patient")
    return user_id


def _request(
    method: str,
    path: str,
    *,
    json: dict | None = None,
    params: dict | None = None,
) -> Any:
    url = f"{_api_base()}{path}"
    with httpx.Client(timeout=_TIMEOUT) as client:
        response = client.request(method, url, headers=_headers(), json=json, params=params)
        response.raise_for_status()
        if not response.content:
            return {}
        return response.json()


def get_upcoming_appointments(tool_context: Any | None = None) -> list[dict[str, Any]]:
    """List upcoming appointments for the authenticated synthetic patient only."""
    user_id = _bound_user_id(tool_context)
    payload = _request(
        "GET",
        "/api/v1/agent-runtime/appointments",
        params={"synthetic_user_id": user_id},
    )
    return payload if isinstance(payload, list) else payload.get("items", [])


def search_appointment_availability(
    specialty: str = "Cardiology",
    time_of_day: str = "afternoon",
    location_name: str = "",
    limit: int = 6,
    tool_context: Any | None = None,
) -> list[dict[str, Any]]:
    """Search free appointment slots via the EIR backend. No direct FHIR access."""
    user_id = _bound_user_id(tool_context)
    payload = _request(
        "GET",
        "/api/v1/agent-runtime/appointments/availability",
        params={
            "synthetic_user_id": user_id,
            "specialty": specialty,
            "time_of_day": time_of_day,
            "location_name": location_name,
            "limit": str(limit),
        },
    )
    return payload if isinstance(payload, list) else payload.get("items", [])


def reschedule_appointment(
    appointment_id: str,
    slot_id: str,
    tool_context: Any | None = None,
) -> dict[str, Any]:
    """Reschedule an owned appointment to a free slot via the EIR backend."""
    user_id = _bound_user_id(tool_context)
    return _request(
        "POST",
        f"/api/v1/agent-runtime/appointments/{appointment_id}/reschedule",
        json={"synthetic_user_id": user_id, "slot_id": slot_id},
    )


def cancel_appointment(
    appointment_id: str,
    reason: str = "synthetic-managed-agent",
    tool_context: Any | None = None,
) -> dict[str, Any]:
    """Cancel an owned appointment via the EIR backend. Requires confirmation in args."""
    user_id = _bound_user_id(tool_context)
    return _request(
        "POST",
        f"/api/v1/agent-runtime/appointments/{appointment_id}/cancel",
        json={"synthetic_user_id": user_id, "reason": reason, "confirmed": True},
    )
