"""Authenticated Voximplant → EIR voice callbacks and browser voice sessions."""

from __future__ import annotations

import hmac
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException

from app.api.deps.auth import require_patient_access
from app.core.config import settings
from app.core.deps import get_container
from app.services.voice_callback import VoiceCallbackRequest, VoiceCallbackService
from app.services.voice_web_session import (
    VoiceWebSessionService,
    WebSessionRequest,
    web_voice_config,
)

router = APIRouter()


def _authorized(token: str | None) -> bool:
    expected = settings.voximplant_callback_token
    if not expected or not token:
        return False
    return hmac.compare_digest(token, expected)


@router.post("/voximplant/callback")
async def voximplant_callback(
    body: VoiceCallbackRequest,
    voice_token: str | None = Header(default=None, alias="X-EIR-Voice-Token"),
) -> dict:
    if not _authorized(voice_token):
        raise HTTPException(status_code=401, detail="Invalid voice callback token")
    return await VoiceCallbackService(get_container()).handle(body)


@router.get("/web-session")
def web_session_config() -> dict:
    """Non-secret client config, so the browser knows where to dial."""
    return web_voice_config()


@router.post("/web-session")
def start_web_session(
    body: WebSessionRequest,
    claims: Annotated[dict[str, Any], Depends(require_patient_access)],
) -> dict:
    """Sign a Voximplant one-time login key for the patient's own episode."""
    return VoiceWebSessionService(get_container()).authorize(body, claims)
