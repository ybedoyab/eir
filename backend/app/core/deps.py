"""Composition root. Swap in-memory adapters here later."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from eir_agents.orchestrator.handler import RecoveryOrchestrator
from eir_agents.registry.bootstrap import default_registry
from eir_agents.safety.handler import SafetyGate
from eir_shared.event_bus import InMemoryEventBus
from eir_shared.memory import InMemoryAgentMemory, InMemoryEpisodeStore
from eir_shared.observability import StructuredLogger

from app.integrations.agents.runtime import WorkflowRuntime
from app.repositories.patient_repository import InMemoryPatientRepository, PatientRepository
from app.repositories.recovery_repository import (
    InMemoryRecoveryEpisodeRepository,
    RecoveryEpisodeRepository,
)
from app.repositories.review_repository import InMemoryReviewRepository

MOCKS_DIR = Path(__file__).resolve().parents[3] / "mocks"


class Container:
    def __init__(self) -> None:
        self.event_bus = InMemoryEventBus()
        self.patients: PatientRepository = InMemoryPatientRepository()
        self.episodes: RecoveryEpisodeRepository = InMemoryRecoveryEpisodeRepository()
        self.reviews = InMemoryReviewRepository()
        self.episode_store = InMemoryEpisodeStore()
        self.agent_memory = InMemoryAgentMemory()
        self.logger = StructuredLogger("eir")
        self.registry = default_registry()
        self.orchestrator = RecoveryOrchestrator(
            registry=self.registry,
            safety=SafetyGate(),
            logger=self.logger,
        )
        self.runtime = WorkflowRuntime(
            event_bus=self.event_bus,
            episodes=self.episodes,
            episode_store=self.episode_store,
            agent_memory=self.agent_memory,
            reviews=self.reviews,
            orchestrator=self.orchestrator,
            logger=self.logger,
        )
        self.runtime.bind()

    def seed(self) -> None:
        patients_path = MOCKS_DIR / "patients" / "patients.json"
        if patients_path.exists():
            self.patients.seed_from_file(patients_path)


@lru_cache
def get_container() -> Container:
    return Container()
