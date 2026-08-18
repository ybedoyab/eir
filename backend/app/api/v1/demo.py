"""Deterministic hackathon demo bootstrap — synthetic data only."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.deps import get_container
from app.integrations.enterprise.security_demo import DEMO_MALICIOUS_PROMPT
from app.services.follow_up_scheduler import FollowUpScheduler
from app.services.recovery_service import RecoveryService

router = APIRouter()

DEMO_PATIENT_ID = "patient-synthetic-001"
DEMO_CONCERNING_MESSAGE = "Pain is an 8 and I noticed swelling near the incision."


class DemoBootstrapRequest(BaseModel):
    patient_id: str = Field(default=DEMO_PATIENT_ID)
    fast_forward: bool = True


@router.post("/bootstrap")
async def bootstrap_demo(body: DemoBootstrapRequest) -> dict:
    """Create a fresh synthetic recovery episode for the hackathon story."""
    container = get_container()
    if container.patients.get(body.patient_id) is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    due_at = datetime.now(UTC) - timedelta(minutes=5)
    service = RecoveryService(container.episodes)
    episode, started = service.create_episode(
        patient_id=body.patient_id,
        next_follow_up_at=due_at,
        assigned_agents=["outreach", "risk"],
    )
    FollowUpScheduler(
        container.episodes,
        idempotency=container.scheduler_idempotency,
    ).ensure_schedule(episode)
    await container.event_bus.publish(started)
    follow_up = None
    if body.fast_forward:
        follow_up = service.trigger_follow_up(episode.id)
        if follow_up is not None:
            await container.event_bus.publish(follow_up)
    return {
        "episode_id": episode.id,
        "patient_id": episode.patient_id,
        "next_follow_up_at": episode.next_follow_up_at,
        "fast_forwarded": follow_up is not None,
        "story": [
            "Consultation finished → RecoveryEpisodeStarted",
            "Next autonomous follow-up scheduled",
            "FollowUpDue published (demo fast-forward or Cloud Scheduler)",
            "outreach_agent reads context and calls conduct_outreach",
            "PatientResponded → risk_agent evaluates",
            f"POST /api/v1/security/demo/prompt-injection/{episode.id}",
            f"POST /api/v1/demo/concerning-signal/{episode.id}",
        ],
        "malicious_prompt": DEMO_MALICIOUS_PROMPT,
    }


@router.post("/concerning-signal/{episode_id}")
async def concerning_signal(episode_id: str) -> dict:
    """Publish a synthetic high-pain patient response through the real event bus."""
    container = get_container()
    if container.episodes.get(episode_id) is None:
        raise HTTPException(status_code=404, detail="Recovery episode not found")
    from eir_shared.events import PatientResponded

    event = PatientResponded(
        episode_id=episode_id,
        channel="synthetic",
        payload={
            "message": DEMO_CONCERNING_MESSAGE,
            "pain_score": 8,
            "reported_issue": True,
        },
    )
    await container.event_bus.publish(event)
    return {
        "published": event.event_type,
        "episode_id": episode_id,
        "expected": "risk_agent escalates; clinician review may open",
    }
