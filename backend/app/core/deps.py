"""Composition root. Adapter choice lives here, not in domain handlers."""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path

from eir_agents.orchestrator.handler import RecoveryOrchestrator
from eir_agents.outreach.llm import GeminiFollowUpSummarizer, TemplateFollowUpSummarizer
from eir_agents.records.fhir_client import LocalFhirClient
from eir_agents.registry.bootstrap import default_registry
from eir_agents.safety.handler import SafetyGate
from eir_shared.env import repo_root
from eir_shared.event_bus import InMemoryEventBus
from eir_shared.memory import InMemoryAgentMemory, InMemoryEpisodeStore
from eir_shared.observability import StructuredLogger

from app.core.config import settings
from app.integrations.agents.runtime import WorkflowRuntime
from app.integrations.fhir.client import GoogleHealthcareFhirClient
from app.integrations.messaging.pubsub import CompositeEventBus, GooglePubSubEventBus
from app.repositories.file_store import (
    FileRecoveryEpisodeRepository,
    FileReviewRepository,
    JsonEpisodeStore,
)
from app.repositories.patient_repository import InMemoryPatientRepository, PatientRepository
from app.repositories.recovery_repository import (
    InMemoryRecoveryEpisodeRepository,
    RecoveryEpisodeRepository,
)
from app.repositories.review_repository import InMemoryReviewRepository

MOCKS_DIR = Path(__file__).resolve().parents[3] / "mocks"
logger = logging.getLogger("eir.deps")


def _in_pytest() -> bool:
    return os.getenv("PYTEST_CURRENT_TEST") is not None


def _data_dir() -> Path:
    return repo_root() / settings.data_dir


class Container:
    def __init__(self) -> None:
        local_bus = InMemoryEventBus()
        sink = None
        if settings.event_bus == "pubsub" and not _in_pytest():
            try:
                sink = GooglePubSubEventBus(settings.google_cloud_project, settings.pubsub_topic)
            except Exception:
                logger.exception("Pub/Sub sink unavailable; using in-memory event bus")
                sink = None
        self.event_bus = CompositeEventBus(local_bus, sink) if sink else local_bus

        use_files = settings.episode_store == "file" and not _in_pytest()
        data_dir = _data_dir()
        self.patients: PatientRepository = InMemoryPatientRepository()
        self.episodes: RecoveryEpisodeRepository = (
            FileRecoveryEpisodeRepository(data_dir / "episodes.json")
            if use_files
            else InMemoryRecoveryEpisodeRepository()
        )
        self.reviews = (
            FileReviewRepository(data_dir / "reviews.json")
            if use_files
            else InMemoryReviewRepository()
        )
        self.episode_store = (
            JsonEpisodeStore(data_dir / "episode-store.json")
            if use_files
            else InMemoryEpisodeStore()
        )
        self.agent_memory = InMemoryAgentMemory()
        self.logger = StructuredLogger("eir")
        self.registry = default_registry()
        self.orchestrator = RecoveryOrchestrator(
            registry=self.registry,
            safety=SafetyGate(),
            logger=self.logger,
        )
        fhir = LocalFhirClient()
        if settings.fhir_mode == "gcp" and not _in_pytest():
            fhir = GoogleHealthcareFhirClient(
                project=settings.fhir_project,
                location=settings.fhir_location,
                dataset=settings.fhir_dataset,
                store=settings.fhir_store,
                fallback=fhir,
            )
        summarizer = TemplateFollowUpSummarizer()
        if settings.outreach_llm and settings.google_api_key and not _in_pytest():
            summarizer = GeminiFollowUpSummarizer(settings.google_api_key, settings.gemini_model)
        self.runtime = WorkflowRuntime(
            event_bus=self.event_bus,
            episodes=self.episodes,
            episode_store=self.episode_store,
            agent_memory=self.agent_memory,
            reviews=self.reviews,
            orchestrator=self.orchestrator,
            logger=self.logger,
            fhir=fhir,
            summarizer=summarizer,
        )
        self.runtime.bind()

    def seed(self) -> None:
        patients_path = MOCKS_DIR / "patients" / "patients.json"
        if patients_path.exists():
            self.patients.seed_from_file(patients_path)


@lru_cache
def get_container() -> Container:
    return Container()
