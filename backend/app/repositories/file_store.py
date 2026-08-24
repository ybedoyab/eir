"""JSON file persistence for local long-running episodes.

TODO: FirestoreRecoveryEpisodeRepository / CloudSqlRecoveryEpisodeRepository.
"""

from __future__ import annotations

import json
from pathlib import Path

from eir_shared.events import DomainEvent, parse_event_dict
from eir_shared.memory import InMemoryEpisodeStore
from eir_shared.observability import StructuredLogger, WorkflowTrace
from eir_shared.supply import InventoryItem, ReplenishmentCase, Supplier

from app.domain.recovery.models import RecoveryEpisode
from app.repositories.recovery_repository import InMemoryRecoveryEpisodeRepository
from app.repositories.review_repository import HumanReview, InMemoryReviewRepository
from app.repositories.supply_repository import InMemorySupplyRepository


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
                loaded.append(parse_event_dict(event))
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


class FileStructuredLogger(StructuredLogger):
    """Restart-safe traces. Cloud Trace remains a later adapter."""

    def __init__(self, name: str, path: Path) -> None:
        super().__init__(name)
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            self.records = [WorkflowTrace.model_validate(item) for item in raw]

    def emit(self, trace: WorkflowTrace) -> None:
        super().emit(trace)
        payload = [item.model_dump(mode="json") for item in self.records]
        self.path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


class FileSupplyRepository(InMemorySupplyRepository):
    """Restart-safe supply state for local runs and the Cloud Run file mode."""

    def __init__(self, path: Path) -> None:
        super().__init__()
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        for item in raw.get("items", []):
            record = InventoryItem.model_validate(item)
            self._items[record.sku] = record
        for item in raw.get("suppliers", []):
            supplier = Supplier.model_validate(item)
            self._suppliers[supplier.id] = supplier
        for item in raw.get("cases", []):
            case = ReplenishmentCase.model_validate(item)
            self._cases[case.id] = case
        for case_id, events in raw.get("events", {}).items():
            self._events[case_id] = [parse_event_dict(event) for event in events]

    def _flush(self) -> None:
        payload = {
            "items": [item.model_dump(mode="json") for item in self._items.values()],
            "suppliers": [item.model_dump(mode="json") for item in self._suppliers.values()],
            "cases": [item.model_dump(mode="json") for item in self._cases.values()],
            "events": {
                case_id: [event.model_dump(mode="json") for event in events]
                for case_id, events in self._events.items()
            },
        }
        self.path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    def save_item(self, item: InventoryItem) -> InventoryItem:
        result = super().save_item(item)
        self._flush()
        return result

    def save_supplier(self, supplier: Supplier) -> Supplier:
        result = super().save_supplier(supplier)
        self._flush()
        return result

    def save_case(self, case: ReplenishmentCase) -> ReplenishmentCase:
        result = super().save_case(case)
        self._flush()
        return result

    def append_event(self, case_id: str, event: DomainEvent) -> DomainEvent:
        result = super().append_event(case_id, event)
        self._flush()
        return result

    def claim_replenishment(self, sku: str, *, now):  # type: ignore[no-untyped-def]
        event = super().claim_replenishment(sku, now=now)
        if event is not None:
            self._flush()
        return event
