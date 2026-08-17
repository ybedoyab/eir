"""JSON file persistence for local long-running episodes.

TODO: FirestoreRecoveryEpisodeRepository / CloudSqlRecoveryEpisodeRepository.
"""

from __future__ import annotations

import json
from pathlib import Path

from eir_shared.events import DomainEvent, parse_event
from eir_shared.memory import InMemoryEpisodeStore

from app.domain.recovery.models import RecoveryEpisode
from app.repositories.recovery_repository import InMemoryRecoveryEpisodeRepository
from app.repositories.review_repository import HumanReview, InMemoryReviewRepository


class JsonEpisodeStore(InMemoryEpisodeStore):
    def __init__(self, path: Path) -> None:
        super().__init__()
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            self._items = {key: dict(value) for key, value in raw.items()}

    async def save(self, episode_id: str, state: dict) -> None:
        await super().save(episode_id, state)
        self.path.write_text(json.dumps(self._items, indent=2, default=str), encoding="utf-8")


class FileRecoveryEpisodeRepository(InMemoryRecoveryEpisodeRepository):
    def __init__(self, path: Path) -> None:
        super().__init__()
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        for item in raw.get("episodes", []):
            episode = RecoveryEpisode.model_validate(item)
            self._items[episode.id] = episode
        for episode_id, events in raw.get("events", {}).items():
            loaded: list[DomainEvent] = []
            for event in events:
                event_copy = dict(event)
                event_type = event_copy.pop("event_type", "DomainEvent")
                loaded.append(parse_event(event_type, **event_copy))
            self._events[episode_id] = loaded

    def _flush(self) -> None:
        payload = {
            "episodes": [item.model_dump(mode="json") for item in self._items.values()],
            "events": {
                episode_id: [event.model_dump(mode="json") for event in events]
                for episode_id, events in self._events.items()
            },
        }
        self.path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    def save(self, episode: RecoveryEpisode) -> RecoveryEpisode:
        result = super().save(episode)
        self._flush()
        return result

    def append_event(self, episode_id: str, event: DomainEvent) -> DomainEvent:
        result = super().append_event(episode_id, event)
        self._flush()
        return result


class FileReviewRepository(InMemoryReviewRepository):
    def __init__(self, path: Path) -> None:
        super().__init__()
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            for item in raw:
                review = HumanReview.model_validate(item)
                self._items[review.id] = review

    def _flush(self) -> None:
        payload = [item.model_dump(mode="json") for item in self._items.values()]
        self.path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    def save(self, review: HumanReview) -> HumanReview:
        result = super().save(review)
        self._flush()
        return result
