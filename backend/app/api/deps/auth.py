"""Request-scoped demo authorization."""

from __future__ import annotations

from typing import Annotated, Any

from eir_shared.auth import DemoRole
from fastapi import Depends, Header, HTTPException

from app.core.deps import get_container


def _claims_from_header(
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> dict[str, Any]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")
    token = authorization.split(" ", 1)[1].strip()
    claims = get_container().identity.verify_token(token)
    if claims is None:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return claims


def require_role(*roles: DemoRole):
    allowed = {role.value for role in roles}

    def dependency(
        claims: Annotated[dict[str, Any], Depends(_claims_from_header)],
    ) -> dict[str, Any]:
        if claims.get("role") not in allowed:
            raise HTTPException(status_code=403, detail="Insufficient role")
        return claims

    return dependency


def require_patient_access(
    claims: Annotated[dict[str, Any], Depends(_claims_from_header)],
) -> dict[str, Any]:
    if claims.get("role") != DemoRole.PATIENT.value:
        raise HTTPException(status_code=403, detail="Patient access required")
    if not claims.get("patient_id"):
        raise HTTPException(status_code=403, detail="Patient identity missing")
    return claims


def optional_claims(
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> dict[str, Any] | None:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    token = authorization.split(" ", 1)[1].strip()
    return get_container().identity.verify_token(token)
