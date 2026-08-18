"""Shared ADK runtime telemetry for split API/worker deployments."""

from __future__ import annotations

import os
import threading
from collections import deque
from typing import Any, Protocol

from eir_shared.runtime_telemetry import AdkInvocationTelemetry

HISTORY_LIMIT = 50
_HISTORY_FIELDS = (
    "timestamp",
    "episode_id",
    "agent_name",
    "capability",
    "model",
    "model_location",
    "tools_invoked",
    "success",
    "used_direct_fallback",
    "security_adapter",
    "security_category",
    "trace_id",
    "service",
)


def _history_item(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: payload.get(key) for key in _HISTORY_FIELDS}


class AdkRuntimeTelemetryStore(Protocol):
    def record(self, telemetry: AdkInvocationTelemetry) -> None: ...

    def latest(self) -> dict[str, Any] | None: ...

    def history(self, limit: int = 25) -> list[dict[str, Any]]: ...


class InMemoryAdkRuntimeTelemetryStore:
    def __init__(self, *, max_items: int = HISTORY_LIMIT) -> None:
        self._lock = threading.Lock()
        self._latest: dict[str, Any] | None = None
        self._history: deque[dict[str, Any]] = deque(maxlen=max_items)

    def record(self, telemetry: AdkInvocationTelemetry) -> None:
        payload = telemetry.to_dict()
        with self._lock:
            self._latest = payload
            self._history.appendleft(_history_item(payload))

    def latest(self) -> dict[str, Any] | None:
        with self._lock:
            return dict(self._latest) if self._latest else None

    def history(self, limit: int = 25) -> list[dict[str, Any]]:
        size = max(1, min(limit, HISTORY_LIMIT))
        with self._lock:
            return [dict(item) for item in list(self._history)[:size]]


class FirestoreAdkRuntimeTelemetryStore:
    DOCUMENT_ID = "adk_worker"

    def __init__(self, client: Any, collection: str = "eir_runtime_telemetry") -> None:
        self._doc = client.collection(collection).document(self.DOCUMENT_ID)

    def record(self, telemetry: AdkInvocationTelemetry) -> None:
        from google.cloud import firestore

        payload = telemetry.to_dict()
        snapshot = self._doc.get()
        existing = dict(snapshot.to_dict() or {}) if snapshot.exists else {}
        prior = list(existing.get("history") or [])
        history = [_history_item(payload), *prior][:HISTORY_LIMIT]
        payload["history"] = history
        payload["updated_at"] = firestore.SERVER_TIMESTAMP
        self._doc.set(payload)

    def latest(self) -> dict[str, Any] | None:
        snapshot = self._doc.get()
        if not snapshot.exists:
            return None
        data = dict(snapshot.to_dict() or {})
        data.pop("updated_at", None)
        data.pop("history", None)
        return data

    def history(self, limit: int = 25) -> list[dict[str, Any]]:
        size = max(1, min(limit, HISTORY_LIMIT))
        snapshot = self._doc.get()
        if not snapshot.exists:
            return []
        data = dict(snapshot.to_dict() or {})
        items = list(data.get("history") or [])
        return items[:size]


def runtime_service_name() -> str:
    return os.getenv("K_SERVICE") or os.getenv("SERVICE_NAME") or "local"


def build_adk_runtime_telemetry_store(
    *,
    firestore_client: Any | None,
    testing: bool,
) -> AdkRuntimeTelemetryStore:
    if testing or firestore_client is None:
        return InMemoryAdkRuntimeTelemetryStore()
    return FirestoreAdkRuntimeTelemetryStore(firestore_client)
