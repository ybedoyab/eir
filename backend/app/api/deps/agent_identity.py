"""Google identity tokens for managed Agent Runtime tools. No demo passwords."""

from __future__ import annotations

import json
from typing import Annotated, Any

from fastapi import Depends, Header, HTTPException, Request

from app.core.config import settings
from app.core.deps import get_container

SYNTHETIC_USERS = frozenset({"patient-synthetic-001"})
PROJECT_NUMBER = "658898892127"
AGENT_IDENTITY_ISSUER = (
    "https://sts.googleapis.com/v1/projects/"
    f"{PROJECT_NUMBER}/locations/global/workloadIdentityPools/"
    f"agents.global.proj-{PROJECT_NUMBER}.system.id.goog"
)


def normalize_principal(raw: str) -> str:
    value = raw.strip()
    if not value:
        return value
    if value.startswith("spiffe://"):
        value = "principal://" + value[len("spiffe://") :]
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


def _jwt_unverified_iss(token: str) -> str:
    import base64

    parts = token.split(".")
    if len(parts) < 2:
        return ""
    padded = parts[1] + "=" * (-len(parts[1]) % 4)
    payload = json.loads(base64.urlsafe_b64decode(padded))
    return str(payload.get("iss") or "")


def _jwk_to_pem(jwk: dict[str, Any]) -> str:
    import base64

    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    def _int(value: str) -> int:
        padded = value + "=" * (-len(value) % 4)
        return int.from_bytes(base64.urlsafe_b64decode(padded), "big")

    public = rsa.RSAPublicNumbers(_int(str(jwk["e"])), _int(str(jwk["n"]))).public_key()
    return public.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")


def _verify_agent_identity_sts(token: str, audience: str) -> dict[str, Any]:
    import urllib.request

    from google.auth import jwt as google_jwt

    issuer = _jwt_unverified_iss(token)
    if issuer != AGENT_IDENTITY_ISSUER:
        raise ValueError("unexpected agent identity issuer")
    certs_url = f"{issuer}/openid/jwks"
    with urllib.request.urlopen(certs_url, timeout=10) as response:
        jwks = json.loads(response.read().decode("utf-8"))
    certs = {
        str(key["kid"]): _jwk_to_pem(key)
        for key in jwks.get("keys", [])
        if key.get("kid") and key.get("kty") == "RSA"
    }
    if not certs:
        raise ValueError("agent identity JWKS unavailable")
    claims = dict(google_jwt.decode(token, certs=certs, audience=None))
    if claims.get("iss") != AGENT_IDENTITY_ISSUER:
        raise ValueError("issuer mismatch")
    aud = claims.get("aud")
    audiences = [str(item) for item in aud] if isinstance(aud, list) else [str(aud)]
    if audience not in audiences:
        raise ValueError("audience mismatch")
    return claims


def _verify_google_identity(token: str, audience: str) -> dict[str, Any]:
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token

    if _jwt_unverified_iss(token) == AGENT_IDENTITY_ISSUER:
        return _verify_agent_identity_sts(token, audience)
    request = google_requests.Request()
    try:
        return id_token.verify_oauth2_token(token, request, audience=audience)
    except ValueError:
        return id_token.verify_oauth2_token(token, request)


def require_agent_runtime_principal(
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization"),
    agent_authorization: str | None = Header(default=None, alias="X-Agent-Authorization"),
) -> dict[str, Any]:
    container = get_container()
    if getattr(container, "testing", False):
        return {"principal": "test-agent-runtime", "role": "agent_runtime"}

    token = _token_from_header(authorization or agent_authorization)
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
