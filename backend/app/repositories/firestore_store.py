"""Firestore persistence for Recovery Episodes.

TODO: Cloud SQL if document size or query patterns outgrow Firestore.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from eir_shared.events import (
    DomainEvent,
    FollowUpDue,
    InventoryLevelLow,
    parse_event_dict,
)
from eir_shared.observability import StructuredLogger, WorkflowTrace
from eir_shared.supply import InventoryItem, ReplenishmentCase, Supplier

from app.domain.recovery.models import EpisodeStatus, RecoveryEpisode
from app.repositories.review_repository import HumanReview, ReviewStatus
from app.repositories.supply_repository import OPEN_CASE_STATUSES

_SCHEDULABLE = frozenset({EpisodeStatus.ACTIVE, EpisodeStatus.WAITING_FOR_NEXT_FOLLOWUP})


class FirestoreRecoveryEpisodeRepository:
    def __init__(self, client: Any, collection: str = "recovery_episodes") -> None:
        self._col = client.collection(collection)

    def get(self, episode_id: str) -> RecoveryEpisode | None:
        snapshot = self._col.document(episode_id).get()
        if not snapshot.exists:
            return None
        data = snapshot.to_dict() or {}
        episode = data.get("episode")
        return RecoveryEpisode.model_validate(episode) if episode else None

    def list(self) -> list[RecoveryEpisode]:
        items: list[RecoveryEpisode] = []
        for snapshot in self._col.stream():
            data = snapshot.to_dict() or {}
            episode = data.get("episode")
            if episode:
                items.append(RecoveryEpisode.model_validate(episode))
        return items

    def save(self, episode: RecoveryEpisode) -> RecoveryEpisode:
        ref = self._col.document(episode.id)
        snapshot = ref.get()
        events = []
        if snapshot.exists:
            events = (snapshot.to_dict() or {}).get("events") or []
        ref.set({"episode": episode.model_dump(mode="json"), "events": events})
        return episode

    def append_event(self, episode_id: str, event: DomainEvent) -> DomainEvent:
        ref = self._col.document(episode_id)
        snapshot = ref.get()
        data = (snapshot.to_dict() or {}) if snapshot.exists else {}
        events = list(data.get("events") or [])
        events.append(event.model_dump(mode="json"))
        data["events"] = events
        ref.set(data, merge=True)
        return event

    def list_events(self, episode_id: str) -> list[DomainEvent]:
        snapshot = self._col.document(episode_id).get()
        if not snapshot.exists:
            return []
        events = (snapshot.to_dict() or {}).get("events") or []
        return [parse_event_dict(item) for item in events]

    def claim_due_follow_up(
        self,
        episode_id: str,
        *,
        now: datetime,
        interval_days: int,
    ) -> FollowUpDue | None:
        from google.cloud import firestore

        ref = self._col.document(episode_id)

        @firestore.transactional
        def _claim(transaction: firestore.Transaction) -> FollowUpDue | None:
            snapshot = ref.get(transaction=transaction)
            if not snapshot.exists:
                return None
            data = snapshot.to_dict() or {}
            episode_data = data.get("episode")
            if not episode_data:
                return None
            episode = RecoveryEpisode.model_validate(episode_data)
            events = list(data.get("events") or [])
            if episode.status not in _SCHEDULABLE:
                return None
            if episode.next_follow_up_at is None:
                return None
            if events and events[-1].get("event_type") == "FollowUpDue":
                return None
            follow_up_at = episode.next_follow_up_at
            if follow_up_at.tzinfo is None:
                follow_up_at = follow_up_at.replace(tzinfo=UTC)
            if follow_up_at > now:
                return None
            event = FollowUpDue(episode_id=episode_id)
            events.append(event.model_dump(mode="json"))
            episode.next_follow_up_at = now + timedelta(days=interval_days)
            transaction.set(
                ref,
                {"episode": episode.model_dump(mode="json"), "events": events},
            )
            return event

        transaction = self._col._client.transaction()
        return _claim(transaction)


class FirestoreReviewRepository:
    def __init__(self, client: Any, collection: str = "human_reviews") -> None:
        self._col = client.collection(collection)

    def save(self, review: HumanReview) -> HumanReview:
        self._col.document(review.id).set(review.model_dump(mode="json"))
        return review

    def get(self, review_id: str) -> HumanReview | None:
        snapshot = self._col.document(review_id).get()
        if not snapshot.exists:
            return None
        return HumanReview.model_validate(snapshot.to_dict())

    def list(
        self,
        *,
        pending_only: bool = False,
        workflow: str | None = None,
    ) -> list[HumanReview]:
        items = [HumanReview.model_validate(item.to_dict()) for item in self._col.stream()]
        if workflow is not None:
            items = [item for item in items if item.workflow == workflow]
        if pending_only:
            return [item for item in items if item.status == ReviewStatus.PENDING]
        return items

    def for_episode(self, episode_id: str) -> list[HumanReview]:
        return [item for item in self.list() if item.episode_id == episode_id]


class FirestoreEpisodeStore:
    def __init__(self, client: Any, collection: str = "episode_checkpoints") -> None:
        self._col = client.collection(collection)

    async def get(self, episode_id: str) -> dict[str, Any] | None:
        snapshot = self._col.document(episode_id).get()
        if not snapshot.exists:
            return None
        return dict(snapshot.to_dict() or {})

    async def save(self, episode_id: str, state: dict[str, Any]) -> None:
        self._col.document(episode_id).set(state)


class FirestoreStructuredLogger(StructuredLogger):
    def __init__(self, name: str, client: Any, collection: str = "workflow_traces") -> None:
        super().__init__(name)
        self._col = client.collection(collection)

    def list_records(self) -> list[WorkflowTrace]:
        return [WorkflowTrace.model_validate(item.to_dict()) for item in self._col.stream()]

    def emit(self, trace: WorkflowTrace) -> None:
        super().emit(trace)
        self._col.document(trace.trace_id).set(trace.model_dump(mode="json"))


class FirestoreSupplyRepository:
    """Supply state in Firestore. Cases embed their event log, like episodes."""

    def __init__(self, client: Any, prefix: str = "eir") -> None:
        self._items_col = client.collection(f"{prefix}_inventory_items")
        self._suppliers_col = client.collection(f"{prefix}_suppliers")
        self._cases_col = client.collection(f"{prefix}_replenishment_cases")

    def get_item(self, sku: str) -> InventoryItem | None:
        snapshot = self._items_col.document(sku).get()
        if not snapshot.exists:
            return None
        return InventoryItem.model_validate(snapshot.to_dict())

    def list_items(self) -> list[InventoryItem]:
        items = [InventoryItem.model_validate(item.to_dict()) for item in self._items_col.stream()]
        return sorted(items, key=lambda item: item.sku)

    def save_item(self, item: InventoryItem) -> InventoryItem:
        self._items_col.document(item.sku).set(item.model_dump(mode="json"))
        return item

    def adjust_stock(self, sku: str, delta: int) -> InventoryItem | None:
        from google.cloud import firestore

        ref = self._items_col.document(sku)

        @firestore.transactional
        def _adjust(transaction: firestore.Transaction) -> InventoryItem | None:
            snapshot = ref.get(transaction=transaction)
            if not snapshot.exists:
                return None
            item = InventoryItem.model_validate(snapshot.to_dict())
            item.on_hand = max(item.on_hand + delta, 0)
            item.updated_at = datetime.now(UTC)
            transaction.set(ref, item.model_dump(mode="json"))
            return item

        return _adjust(self._items_col._client.transaction())

    def get_supplier(self, supplier_id: str) -> Supplier | None:
        snapshot = self._suppliers_col.document(supplier_id).get()
        if not snapshot.exists:
            return None
        return Supplier.model_validate(snapshot.to_dict())

    def list_suppliers(self, sku: str | None = None) -> list[Supplier]:
        items = [Supplier.model_validate(item.to_dict()) for item in self._suppliers_col.stream()]
        items.sort(key=lambda supplier: supplier.name)
        if sku is None:
            return items
        return [supplier for supplier in items if supplier.entry_for(sku) is not None]

    def save_supplier(self, supplier: Supplier) -> Supplier:
        self._suppliers_col.document(supplier.id).set(supplier.model_dump(mode="json"))
        return supplier

    def get_case(self, case_id: str) -> ReplenishmentCase | None:
        snapshot = self._cases_col.document(case_id).get()
        if not snapshot.exists:
            return None
        data = snapshot.to_dict() or {}
        case = data.get("case")
        return ReplenishmentCase.model_validate(case) if case else None

    def list_cases(self) -> list[ReplenishmentCase]:
        cases: list[ReplenishmentCase] = []
        for snapshot in self._cases_col.stream():
            data = snapshot.to_dict() or {}
            case = data.get("case")
            if case:
                cases.append(ReplenishmentCase.model_validate(case))
        return sorted(cases, key=lambda case: case.opened_at, reverse=True)

    def open_case_for_sku(self, sku: str) -> ReplenishmentCase | None:
        for case in self.list_cases():
            if case.sku == sku and case.status in OPEN_CASE_STATUSES:
                return case
        return None

    def save_case(self, case: ReplenishmentCase) -> ReplenishmentCase:
        ref = self._cases_col.document(case.id)
        snapshot = ref.get()
        events = []
        if snapshot.exists:
            events = (snapshot.to_dict() or {}).get("events") or []
        ref.set({"case": case.model_dump(mode="json"), "events": events})
        return case

    def append_event(self, case_id: str, event: DomainEvent) -> DomainEvent:
        ref = self._cases_col.document(case_id)
        snapshot = ref.get()
        data = (snapshot.to_dict() or {}) if snapshot.exists else {}
        events = list(data.get("events") or [])
        events.append(event.model_dump(mode="json"))
        data["events"] = events
        ref.set(data, merge=True)
        return event

    def list_events(self, case_id: str) -> list[DomainEvent]:
        snapshot = self._cases_col.document(case_id).get()
        if not snapshot.exists:
            return []
        events = (snapshot.to_dict() or {}).get("events") or []
        return [parse_event_dict(item) for item in events]

    def claim_replenishment(self, sku: str, *, now: datetime) -> InventoryLevelLow | None:
        """Transactional guard on the inventory item.

        The item document is the contended resource: two scheduler runs racing on
        the same SKU must not both open a case.
        """
        from google.cloud import firestore

        item_ref = self._items_col.document(sku)

        @firestore.transactional
        def _claim(transaction: firestore.Transaction) -> InventoryItem | None:
            snapshot = item_ref.get(transaction=transaction)
            if not snapshot.exists:
                return None
            item = InventoryItem.model_validate(snapshot.to_dict())
            if not item.needs_replenishment():
                return None
            item.updated_at = now
            transaction.set(item_ref, item.model_dump(mode="json"))
            return item

        item = _claim(self._items_col._client.transaction())
        if item is None:
            return None
        if self.open_case_for_sku(sku) is not None:
            return None
        case = ReplenishmentCase(
            id=str(uuid4()),
            sku=item.sku,
            item_name=item.name,
            opened_at=now,
            requested_quantity=item.suggested_quantity(),
            rationale=(
                f"on hand {item.on_hand} {item.unit} at or below reorder point "
                f"{item.reorder_point}"
            ),
        )
        self.save_case(case)
        event = InventoryLevelLow(
            episode_id=case.id,
            sku=item.sku,
            occurred_at=now,
            payload={
                "sku": item.sku,
                "item_name": item.name,
                "on_hand": item.on_hand,
                "reorder_point": item.reorder_point,
                "target_level": item.target_level,
                "suggested_quantity": case.requested_quantity,
                "days_of_cover": item.days_of_cover,
                "critical": item.critical,
                "stock_status": item.status.value,
            },
        )
        self.append_event(case.id, event)
        return event
