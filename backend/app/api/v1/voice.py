"""Authenticated Voximplant → EIR voice callbacks and browser voice sessions."""

from __future__ import annotations

import hmac
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException

from app.api.deps.auth import require_patient_access
from app.core.config import settings
from app.core.deps import get_container
from app.services.medications import medications_for_patient
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


@router.get("/context")
def voice_call_context(
    episode_id: str,
    voice_token: str | None = Header(default=None, alias="X-EIR-Voice-Token"),
) -> dict:
    """Medication names for the live prompt. Fetched at call start, not packed into custom data."""
    if not _authorized(voice_token):
        raise HTTPException(status_code=401, detail="Invalid voice callback token")
    container = get_container()
    episode = container.episodes.get(episode_id)
    if episode is None:
        raise HTTPException(status_code=404, detail="Recovery episode not found")
    items = container.supply.list_items()
    medications = medications_for_patient(
        container.fhir.get_medications(episode.patient_id),
        items,
    )
    return {
        "episode_id": episode.id,
        "patient_id": episode.patient_id,
        "medications": [
            {
                "sku": item.sku,
                "name": item.name,
                "short_code": (item.sku.split("-")[1] if "-" in item.sku else item.sku)[:8],
                "critical": item.critical,
            }
            for item in medications
            if item.sku
        ],
    }


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
