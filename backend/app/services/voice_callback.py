"""Voice callback processing. Publishes domain events; never invokes risk_agent."""

from __future__ import annotations

from typing import Any

from eir_shared.events import (
    PatientResponded,
    VoiceCallCompleted,
    VoiceCallConnected,
    VoiceCallFailed,
    VoiceCallStarted,
)
from fastapi import HTTPException
from pydantic import BaseModel

from app.core.config import settings
from app.services.demo_controls import is_synthetic_patient

VOICE_STATES = frozenset(
    {"CALL_STARTED", "CALL_CONNECTED", "CALL_COMPLETED", "CALL_FAILED", "NO_ANSWER"}
)
COMPLETED_STATES = frozenset({"CALL_COMPLETED"})
SYNTHETIC_PREFIX = "patient-synthetic-"


class VoiceCallbackRequest(BaseModel):
    episode_id: str
    correlation_id: str
    state: str
    call_id: str = ""
    provider: str = "voximplant"
    pain_score: int | None = None
    reported_issue: bool | None = None
    issue_summary: str = ""
    symptoms_worsening: bool | None = None
    medication_adherence: str = "unknown"
    patient_requests_clinician: bool | None = None
    call_outcome: str = ""
    failure_reason: str = ""


def _sanitize_summary(value: str) -> str:
    text = " ".join(value.split())
    return text[:240]


def _structured_payload(body: VoiceCallbackRequest) -> dict[str, Any]:
    pain = body.pain_score
    if pain is not None:
        pain = max(0, min(10, int(pain)))
    adherence = (
        body.medication_adherence
        if body.medication_adherence in {"yes", "no", "unknown"}
        else "unknown"
    )
    return {
        "channel": "voice",
        "provider": "voximplant",
        "synthetic": True,
        "correlation_id": body.correlation_id,
        "call_id": body.call_id,
        "pain_score": pain,
        "reported_issue": bool(body.reported_issue),
        "issue_summary": _sanitize_summary(body.issue_summary),
        "symptoms_worsening": bool(body.symptoms_worsening),
        "medication_adherence": adherence,
        "patient_requests_clinician": bool(body.patient_requests_clinician),
        "call_outcome": body.call_outcome or "completed",
        "gemini_live_model": settings.gemini_live_model,
    }


class VoiceCallbackService:
    def __init__(self, container: Any) -> None:
        self._container = container

    async def handle(self, body: VoiceCallbackRequest) -> dict[str, Any]:
        state = body.state.strip().upper()
        if state not in VOICE_STATES:
            raise HTTPException(status_code=400, detail="Unsupported voice callback state")
        episode = self._container.episodes.get(body.episode_id)
        if episode is None:
            raise HTTPException(status_code=404, detail="Recovery episode not found")
        if not is_synthetic_patient(episode.patient_id):
            raise HTTPException(
                status_code=403,
                detail="Voice callbacks are restricted to synthetic episodes",
            )
        if not episode.patient_id.startswith(SYNTHETIC_PREFIX):
            raise HTTPException(
                status_code=403,
                detail="Voice callbacks are restricted to synthetic episodes",
            )

        idempotency_key = f"{body.correlation_id}:{state}"
        claimed = self._container.voice_idempotency.claim_run(idempotency_key)
        if not claimed:
            return {
                "accepted": True,
                "duplicate": True,
                "state": state,
                "episode_id": body.episode_id,
            }

        voice_event = self._voice_event(body, state)
        self._container.episodes.append_event(episode.id, voice_event)
        await self._container.event_bus.publish(voice_event)

        published = [voice_event.event_type]
        if state in COMPLETED_STATES:
            responded = PatientResponded(
                episode_id=episode.id,
                channel="voice",
                payload=_structured_payload(body),
            )
            self._container.episodes.append_event(episode.id, responded)
            await self._container.event_bus.publish(responded)
            published.append(responded.event_type)

        return {
            "accepted": True,
            "duplicate": False,
            "state": state,
            "episode_id": episode.id,
            "published": published,
        }

    def _voice_event(self, body: VoiceCallbackRequest, state: str):
        payload = {
            "provider": "voximplant",
            "correlation_id": body.correlation_id,
            "call_id": body.call_id,
            "state": state,
            "gemini_live_model": settings.gemini_live_model,
        }
        if state == "CALL_STARTED":
            return VoiceCallStarted(episode_id=body.episode_id, payload=payload)
        if state == "CALL_CONNECTED":
            return VoiceCallConnected(episode_id=body.episode_id, payload=payload)
        if state == "CALL_COMPLETED":
            completed = dict(payload)
            completed["call_outcome"] = body.call_outcome or "completed"
            return VoiceCallCompleted(episode_id=body.episode_id, payload=completed)
        failed = dict(payload)
        failed["failure_reason"] = _sanitize_summary(body.failure_reason or state.lower())
        return VoiceCallFailed(episode_id=body.episode_id, payload=failed)
