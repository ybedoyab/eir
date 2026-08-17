"""Patient persistence.

TODO: FirestorePatientRepository / CloudSqlPatientRepository implementing this protocol.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

from app.domain.patients.models import Patient


class PatientRepository(Protocol):
    def get(self, patient_id: str) -> Patient | None: ...

    def list(self) -> list[Patient]: ...

    def save(self, patient: Patient) -> Patient: ...

    def seed_from_file(self, path: Path) -> None: ...


class InMemoryPatientRepository:
    def __init__(self) -> None:
        self._items: dict[str, Patient] = {}

    def get(self, patient_id: str) -> Patient | None:
        return self._items.get(patient_id)

    def list(self) -> list[Patient]:
        return list(self._items.values())

    def save(self, patient: Patient) -> Patient:
        self._items[patient.id] = patient
        return patient

    def seed_from_file(self, path: Path) -> None:
        data = json.loads(path.read_text(encoding="utf-8"))
        for raw in data:
            patient = Patient.model_validate(raw)
            self.save(patient)
