"""Durable daily ceiling for Veo generations.

A hard cap on how many clips can be generated per UTC day, so a click-happy demo audience
cannot run up the Vertex bill or the media bucket. Same shape as
``scheduler_idempotency.py``: a Protocol, a Firestore implementation, an in-memory fallback,
and a builder that ``deps.py`` calls once.
"""

from __future__ import annotations

import threading
from datetime import UTC, datetime
from typing import Any, Protocol


def utc_day(now: datetime | None = None) -> str:
    return (now or datetime.now(UTC)).strftime("%Y-%m-%d")


class DailyVideoBudget(Protocol):
    def increment(self, day: str, *, limit: int) -> bool:
        """Return True when a slot was claimed; False when the day is already at ``limit``."""

    def used(self, day: str) -> int: ...


class InMemoryDailyVideoBudget:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counts: dict[str, int] = {}

    def increment(self, day: str, *, limit: int) -> bool:
        with self._lock:
            current = self._counts.get(day, 0)
            if current >= limit:
                return False
            self._counts[day] = current + 1
            return True

    def used(self, day: str) -> int:
        with self._lock:
            return self._counts.get(day, 0)


class FirestoreDailyVideoBudget:
    """Transactional so the API and the worker cannot both spend the last slot."""

    def __init__(self, client: Any, collection: str = "eir_video_budget") -> None:
        self._col = client.collection(collection)

    def increment(self, day: str, *, limit: int) -> bool:
        from google.cloud import firestore

        doc_ref = self._col.document(day)

        @firestore.transactional
        def _bump(transaction: firestore.Transaction) -> bool:
            snapshot = doc_ref.get(transaction=transaction)
            current = int((snapshot.to_dict() or {}).get("count", 0)) if snapshot.exists else 0
            if current >= limit:
                return False
            transaction.set(
                doc_ref,
                {"count": current + 1, "updated_at": firestore.SERVER_TIMESTAMP},
            )
            return True

        return _bump(self._col._client.transaction())

    def used(self, day: str) -> int:
        snapshot = self._col.document(day).get()
        if not snapshot.exists:
            return 0
        return int((snapshot.to_dict() or {}).get("count", 0))


def build_video_budget(
    *,
    firestore_client: Any | None,
    testing: bool,
    collection: str = "eir_video_budget",
) -> DailyVideoBudget:
    if testing or firestore_client is None:
        return InMemoryDailyVideoBudget()
    return FirestoreDailyVideoBudget(firestore_client, collection=collection)
