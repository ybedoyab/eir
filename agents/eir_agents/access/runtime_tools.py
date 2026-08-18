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


def _metadata_identity_token(audience: str) -> str:
    import urllib.parse
    import urllib.request

    params = urllib.parse.urlencode({"audience": audience, "format": "full"})
    request = urllib.request.Request(
        f"http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity?{params}",
        headers={"Metadata-Flavor": "Google"},
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        token = response.read().decode("utf-8").strip()
    if not token:
        raise RuntimeError("metadata identity token unavailable")
    return token


def _identity_token() -> str:
    from google.auth.transport.requests import Request
    from google.oauth2 import id_token

    audience = _audience()
    errors: list[str] = []
    try:
        from google.auth.compute_engine import IDTokenCredentials

        creds = IDTokenCredentials(
            Request(),
            target_audience=audience,
            use_metadata_identity_endpoint=True,
        )
        creds.refresh(Request())
        token = getattr(creds, "token", None)
        if token:
            return str(token)
    except Exception as exc:
        errors.append(type(exc).__name__)
    try:
        return _metadata_identity_token(audience)
    except Exception as exc:
        errors.append(type(exc).__name__)
    try:
        return id_token.fetch_id_token(Request(), audience)
    except Exception as exc:
        errors.append(type(exc).__name__)
        allowed = os.environ.get("EIR_ALLOW_IMPERSONATE_TOOL_SA", "").strip().lower()
        if allowed in {"1", "true", "yes"}:
            return _impersonated_identity_token(audience)
        raise RuntimeError(f"identity token unavailable ({', '.join(errors)})") from exc


def _impersonated_identity_token(audience: str) -> str:
    from google.auth import default, impersonated_credentials
    from google.auth.transport.requests import Request

    source, _ = default()
    principal = os.environ.get(
        "EIR_TOOL_IMPERSONATE_SA",
        "eir-runtime@eir-ata.iam.gserviceaccount.com",
    )
    delegated = impersonated_credentials.Credentials(
        source_credentials=source,
        target_principal=principal,
        target_scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    id_creds = impersonated_credentials.IDTokenCredentials(
        target_credentials=delegated,
        target_audience=audience,
        include_email=True,
    )
    id_creds.refresh(Request())
    token = getattr(id_creds, "token", None)
    if not token:
        raise RuntimeError("identity token unavailable")
    return str(token)


def _headers(token: str) -> dict[str, str]:
    # Cloud Run intercepts Authorization / X-Serverless-Authorization. Agent Identity
    # ID tokens are verified by eir-api; do not send them as Cloud Run IAM bearers.
    return {
        "X-Agent-Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _jwt_debug(token: str) -> dict[str, Any]:
    import base64
    import json

    parts = token.split(".")
    if len(parts) < 2:
        return {"jwt": False}
    padded = parts[1] + "=" * (-len(parts[1]) % 4)
    try:
        payload = json.loads(base64.urlsafe_b64decode(padded))
    except Exception:
        return {"jwt": False}
    return {
        key: payload.get(key)
        for key in ("iss", "aud", "sub", "email", "azp")
        if payload.get(key)
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
    token = _identity_token()
    with httpx.Client(timeout=_TIMEOUT) as client:
        response = client.request(
            method, url, headers=_headers(token), json=json, params=params
        )
        if response.is_error:
            body = (response.text or "")[:500]
            return {
                "error": f"HTTP {response.status_code}",
                "path": path,
                "detail": body,
                "token_claims": _jwt_debug(token),
            }
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
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and payload.get("error"):
        return payload
    return payload.get("items", []) if isinstance(payload, dict) else []


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
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and payload.get("error"):
        return payload
    return payload.get("items", []) if isinstance(payload, dict) else []


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
