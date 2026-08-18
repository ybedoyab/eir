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
from eir_agents.runtime.adk_runner import AdkAgentRunner
from eir_agents.safety.handler import SafetyGate
from eir_shared.env import repo_root
from eir_shared.event_bus import InMemoryEventBus
from eir_shared.gemini_config import configure_genai_environment
from eir_shared.memory import InMemoryEpisodeStore
from eir_shared.observability import StructuredLogger

from app.core.config import settings
from app.integrations.agents.runtime import WorkflowRuntime
from app.integrations.agents.runtime_verification import verify_runtime
from app.integrations.enterprise.gateway import AgentGateway
from app.integrations.enterprise.registry import EnterpriseAgentRegistry
from app.integrations.enterprise.vertex_memory import build_agent_memory
from app.integrations.enterprise.vertex_model_armor import build_content_guard
from app.integrations.fhir.client import GoogleHealthcareFhirClient
from app.integrations.messaging.pubsub import CompositeEventBus, GooglePubSubEventBus
from app.integrations.voice.providers import voice_provider
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
from app.repositories.scheduler_idempotency import build_scheduler_idempotency_store

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
        configure_genai_environment(
            use_vertexai=settings.google_genai_use_vertexai,
            use_enterprise=settings.google_genai_use_enterprise,
            project=settings.google_cloud_project,
            location=settings.google_cloud_location,
            api_key=settings.google_api_key or None,
        )
        testing = _in_pytest()
        is_worker = settings.pubsub_handle and not testing
        local_bus = InMemoryEventBus()
        sink = None

        if is_worker:
            self.event_bus = local_bus
            self.pubsub_sink = False
            bind_runtime = True
        elif settings.workflow_subscriber == "pubsub" and not testing:
            try:
                self.event_bus = GooglePubSubEventBus(
                    settings.google_cloud_project,
                    settings.pubsub_topic,
                )
                self.pubsub_sink = True
                bind_runtime = False
            except Exception:
                logger.exception("Pub/Sub publisher unavailable; falling back to in-memory bus")
                self.event_bus = local_bus
                self.pubsub_sink = False
                bind_runtime = True
        else:
            if settings.event_bus == "pubsub" and not testing:
                try:
                    sink = GooglePubSubEventBus(
                        settings.google_cloud_project,
                        settings.pubsub_topic,
                    )
                except Exception:
                    logger.exception("Pub/Sub sink unavailable; using in-memory event bus")
                    sink = None
            self.event_bus = CompositeEventBus(local_bus, sink) if sink else local_bus
            self.pubsub_sink = sink is not None
            bind_runtime = True

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
        self.scheduler_idempotency = build_scheduler_idempotency_store(
            firestore_client=firestore_client,
            testing=testing,
        )
        prefer_managed = settings.environment == "production" and not testing
        armor = build_content_guard(
            project=settings.google_cloud_project,
            location=settings.google_cloud_location,
            prefer_vertex=prefer_managed and settings.google_genai_use_vertexai,
        )
        self.content_guard = armor
        self.agent_memory = build_agent_memory(
            firestore_client=firestore_client,
            prefer_agent_engine=prefer_managed and settings.google_genai_use_enterprise,
        )
        local_registry = default_registry()
        self.registry = EnterpriseAgentRegistry(local_registry)
        self.orchestrator = RecoveryOrchestrator(
            registry=self.registry,
            safety=SafetyGate(armor=armor),
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
        allow_fallback = settings.adk_allow_direct_fallback if not testing else True
        self.adk_runner = AdkAgentRunner(
            mode="direct" if testing else settings.adk_runner_mode,
            allow_direct_fallback=allow_fallback,
        )
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
            adk_runner=self.adk_runner,
            gateway=AgentGateway(armor=armor),
            voice=voice_provider("mock" if testing else settings.voice_provider),
        )
        self.adk_runner_mode = "direct" if testing else settings.adk_runner_mode
        self.adk_allow_direct_fallback = allow_fallback
        self.runtime_verification = verify_runtime(
            adk_runner_mode=self.adk_runner_mode,
            adk_allow_direct_fallback=self.adk_allow_direct_fallback,
            use_vertexai=settings.google_genai_use_vertexai,
            use_enterprise=settings.google_genai_use_enterprise,
            project=settings.google_cloud_project,
            location=settings.google_cloud_location,
            api_key=settings.google_api_key,
            skip_probe=testing,
        )
        self.workflow_subscriber = "local" if testing else settings.workflow_subscriber
        self.pubsub_handle = is_worker
        if bind_runtime:
            self.runtime.bind()

    def adapter_status(self) -> dict[str, Any]:
        report = self.adk_runner.last_report
        verification = self.runtime_verification
        return {
            "event_bus": "pubsub" if self.pubsub_sink else "memory",
            "episode_store": self.store_mode,
            "fhir_mode": self.fhir_mode,
            "outreach_llm": self.outreach_llm,
            "adk_runner_mode": self.adk_runner_mode,
            "adk_allow_direct_fallback": self.adk_allow_direct_fallback,
            "workflow_subscriber": self.workflow_subscriber,
            "pubsub_sink": self.pubsub_sink,
            "pubsub_handle": self.pubsub_handle,
            "agent_memory_adapter": getattr(self.agent_memory, "adapter_name", "unknown"),
            "content_guard_adapter": getattr(self.content_guard, "adapter_name", "unknown"),
            "runtime_verification": {
                "vertex_model_probe": {
                    "model": verification.model,
                    "success": verification.vertex_model_probe_success,
                    "error": verification.probe_error,
                },
                "adk_runtime": {
                    "mode": verification.adk_runner_mode,
                    "allow_direct_fallback": verification.adk_allow_direct_fallback,
                },
                "enterprise": {
                    "configured": verification.enterprise_configured,
                    "managed_agent_runtime_verified": verification.managed_agent_runtime_verified,
                },
            },
            "last_adk_run": {
                "mode": report.mode,
                "last_invocation_success": report.adk_invocation_succeeded,
                "tools_invoked": report.tools_invoked,
                "used_direct_fallback": report.used_direct_fallback,
                "error": report.error,
            },
        }

    def seed(self) -> None:
        patients_path = MOCKS_DIR / "patients" / "patients.json"
        if patients_path.exists():
            self.patients.seed_from_file(patients_path)


@lru_cache
def get_container() -> Container:
    return Container()
