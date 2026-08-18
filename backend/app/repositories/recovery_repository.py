"""Recovery Episode persistence.

Episodes are long-running workflows. This store does not assume a request
completes the whole recovery path.

TODO: FirestoreRecoveryEpisodeRepository / CloudSqlRecoveryEpisodeRepository.
"""

from __future__ import annotations

import threading
from datetime import UTC, datetime, timedelta
from typing import Protocol

from eir_shared.events import DomainEvent, FollowUpDue

from app.domain.recovery.models import EpisodeStatus, RecoveryEpisode

_SCHEDULABLE = frozenset({EpisodeStatus.ACTIVE, EpisodeStatus.WAITING_FOR_NEXT_FOLLOWUP})


class RecoveryEpisodeRepository(Protocol):
    def get(self, episode_id: str) -> RecoveryEpisode | None: ...

    def list(self) -> list[RecoveryEpisode]: ...

    def save(self, episode: RecoveryEpisode) -> RecoveryEpisode: ...

    def append_event(self, episode_id: str, event: DomainEvent) -> DomainEvent: ...

    def list_events(self, episode_id: str) -> list[DomainEvent]: ...

    def claim_due_follow_up(
        self,
        episode_id: str,
        *,
        now: datetime,
        interval_days: int,
    ) -> FollowUpDue | None: ...


class InMemoryRecoveryEpisodeRepository:
    def __init__(self) -> None:
        self._items: dict[str, RecoveryEpisode] = {}
        self._events: dict[str, list[DomainEvent]] = {}
        self._lock = threading.Lock()

    def get(self, episode_id: str) -> RecoveryEpisode | None:
        return self._items.get(episode_id)

    def list(self) -> list[RecoveryEpisode]:
        return list(self._items.values())

    def save(self, episode: RecoveryEpisode) -> RecoveryEpisode:
        self._items[episode.id] = episode
        self._events.setdefault(episode.id, [])
        return episode

    def append_event(self, episode_id: str, event: DomainEvent) -> DomainEvent:
        self._events.setdefault(episode_id, []).append(event)
        return event

    def list_events(self, episode_id: str) -> list[DomainEvent]:
        return list(self._events.get(episode_id, []))

    def claim_due_follow_up(
        self,
        episode_id: str,
        *,
        now: datetime,
        interval_days: int,
    ) -> FollowUpDue | None:
        with self._lock:
            episode = self._items.get(episode_id)
            if episode is None:
                return None
            if episode.status not in _SCHEDULABLE:
                return None
            if episode.next_follow_up_at is None:
                return None
            events = self._events.get(episode_id, [])
            if events and events[-1].event_type == "FollowUpDue":
                return None
            follow_up_at = episode.next_follow_up_at
            if follow_up_at.tzinfo is None:
                follow_up_at = follow_up_at.replace(tzinfo=UTC)
            if follow_up_at > now:
                return None
            event = FollowUpDue(episode_id=episode_id)
            self._events.setdefault(episode_id, []).append(event)
            episode.next_follow_up_at = now + timedelta(days=interval_days)
            self._items[episode_id] = episode
            return event
