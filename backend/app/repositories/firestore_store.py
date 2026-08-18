"""Firestore persistence for Recovery Episodes.

TODO: Cloud SQL if document size or query patterns outgrow Firestore.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from eir_shared.events import DomainEvent, FollowUpDue, parse_event_dict
from eir_shared.observability import StructuredLogger, WorkflowTrace

from app.domain.recovery.models import EpisodeStatus, RecoveryEpisode
from app.repositories.review_repository import HumanReview, ReviewStatus

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

    def list(self, *, pending_only: bool = False) -> list[HumanReview]:
        items = [HumanReview.model_validate(item.to_dict()) for item in self._col.stream()]
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
