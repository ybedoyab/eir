from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.deps import get_container
from app.domain.recovery.models import RecoveryEpisode
from app.services.recovery_service import RecoveryService

router = APIRouter()


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
    # Publish and return. Do not run the multi-day workflow in this request.
    await container.event_bus.publish(event)
    return episode


@router.get("", response_model=list[RecoveryEpisode])
def list_recovery() -> list[RecoveryEpisode]:
    return _service().list_episodes()


@router.get("/{episode_id}", response_model=RecoveryEpisode)
def get_recovery(episode_id: str) -> RecoveryEpisode:
    episode = _service().get_episode(episode_id)
    if episode is None:
        raise HTTPException(status_code=404, detail="Recovery episode not found")
    return episode


@router.post("/{episode_id}/events")
async def append_recovery_event(episode_id: str, body: AppendEventRequest) -> dict:
    container = get_container()
    event = _service().append_event(episode_id, body.event_type, body.payload)
    if event is None:
        raise HTTPException(status_code=404, detail="Recovery episode not found")
    await container.event_bus.publish(event)
    return event.model_dump(mode="json")
