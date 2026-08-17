from datetime import datetime
from uuid import uuid4

from eir_shared.events import DomainEvent, FollowUpDue, RecoveryEpisodeStarted, parse_event

from app.domain.recovery.models import RecoveryEpisode
from app.repositories.recovery_repository import RecoveryEpisodeRepository


class RecoveryService:
    def __init__(self, episodes: RecoveryEpisodeRepository) -> None:
        self._episodes = episodes

    def list_episodes(self) -> list[RecoveryEpisode]:
        return self._episodes.list()

    def get_episode(self, episode_id: str) -> RecoveryEpisode | None:
        return self._episodes.get(episode_id)

    def create_episode(
        self,
        patient_id: str,
        next_follow_up_at: datetime | None = None,
        assigned_agents: list[str] | None = None,
    ) -> tuple[RecoveryEpisode, RecoveryEpisodeStarted]:
        episode = RecoveryEpisode(
            id=str(uuid4()),
            patient_id=patient_id,
            next_follow_up_at=next_follow_up_at,
            assigned_agents=assigned_agents or [],
        )
        self._episodes.save(episode)
        event = RecoveryEpisodeStarted(episode_id=episode.id, patient_id=patient_id)
        self._episodes.append_event(episode.id, event)
        return episode, event

    def list_events(self, episode_id: str) -> list[DomainEvent]:
        return self._episodes.list_events(episode_id)

    def trigger_follow_up(self, episode_id: str) -> FollowUpDue | None:
        if self._episodes.get(episode_id) is None:
            return None
        event = FollowUpDue(episode_id=episode_id)
        self._episodes.append_event(episode_id, event)
        return event

    def append_event(
        self,
        episode_id: str,
        event_type: str,
        payload: dict | None = None,
    ) -> DomainEvent | None:
        if self._episodes.get(episode_id) is None:
            return None
        event = parse_event(event_type, episode_id=episode_id, payload=payload or {})
        self._episodes.append_event(episode_id, event)
        return event
