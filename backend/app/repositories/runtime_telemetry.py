"""Shared ADK runtime telemetry for split API/worker deployments."""

from __future__ import annotations

import os
import threading
from typing import Any, Protocol

from eir_shared.runtime_telemetry import AdkInvocationTelemetry


class AdkRuntimeTelemetryStore(Protocol):
    def record(self, telemetry: AdkInvocationTelemetry) -> None: ...

    def latest(self) -> dict[str, Any] | None: ...


class InMemoryAdkRuntimeTelemetryStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._latest: dict[str, Any] | None = None

    def record(self, telemetry: AdkInvocationTelemetry) -> None:
        with self._lock:
            self._latest = telemetry.to_dict()

    def latest(self) -> dict[str, Any] | None:
        with self._lock:
            return dict(self._latest) if self._latest else None


class FirestoreAdkRuntimeTelemetryStore:
    DOCUMENT_ID = "adk_worker"

    def __init__(self, client: Any, collection: str = "eir_runtime_telemetry") -> None:
        self._doc = client.collection(collection).document(self.DOCUMENT_ID)

    def record(self, telemetry: AdkInvocationTelemetry) -> None:
        from google.cloud import firestore

        payload = telemetry.to_dict()
        payload["updated_at"] = firestore.SERVER_TIMESTAMP
        self._doc.set(payload)

    def latest(self) -> dict[str, Any] | None:
        snapshot = self._doc.get()
        if not snapshot.exists:
            return None
        data = dict(snapshot.to_dict() or {})
        data.pop("updated_at", None)
        return data


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
