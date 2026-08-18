"""Proactive follow-up scheduling (Cloud Scheduler entry point)."""

from __future__ import annotations

import threading
from datetime import UTC, datetime, timedelta

from eir_shared.events import FollowUpDue

from app.domain.recovery.models import EpisodeStatus, RecoveryEpisode
from app.repositories.recovery_repository import RecoveryEpisodeRepository
from app.repositories.scheduler_idempotency import (
    InMemorySchedulerIdempotencyStore,
    SchedulerIdempotencyStore,
)

_SCHEDULABLE = frozenset({EpisodeStatus.ACTIVE, EpisodeStatus.WAITING_FOR_NEXT_FOLLOWUP})


class FollowUpScheduler:
    def __init__(
        self,
        episodes: RecoveryEpisodeRepository,
        *,
        idempotency: SchedulerIdempotencyStore | None = None,
        default_interval_days: int = 7,
    ) -> None:
        self._episodes = episodes
        self._idempotency = idempotency or InMemorySchedulerIdempotencyStore()
        self._default_interval = default_interval_days
        self._lock = threading.Lock()

    def process_due(
        self,
        *,
        now: datetime | None = None,
        idempotency_key: str | None = None,
    ) -> list[FollowUpDue]:
        now = now or datetime.now(UTC)
        idempotency_key = idempotency_key or now.isoformat()
        with self._lock:
            if not self._idempotency.claim_run(idempotency_key):
                return []
            due_events: list[FollowUpDue] = []
            for episode in self._episodes.list():
                claimed = self._claim_episode_follow_up(episode, now=now)
                if claimed is not None:
                    due_events.append(claimed)
            return due_events

    def _claim_episode_follow_up(
        self,
        episode: RecoveryEpisode,
        *,
        now: datetime,
    ) -> FollowUpDue | None:
        if episode.status not in _SCHEDULABLE:
            return None
        if episode.next_follow_up_at is None:
            return None
        if self._has_unprocessed_follow_up(episode.id):
            return None
        follow_up_at = episode.next_follow_up_at
        if follow_up_at.tzinfo is None:
            follow_up_at = follow_up_at.replace(tzinfo=UTC)
        if follow_up_at > now:
            return None
        event = FollowUpDue(episode_id=episode.id)
        self._episodes.append_event(episode.id, event)
        episode.next_follow_up_at = now + timedelta(days=self._default_interval)
        self._episodes.save(episode)
        return event

    def _has_unprocessed_follow_up(self, episode_id: str) -> bool:
        events = self._episodes.list_events(episode_id)
        if not events:
            return False
        last = events[-1]
        return last.event_type == "FollowUpDue"

    def ensure_schedule(self, episode: RecoveryEpisode) -> RecoveryEpisode:
        if episode.next_follow_up_at is None:
            episode.next_follow_up_at = datetime.now(UTC) + timedelta(minutes=1)
            self._episodes.save(episode)
        return episode
