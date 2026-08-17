"""Composition root. Adapter choice lives here, not in domain handlers."""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

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
    FileStructuredLogger,
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


def _firestore_client() -> Any | None:
    try:
        from google.cloud import firestore

        return firestore.Client(project=settings.google_cloud_project)
    except Exception:
        logger.exception("Firestore client unavailable")
        return None


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
        self.pubsub_sink = sink is not None

        testing = _in_pytest()
        store_mode = "memory" if testing else settings.episode_store
        data_dir = _data_dir()
        firestore_client = (
            _firestore_client() if store_mode == "firestore" and not testing else None
        )
        if store_mode == "firestore" and firestore_client is None and not testing:
            logger.warning("Firestore requested but unavailable; using file store")
            store_mode = "file"

        use_files = store_mode == "file"
        self.patients: PatientRepository = InMemoryPatientRepository()
        if firestore_client is not None:
            from app.repositories.firestore_store import (
                FirestoreEpisodeStore,
                FirestoreRecoveryEpisodeRepository,
                FirestoreReviewRepository,
                FirestoreStructuredLogger,
            )

            self.episodes: RecoveryEpisodeRepository = FirestoreRecoveryEpisodeRepository(
                firestore_client
            )
            self.reviews = FirestoreReviewRepository(firestore_client)
            self.episode_store = FirestoreEpisodeStore(firestore_client)
            self.logger = FirestoreStructuredLogger("eir", firestore_client)
        elif use_files:
            self.episodes = FileRecoveryEpisodeRepository(data_dir / "episodes.json")
            self.reviews = FileReviewRepository(data_dir / "reviews.json")
            self.episode_store = JsonEpisodeStore(data_dir / "episode-store.json")
            self.logger = FileStructuredLogger("eir", data_dir / "traces.json")
        else:
            self.episodes = InMemoryRecoveryEpisodeRepository()
            self.reviews = InMemoryReviewRepository()
            self.episode_store = InMemoryEpisodeStore()
            self.logger = StructuredLogger("eir")

        self.store_mode = store_mode if not testing else "memory"
        self.agent_memory = InMemoryAgentMemory()
        self.registry = default_registry()
        self.orchestrator = RecoveryOrchestrator(
            registry=self.registry,
            safety=SafetyGate(),
            logger=self.logger,
        )
        fhir = LocalFhirClient()
        self.fhir_mode = "local" if testing else settings.fhir_mode
        if self.fhir_mode == "gcp":
            fhir = GoogleHealthcareFhirClient(
                project=settings.fhir_project,
                location=settings.fhir_location,
                dataset=settings.fhir_dataset,
                store=settings.fhir_store,
                fallback=fhir,
                fallback_on_miss=settings.fhir_fallback,
            )
        summarizer = TemplateFollowUpSummarizer()
        self.outreach_llm = False
        if settings.outreach_llm and settings.google_api_key and not testing:
            summarizer = GeminiFollowUpSummarizer(settings.google_api_key, settings.gemini_model)
            self.outreach_llm = True
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
        self.workflow_subscriber = "local" if testing else settings.workflow_subscriber
        if self.workflow_subscriber != "pubsub":
            self.runtime.bind()

    def adapter_status(self) -> dict[str, Any]:
        return {
            "event_bus": "pubsub" if self.pubsub_sink else "memory",
            "episode_store": self.store_mode,
            "fhir_mode": self.fhir_mode,
            "outreach_llm": self.outreach_llm,
            "workflow_subscriber": self.workflow_subscriber,
            "pubsub_sink": self.pubsub_sink,
        }

    def seed(self) -> None:
        patients_path = MOCKS_DIR / "patients" / "patients.json"
        if patients_path.exists():
            self.patients.seed_from_file(patients_path)


@lru_cache
def get_container() -> Container:
    return Container()
