"""Proactive follow-up scheduling (Cloud Scheduler entry point)."""

from __future__ import annotations

import threading
from datetime import UTC, datetime

from eir_shared.events import FollowUpDue

from app.domain.recovery.models import RecoveryEpisode
from app.repositories.recovery_repository import RecoveryEpisodeRepository
from app.repositories.scheduler_idempotency import (
    InMemorySchedulerIdempotencyStore,
    SchedulerIdempotencyStore,
)


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
                claimed = self._episodes.claim_due_follow_up(
                    episode.id,
                    now=now,
                    interval_days=self._default_interval,
                )
                if claimed is not None:
                    due_events.append(claimed)
            return due_events

    def advance_episode(
        self,
        episode_id: str,
        *,
        now: datetime | None = None,
    ) -> FollowUpDue | None:
        """Demo clock control: make one episode due, then claim via the production path.

        Uses the same ``claim_due_follow_up`` as Cloud Scheduler. Does not invoke
        outreach agents or bypass EventBus/worker handling.
        """
        now = now or datetime.now(UTC)
        episode = self._episodes.get(episode_id)
        if episode is None:
            return None
        if episode.next_follow_up_at is not None:
            follow_up_at = episode.next_follow_up_at
            if follow_up_at.tzinfo is None:
                follow_up_at = follow_up_at.replace(tzinfo=UTC)
            if follow_up_at > now:
                episode.next_follow_up_at = now
                self._episodes.save(episode)
        return self._episodes.claim_due_follow_up(
            episode_id,
            now=now,
            interval_days=self._default_interval,
        )

    def ensure_schedule(self, episode: RecoveryEpisode) -> RecoveryEpisode:
        if episode.next_follow_up_at is None:
            from datetime import timedelta

            episode.next_follow_up_at = datetime.now(UTC) + timedelta(minutes=1)
            self._episodes.save(episode)
        return episode
