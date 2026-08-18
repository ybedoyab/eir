"""Patient access session persistence."""

from __future__ import annotations

import threading
from typing import Protocol

from app.domain.access.models import PatientAccessSession


class PatientAccessSessionRepository(Protocol):
    def get(self, session_id: str) -> PatientAccessSession | None: ...

    def save(self, session: PatientAccessSession) -> PatientAccessSession: ...

    def list_for_patient(self, patient_id: str) -> list[PatientAccessSession]: ...


class InMemoryPatientAccessSessionRepository:
    def __init__(self) -> None:
        self._items: dict[str, PatientAccessSession] = {}
        self._lock = threading.Lock()

    def get(self, session_id: str) -> PatientAccessSession | None:
        return self._items.get(session_id)

    def save(self, session: PatientAccessSession) -> PatientAccessSession:
        with self._lock:
            self._items[session.id] = session
        return session

    def list_for_patient(self, patient_id: str) -> list[PatientAccessSession]:
        return [item for item in self._items.values() if item.patient_id == patient_id]
