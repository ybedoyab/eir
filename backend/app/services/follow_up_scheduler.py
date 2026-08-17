"""Proactive follow-up scheduling (Cloud Scheduler entry point)."""

from __future__ import annotations

import threading
from datetime import UTC, datetime, timedelta

from eir_shared.events import FollowUpDue

from app.domain.recovery.models import EpisodeStatus, RecoveryEpisode
from app.repositories.recovery_repository import RecoveryEpisodeRepository

_SCHEDULABLE = frozenset({EpisodeStatus.ACTIVE, EpisodeStatus.WAITING_FOR_NEXT_FOLLOWUP})


class FollowUpScheduler:
    def __init__(
        self,
        episodes: RecoveryEpisodeRepository,
        *,
        default_interval_days: int = 7,
    ) -> None:
        self._episodes = episodes
        self._default_interval = default_interval_days
        self._lock = threading.Lock()
        self._processed_keys: set[str] = set()

    def process_due(
        self,
        *,
        now: datetime | None = None,
        idempotency_key: str | None = None,
    ) -> list[FollowUpDue]:
        now = now or datetime.now(UTC)
        idempotency_key = idempotency_key or now.isoformat()
        with self._lock:
            if idempotency_key in self._processed_keys:
                return []
            due_events: list[FollowUpDue] = []
            for episode in self._episodes.list():
                if episode.status not in _SCHEDULABLE:
                    continue
                if episode.next_follow_up_at is None:
                    continue
                if self._has_unprocessed_follow_up(episode.id):
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
            self._processed_keys.add(idempotency_key)
            return due_events

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
