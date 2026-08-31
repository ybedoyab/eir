"""Guards for judge-demo controls. Synthetic episodes only."""

from __future__ import annotations

import threading

from eir_shared.events import DomainEvent
from fastapi import HTTPException

from app.domain.recovery.models import RecoveryEpisode
from app.integrations.enterprise.security_demo import DEMO_MALICIOUS_PROMPT
from app.repositories.recovery_repository import RecoveryEpisodeRepository

SYNTHETIC_PATIENT_PREFIX = "patient-synthetic-"
SYNTHETIC_SKU_PREFIX = "MED-"
CONCERNING_MESSAGE = "Pain is an 8 and I noticed swelling near the incision."
ADHERENCE_VALUES = frozenset({"yes", "no", "unknown"})

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


def require_demo_sku(sku: str) -> str:
    """Demo controls only touch the synthetic pharmacy catalog."""
    if not sku.startswith(SYNTHETIC_SKU_PREFIX):
        raise HTTPException(
            status_code=403,
            detail="Demo controls only operate on synthetic inventory",
        )
    return sku


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


def has_recovery_checkin(events: list[DomainEvent]) -> bool:
    """A structured check-in already reached the episode, mock or spoken."""
    return any(event.event_type == "PatientResponded" for event in events)


def mock_checkin_payload(
    *,
    pain_score: int | None,
    reported_issue: bool,
    issue_summary: str,
    symptoms_worsening: bool,
    medication_adherence: str,
    medications: list[dict[str, object]],
    patient_requests_clinician: bool,
) -> dict[str, object]:
    """Structured stand-in for a spoken check-in.

    Same field names the Voximplant callback writes, so the risk agent reads one
    shape either way -- but `synthetic` stays True, which is what marks the
    answers as typed rather than spoken everywhere downstream.
    """
    pain = None if pain_score is None else max(0, min(10, int(pain_score)))
    adherence = (
        medication_adherence if medication_adherence in ADHERENCE_VALUES else "unknown"
    )
    clean_medications: list[dict[str, object]] = []
    for item in medications:
        sku = str(item.get("sku") or "").strip()[:24]
        if sku:
            clean_medications.append({"sku": sku, "taken": bool(item.get("taken", True))})
    if any(entry["taken"] is False for entry in clean_medications):
        adherence = "no"
    summary = " ".join(str(issue_summary).split())[:240]
    spoken = f"Pain is a {pain if pain is not None else 'unspecified'}"
    if reported_issue and summary:
        spoken = f"{spoken} and I noticed {summary}."
    else:
        spoken = f"{spoken} and nothing new to report."
    return {
        "channel": "voice",
        "provider": "demo-mock",
        "transport": "mock",
        "synthetic": True,
        "message": spoken,
        "pain_score": pain,
        "reported_issue": bool(reported_issue),
        "issue_summary": summary,
        "symptoms_worsening": bool(symptoms_worsening),
        "medication_adherence": adherence,
        "medications": clean_medications,
        "patient_requests_clinician": bool(patient_requests_clinician),
    }
