"""Composition root. Swap in-memory adapters here later."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from eir_shared.event_bus import InMemoryEventBus

from app.repositories.patient_repository import InMemoryPatientRepository, PatientRepository
from app.repositories.recovery_repository import (
    InMemoryRecoveryEpisodeRepository,
    RecoveryEpisodeRepository,
)

MOCKS_DIR = Path(__file__).resolve().parents[3] / "mocks"


class Container:
    def __init__(self) -> None:
        self.event_bus = InMemoryEventBus()
        self.patients: PatientRepository = InMemoryPatientRepository()
        self.episodes: RecoveryEpisodeRepository = InMemoryRecoveryEpisodeRepository()

    def seed(self) -> None:
        patients_path = MOCKS_DIR / "patients" / "patients.json"
        if patients_path.exists():
            self.patients.seed_from_file(patients_path)


@lru_cache
def get_container() -> Container:
    return Container()
