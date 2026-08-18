"""Guards for judge-demo controls. Synthetic episodes only."""

from __future__ import annotations

import threading

from eir_shared.events import DomainEvent
from fastapi import HTTPException

from app.domain.recovery.models import RecoveryEpisode
from app.integrations.enterprise.security_demo import DEMO_MALICIOUS_PROMPT
from app.repositories.recovery_repository import RecoveryEpisodeRepository

SYNTHETIC_PATIENT_PREFIX = "patient-synthetic-"
CONCERNING_MESSAGE = "Pain is an 8 and I noticed swelling near the incision."

_lock = threading.Lock()
_claimed: set[tuple[str, str]] = set()


def is_synthetic_patient(patient_id: str) -> bool:
    return patient_id.startswith(SYNTHETIC_PATIENT_PREFIX)


def require_synthetic_episode(
    episodes: RecoveryEpisodeRepository,
    episode_id: str,
) -> RecoveryEpisode:
    episode = episodes.get(episode_id)
    if episode is None:
        raise HTTPException(status_code=404, detail="Recovery episode not found")
    if not is_synthetic_patient(episode.patient_id):
        raise HTTPException(
            status_code=403,
            detail="Demo controls only operate on synthetic episodes",
        )
    return episode


def claim_demo_action(episode_id: str, action: str) -> bool:
    with _lock:
        key = (episode_id, action)
        if key in _claimed:
            return False
        _claimed.add(key)
        return True


def has_security_block(events: list[DomainEvent]) -> bool:
    return any(event.event_type == "ContentSecurityBlocked" for event in events)


def has_prompt_injection_attempt(events: list[DomainEvent]) -> bool:
    for event in events:
        if event.event_type != "PatientResponded":
            continue
        message = str((event.payload or {}).get("message") or "")
        if DEMO_MALICIOUS_PROMPT in message or "Ignore previous policy" in message:
            return True
    return has_security_block(events)


def has_concerning_signal(events: list[DomainEvent]) -> bool:
    for event in events:
        if event.event_type != "PatientResponded":
            continue
        payload = event.payload or {}
        if payload.get("reported_issue") is True and payload.get("pain_score") == 8:
            return True
        if str(payload.get("message") or "") == CONCERNING_MESSAGE:
            return True
    return False
