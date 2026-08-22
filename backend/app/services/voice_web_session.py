"""Browser-dialled recovery check-in.

The patient's browser dials the Voximplant application over WebRTC instead of
EIR placing a PSTN call. Two properties matter here:

1. The shared Voximplant user password never reaches the browser. The client
   asks Voximplant for a one-time key, we sign it server-side, and it logs in
   with the signature. A leaked signature is worthless once used.
2. The browser is told which episode it may dial for. Custom data is
   attacker-controllable, so the scenario forces the WebRTC transport itself and
   the callback re-validates the episode -- this service is the authorization
   point, not the trust anchor.
"""

from __future__ import annotations

import hashlib
import secrets
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel

from app.core.config import settings
from app.integrations.voice.voximplant_custom import encode_script_custom_data
from app.services.demo_controls import is_synthetic_patient


class WebSessionRequest(BaseModel):
    episode_id: str
    # Only needed for the login step. An already-registered client re-authorizes
    # for a second check-in and just needs fresh custom data.
    one_time_key: str = ""


def web_voice_domain() -> str:
    """The Voximplant SIP domain: <application>.<account>.voximplant.com."""
    account = settings.voximplant_account_name.strip()
    application = settings.voximplant_application_name.strip()
    if not account or not application:
        return ""
    return f"{application}.{account}.voximplant.com"


def web_voice_login() -> str:
    domain = web_voice_domain()
    user = settings.voximplant_web_user.strip()
    if not domain or not user:
        return ""
    return f"{user}@{domain}"


def web_voice_enabled() -> bool:
    return bool(web_voice_login() and settings.voximplant_web_password.strip())


# The realm in the inner digest is the literal string "voximplant.com" -- NOT
# the application domain that appears in the login. They look interchangeable
# and are not: using the application domain produces a well-formed hash that
# Voximplant rejects with AuthResult code 401 (invalid password), which reads
# like a credential problem rather than a signing one.
# https://voximplant.com/docs/guides/sdk/authorization-onetimekey
VOX_AUTH_REALM = "voximplant.com"


def _one_time_hash(*, key: str, user: str, password: str) -> str:
    """Voximplant's onetimekey algorithm.

    MD5(key + "|" + MD5(user + ":voximplant.com:" + password)), where `user` is
    the bare login without the "@app.account.voximplant.com" suffix.

    MD5 is not our choice -- it is what the platform's auth scheme specifies.
    It authenticates a single short-lived login, not stored data.
    """
    inner = hashlib.md5(f"{user}:{VOX_AUTH_REALM}:{password}".encode()).hexdigest()
    return hashlib.md5(f"{key}|{inner}".encode()).hexdigest()


def web_voice_config() -> dict[str, Any]:
    """Non-secret client configuration. Safe to serve before authentication."""
    return {
        "enabled": web_voice_enabled(),
        "login": web_voice_login(),
        "number": settings.voximplant_web_number.strip(),
        "transport": "webrtc",
        "gemini_live_model": settings.gemini_live_model,
        "gemini_live_voice": settings.gemini_live_voice,
    }


class VoiceWebSessionService:
    def __init__(self, container: Any) -> None:
        self._container = container

    def authorize(self, body: WebSessionRequest, claims: dict[str, Any]) -> dict[str, Any]:
        if not web_voice_enabled():
            raise HTTPException(
                status_code=503,
                detail="Browser voice is not configured",
            )
        key = body.one_time_key.strip()
        if len(key) > 128:
            raise HTTPException(status_code=400, detail="Invalid one-time key")

        episode = self._container.episodes.get(body.episode_id)
        if episode is None:
            raise HTTPException(status_code=404, detail="Recovery episode not found")
        if not is_synthetic_patient(episode.patient_id):
            raise HTTPException(
                status_code=403,
                detail="Browser voice is restricted to synthetic episodes",
            )
        if claims.get("patient_id") != episode.patient_id:
            raise HTTPException(status_code=403, detail="Episode belongs to another patient")

        # Fresh per session: the callback de-duplicates on correlation_id, so a
        # stable id would make a patient's second check-in look like a replay.
        correlation_id = f"web-{secrets.token_hex(8)}"
        return {
            "login": web_voice_login(),
            "hash": _one_time_hash(
                key=key,
                user=settings.voximplant_web_user.strip(),
                password=settings.voximplant_web_password,
            )
            if key
            else "",
            "number": settings.voximplant_web_number.strip(),
            "correlation_id": correlation_id,
            # outbound=False: this payload becomes VoxEngine.customData() on the
            # inbound leg, and without the marker the scenario's Started handler
            # would read it as a PSTN dial request and terminate the session.
            "custom_data": encode_script_custom_data(
                episode_id=episode.id,
                correlation_id=correlation_id,
                display_name=str(claims.get("display_name") or "Alex"),
                outbound=False,
            ),
        }
