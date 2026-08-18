"""Durable idempotency markers for Cloud Scheduler follow-up runs."""

from __future__ import annotations

import threading
from typing import Any, Protocol


class SchedulerIdempotencyStore(Protocol):
    def claim_run(self, key: str) -> bool:
        """Return True when this caller owns the run; False when duplicate."""


class InMemorySchedulerIdempotencyStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._claimed: set[str] = set()

    def claim_run(self, key: str) -> bool:
        with self._lock:
            if key in self._claimed:
                return False
            self._claimed.add(key)
            return True


class FirestoreSchedulerIdempotencyStore:
    def __init__(self, client: Any, collection: str = "eir_scheduler_runs") -> None:
        self._col = client.collection(collection)

    def claim_run(self, key: str) -> bool:
        from google.cloud import firestore

        doc_ref = self._col.document(key)

        @firestore.transactional
        def _claim(transaction: firestore.Transaction) -> bool:
            snapshot = doc_ref.get(transaction=transaction)
            if snapshot.exists:
                return False
            transaction.set(
                doc_ref,
                {"status": "claimed", "created_at": firestore.SERVER_TIMESTAMP},
            )
            return True

        transaction = self._col._client.transaction()
        return _claim(transaction)


def build_scheduler_idempotency_store(
    *,
    firestore_client: Any | None,
    testing: bool,
) -> SchedulerIdempotencyStore:
    if testing or firestore_client is None:
        return InMemorySchedulerIdempotencyStore()
    return FirestoreSchedulerIdempotencyStore(firestore_client)
