"""Hackathon demo identity. Replace with a real IdP in production."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any, Protocol

from eir_shared.auth import ROLE_PERMISSIONS, DemoRole


@dataclass(frozen=True)
class DemoUser:
    username: str
    display_name: str
    role: DemoRole
    patient_id: str | None = None


DEMO_USERS: dict[str, DemoUser] = {
    "alex": DemoUser(
        username="alex",
        display_name="Alex Rivera",
        role=DemoRole.PATIENT,
        patient_id="patient-synthetic-001",
    ),
    "jordan": DemoUser(
        username="jordan",
        display_name="Jordan Lee",
        role=DemoRole.PATIENT,
        patient_id="patient-synthetic-002",
    ),
    "clinician": DemoUser(
        username="clinician",
        display_name="Dr. Maya Chen",
        role=DemoRole.CLINICIAN,
    ),
    "admin": DemoUser(
        username="admin",
        display_name="Operations Admin",
        role=DemoRole.OPERATIONS_ADMIN,
    ),
}


class IdentityProvider(Protocol):
    def issue_token(self, user: DemoUser) -> str: ...

    def verify_token(self, token: str) -> dict[str, Any] | None: ...


class DemoIdentityProvider:
    def __init__(self, secret: str, *, ttl_seconds: int = 86_400) -> None:
        if not secret:
            raise ValueError("session secret is required")
        self._secret = secret.encode("utf-8")
        self._ttl_seconds = ttl_seconds

    def issue_token(self, user: DemoUser) -> str:
        payload = {
            "sub": user.username,
            "name": user.display_name,
            "role": user.role.value,
            "patient_id": user.patient_id,
            "permissions": sorted(ROLE_PERMISSIONS[user.role]),
            "exp": int(time.time()) + self._ttl_seconds,
        }
        return self._sign(payload)

    def verify_token(self, token: str) -> dict[str, Any] | None:
        try:
            payload_b64, signature = token.rsplit(".", 1)
            expected = hmac.new(
                self._secret,
                payload_b64.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
            if not hmac.compare_digest(signature, expected):
                return None
            payload = json.loads(base64.urlsafe_b64decode(payload_b64.encode("utf-8")).decode())
            if int(payload.get("exp", 0)) < int(time.time()):
                return None
            return payload
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
            return None

    def _sign(self, payload: dict[str, Any]) -> str:
        payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8")
        signature = hmac.new(
            self._secret,
            payload_b64.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return f"{payload_b64}.{signature}"


def authenticate_demo_user(username: str, password: str) -> DemoUser | None:
    user = DEMO_USERS.get(username.strip().lower())
    if user is None:
        return None
    expected = f"demo-{username.strip().lower()}"
    if password != expected:
        return None
    return user
