"""Google identity tokens for managed Agent Runtime tools. No demo passwords."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends, Header, HTTPException, Request

from app.core.config import settings
from app.core.deps import get_container

SYNTHETIC_USERS = frozenset({"patient-synthetic-001"})


def normalize_principal(raw: str) -> str:
    value = raw.strip()
    if not value:
        return value
    if value.startswith(("principal://", "user:", "serviceAccount:")):
        return value
    if value.startswith("agents.global."):
        return f"principal://{value}"
    return value


def principals_from_claims(claims: dict[str, Any]) -> set[str]:
    found: set[str] = set()
    for key in ("email", "sub"):
        value = claims.get(key)
        if value:
            found.add(normalize_principal(str(value)))
    nested = claims.get("google")
    if isinstance(nested, dict):
        subject = nested.get("subject")
        if subject:
            found.add(normalize_principal(str(subject)))
    return {item for item in found if item}


def _token_from_header(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Agent identity token required")
    return authorization.split(" ", 1)[1].strip()


def _verify_google_identity(token: str, audience: str) -> dict[str, Any]:
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token

    request = google_requests.Request()
    try:
        return id_token.verify_oauth2_token(token, request, audience=audience)
    except ValueError:
        return id_token.verify_oauth2_token(token, request)


def require_agent_runtime_principal(
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> dict[str, Any]:
    container = get_container()
    if getattr(container, "testing", False):
        return {"principal": "test-agent-runtime", "role": "agent_runtime"}

    token = _token_from_header(authorization)
    audience = settings.agent_runtime_audience.strip() or str(request.base_url).rstrip("/")
    try:
        claims = _verify_google_identity(token, audience)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid agent identity token") from exc

    candidates = principals_from_claims(claims)
    allowed = {
        normalize_principal(item)
        for item in container.platform_verification.allowed_principals()
    }
    matched = next((item for item in candidates if item in allowed), "")
    if not allowed or not matched:
        raise HTTPException(status_code=403, detail="Agent identity not authorized")
    container.platform_verification.write({"last_authenticated_principal": matched})
    return {"principal": matched, "role": "agent_runtime", "claims": claims}


AgentRuntimeAuth = Annotated[dict[str, Any], Depends(require_agent_runtime_principal)]


def bound_synthetic_user(synthetic_user_id: str) -> str:
    if synthetic_user_id not in SYNTHETIC_USERS:
        raise HTTPException(status_code=403, detail="synthetic user not permitted")
    return synthetic_user_id
