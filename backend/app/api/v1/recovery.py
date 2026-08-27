import asyncio
import logging
from datetime import datetime

from eir_shared.events import RecoveryVideoRequested
from fastapi import APIRouter, Header, HTTPException, Response
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.deps import get_container
from app.domain.recovery.models import RecoveryEpisode
from app.services.follow_up_scheduler import FollowUpScheduler
from app.services.recovery_service import RecoveryService

router = APIRouter()
logger = logging.getLogger("eir.recovery_api")


class CreateRecoveryRequest(BaseModel):
    patient_id: str
    next_follow_up_at: datetime | None = None
    assigned_agents: list[str] = Field(default_factory=list)


class AppendEventRequest(BaseModel):
    event_type: str
    payload: dict = Field(default_factory=dict)


def _service() -> RecoveryService:
    return RecoveryService(get_container().episodes)


@router.post("", response_model=RecoveryEpisode, status_code=201)
async def create_recovery(body: CreateRecoveryRequest) -> RecoveryEpisode:
    container = get_container()
    if container.patients.get(body.patient_id) is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    episode, event = _service().create_episode(
        patient_id=body.patient_id,
        next_follow_up_at=body.next_follow_up_at,
        assigned_agents=body.assigned_agents,
    )
    FollowUpScheduler(
        container.episodes,
        idempotency=container.scheduler_idempotency,
    ).ensure_schedule(episode)
    # Publish and return. Do not run the multi-day workflow in this request.
    await container.event_bus.publish(event)
    # Kick off the personalized recovery video as a background task, not awaited: Veo
    # generation can take tens of seconds, and episode creation must stay fast (HTTP
    # handlers publish and return; they never run a whole workflow in-request). A no-op
    # when RECOVERY_VIDEO_ENABLED is false — the fallback client just reports "unavailable".
    asyncio.create_task(_request_recovery_video(episode.id))
    return episode


async def _request_recovery_video(episode_id: str) -> None:
    try:
        await get_container().event_bus.publish(RecoveryVideoRequested(episode_id=episode_id))
    except Exception:
        logger.exception("Recovery video generation failed for episode %s", episode_id)


@router.get("", response_model=list[RecoveryEpisode])
def list_recovery() -> list[RecoveryEpisode]:
    return _service().list_episodes()


@router.get("/{episode_id}", response_model=RecoveryEpisode)
def get_recovery(episode_id: str) -> RecoveryEpisode:
    episode = _service().get_episode(episode_id)
    if episode is None:
        raise HTTPException(status_code=404, detail="Recovery episode not found")
    return episode


@router.get("/{episode_id}/events")
def list_recovery_events(episode_id: str) -> list[dict]:
    if _service().get_episode(episode_id) is None:
        raise HTTPException(status_code=404, detail="Recovery episode not found")
    return [event.model_dump(mode="json") for event in _service().list_events(episode_id)]


@router.post("/{episode_id}/follow-up")
async def trigger_follow_up(episode_id: str) -> dict:
    container = get_container()
    event = _service().trigger_follow_up(episode_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Recovery episode not found")
    await container.event_bus.publish(event)
    episode = _service().get_episode(episode_id)
    return {
        "event": event.model_dump(mode="json"),
        "episode": episode.model_dump(mode="json") if episode else None,
    }


@router.post("/process-due-follow-ups")
async def process_due_follow_ups(
    scheduler_token: str | None = Header(default=None, alias="X-Scheduler-Token"),
    idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
) -> dict:
    if settings.scheduler_secret and scheduler_token != settings.scheduler_secret:
        raise HTTPException(status_code=401, detail="Invalid scheduler token")
    container = get_container()
    scheduler = FollowUpScheduler(
        container.episodes,
        idempotency=container.scheduler_idempotency,
    )
    events = scheduler.process_due(idempotency_key=idempotency_key)
    for event in events:
        await container.event_bus.publish(event)
    return {
        "processed": len(events),
        "episodes": [event.episode_id for event in events],
        "idempotency_key": idempotency_key or "generated",
    }


@router.post("/{episode_id}/events")
async def append_recovery_event(episode_id: str, body: AppendEventRequest) -> dict:
    container = get_container()
    event = _service().append_event(episode_id, body.event_type, body.payload)
    if event is None:
        raise HTTPException(status_code=404, detail="Recovery episode not found")
    await container.event_bus.publish(event)
    return event.model_dump(mode="json")


@router.get("/{episode_id}/video/{filename}")
def get_recovery_video(episode_id: str, filename: str) -> Response:
    """Serves a generated recovery clip from private storage (GCS or local disk).

    Never a public/gs:// URL handed to the browser directly — the bucket stays private and
    every read goes through this route.
    """
    container = get_container()
    data = container.video_client.read(episode_id=episode_id, filename=filename)
    if data is None:
        raise HTTPException(status_code=404, detail="Recovery video not found")
    return Response(content=data, media_type="video/mp4")
