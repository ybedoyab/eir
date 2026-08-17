"""Proactive follow-up scheduling (Cloud Tasks / cron entry point)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from eir_shared.events import FollowUpDue

from app.domain.recovery.models import EpisodeStatus, RecoveryEpisode
from app.repositories.recovery_repository import RecoveryEpisodeRepository


class FollowUpScheduler:
    def __init__(
        self,
        episodes: RecoveryEpisodeRepository,
        *,
        default_interval_days: int = 7,
    ) -> None:
        self._episodes = episodes
        self._default_interval = default_interval_days

    def process_due(self, *, now: datetime | None = None) -> list[FollowUpDue]:
        now = now or datetime.now(UTC)
        due_events: list[FollowUpDue] = []
        for episode in self._episodes.list():
            if episode.status != EpisodeStatus.ACTIVE:
                continue
            if episode.next_follow_up_at is None:
                continue
            follow_up_at = episode.next_follow_up_at
            if follow_up_at.tzinfo is None:
                follow_up_at = follow_up_at.replace(tzinfo=UTC)
            if follow_up_at > now:
                continue
            event = FollowUpDue(episode_id=episode.id)
            self._episodes.append_event(episode.id, event)
            episode.next_follow_up_at = now + timedelta(days=self._default_interval)
            self._episodes.save(episode)
            due_events.append(event)
        return due_events

    def ensure_schedule(self, episode: RecoveryEpisode) -> RecoveryEpisode:
        if episode.next_follow_up_at is None:
            episode.next_follow_up_at = datetime.now(UTC) + timedelta(minutes=1)
            self._episodes.save(episode)
        return episode
