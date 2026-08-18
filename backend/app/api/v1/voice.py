"""Authenticated Voximplant → EIR voice callbacks."""

from __future__ import annotations

import hmac

from fastapi import APIRouter, Header, HTTPException

from app.core.config import settings
from app.core.deps import get_container
from app.services.voice_callback import VoiceCallbackRequest, VoiceCallbackService

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
