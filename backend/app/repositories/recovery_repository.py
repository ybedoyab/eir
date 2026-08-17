"""Recovery Episode persistence.

Episodes are long-running workflows. This store does not assume a request
completes the whole recovery path.

TODO: FirestoreRecoveryEpisodeRepository / CloudSqlRecoveryEpisodeRepository.
"""

from __future__ import annotations

from typing import Protocol

from eir_shared.events import DomainEvent

from app.domain.recovery.models import RecoveryEpisode


class RecoveryEpisodeRepository(Protocol):
    def get(self, episode_id: str) -> RecoveryEpisode | None: ...

    def list(self) -> list[RecoveryEpisode]: ...

    def save(self, episode: RecoveryEpisode) -> RecoveryEpisode: ...

    def append_event(self, episode_id: str, event: DomainEvent) -> DomainEvent: ...

    def list_events(self, episode_id: str) -> list[DomainEvent]: ...


class InMemoryRecoveryEpisodeRepository:
    def __init__(self) -> None:
        self._items: dict[str, RecoveryEpisode] = {}
        self._events: dict[str, list[DomainEvent]] = {}

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
