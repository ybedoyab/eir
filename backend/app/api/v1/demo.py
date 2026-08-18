"""Deterministic hackathon demo bootstrap — synthetic data only."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from eir_shared.events import PatientResponded
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.deps import get_container
from app.integrations.enterprise.security_demo import DEMO_MALICIOUS_PROMPT
from app.services.demo_controls import (
    CONCERNING_MESSAGE,
    claim_demo_action,
    has_concerning_signal,
    require_synthetic_episode,
)
from app.services.follow_up_scheduler import FollowUpScheduler
from app.services.recovery_service import RecoveryService

router = APIRouter()

DEMO_PATIENT_ID = "patient-synthetic-001"
DEMO_CONCERNING_MESSAGE = CONCERNING_MESSAGE


class DemoBootstrapRequest(BaseModel):
    patient_id: str = Field(default=DEMO_PATIENT_ID)
    fast_forward: bool = False


def _scheduler() -> FollowUpScheduler:
    container = get_container()
    return FollowUpScheduler(
        container.episodes,
        idempotency=container.scheduler_idempotency,
    )


@router.post("/bootstrap")
async def bootstrap_demo(body: DemoBootstrapRequest) -> dict:
    """Create a fresh synthetic recovery episode for the hackathon story."""
    container = get_container()
    patient = container.patients.get(body.patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    due_at = datetime.now(UTC) + timedelta(days=7)
    service = RecoveryService(container.episodes)
    episode, started = service.create_episode(
        patient_id=body.patient_id,
        next_follow_up_at=due_at,
        assigned_agents=["outreach", "risk"],
    )
    scheduler = _scheduler()
    scheduler.ensure_schedule(episode)
    await container.event_bus.publish(started)
    follow_up = None
    if body.fast_forward:
        follow_up = scheduler.advance_episode(episode.id)
        if follow_up is not None:
            await container.event_bus.publish(follow_up)
    episode = container.episodes.get(episode.id) or episode
    return {
        "episode_id": episode.id,
        "patient_id": episode.patient_id,
        "patient_name": patient.name,
        "status": episode.status.value,
        "risk_level": episode.risk_level.value,
        "next_follow_up_at": episode.next_follow_up_at,
        "fast_forwarded": follow_up is not None,
        "monitoring": True,
        "story": [
            "Consultation finished → RecoveryEpisodeStarted",
            "Next autonomous follow-up scheduled",
            "POST /api/v1/demo/advance-follow-up/{episode_id} uses FollowUpScheduler",
            "FollowUpDue published through EventBus → worker outreach_agent",
            "PatientResponded → risk_agent evaluates",
            f"POST /api/v1/security/demo/prompt-injection/{episode.id}",
            f"POST /api/v1/demo/concerning-signal/{episode.id}",
        ],
        "malicious_prompt": DEMO_MALICIOUS_PROMPT,
    }


@router.post("/advance-follow-up/{episode_id}")
async def advance_follow_up(episode_id: str) -> dict:
    """Demo time acceleration: make the follow-up due via FollowUpScheduler.

    Production uses Cloud Scheduler to call the same claim path. This endpoint
    never invokes outreach_agent and never bypasses EventBus/worker logic.
    """
    container = get_container()
    require_synthetic_episode(container.episodes, episode_id)
    events = container.episodes.list_events(episode_id)
    already_due = any(event.event_type == "FollowUpDue" for event in events)
    if already_due or not claim_demo_action(episode_id, "advance"):
        return {
            "advanced": False,
            "episode_id": episode_id,
            "event": None,
            "reason": "follow-up already claimed or episode is not schedulable",
        }
    event = _scheduler().advance_episode(episode_id)
    if event is None:
        return {
            "advanced": False,
            "episode_id": episode_id,
            "event": None,
            "reason": "follow-up already claimed or episode is not schedulable",
        }
    await container.event_bus.publish(event)
    return {
        "advanced": True,
        "episode_id": episode_id,
        "event": event.event_type,
    }


@router.post("/concerning-signal/{episode_id}")
async def concerning_signal(episode_id: str) -> dict:
    """Publish a synthetic high-pain patient response through the real event bus."""
    container = get_container()
    require_synthetic_episode(container.episodes, episode_id)
    events = container.episodes.list_events(episode_id)
    if has_concerning_signal(events) or not claim_demo_action(episode_id, "concerning"):
        raise HTTPException(
            status_code=409,
            detail="Concerning signal already submitted for this demo episode",
        )
    event = PatientResponded(
        episode_id=episode_id,
        channel="synthetic",
        payload={
            "message": DEMO_CONCERNING_MESSAGE,
            "pain_score": 8,
            "reported_issue": True,
        },
    )
    container.episodes.append_event(episode_id, event)
    await container.event_bus.publish(event)
    return {
        "published": event.event_type,
        "episode_id": episode_id,
        "expected": "risk_agent escalates; clinician review may open",
        "signal": {"pain_score": 8, "reported_issue": "swelling"},
    }
