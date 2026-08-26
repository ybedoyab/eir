"""Composition root. Adapter choice lives here, not in domain handlers."""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from eir_agents.access.orchestrator import AccessOrchestrator
from eir_agents.orchestrator.handler import RecoveryOrchestrator
from eir_agents.outreach.llm import GeminiFollowUpSummarizer, TemplateFollowUpSummarizer
from eir_agents.procurement.voice import (
    SyntheticSupplierVoiceProvider,
    UnavailableSupplierVoiceProvider,
)
from eir_agents.records.fhir_client import LocalFhirClient
from eir_agents.registry.bootstrap import default_registry
from eir_agents.runtime.adk_runner import AdkAgentRunner
from eir_agents.safety.handler import SafetyGate
from eir_agents.supply.orchestrator import SupplyOrchestrator
from eir_shared.env import repo_root
from eir_shared.event_bus import InMemoryEventBus
from eir_shared.gemini_config import configure_genai_environment
from eir_shared.memory import InMemoryEpisodeStore
from eir_shared.observability import StructuredLogger

from app.core.config import settings
from app.integrations.agents.runtime import WorkflowRuntime
from app.integrations.agents.runtime_verification import verify_runtime
from app.integrations.agents.supply_runtime import SupplyWorkflowRuntime
from app.integrations.enterprise.demo_identity import DemoIdentityProvider
from app.integrations.enterprise.gateway import AgentGateway
from app.integrations.enterprise.registry import EnterpriseAgentRegistry
from app.integrations.enterprise.vertex_memory import build_agent_memory
from app.integrations.enterprise.vertex_model_armor import build_content_guard
from app.integrations.fhir.client import GoogleHealthcareFhirClient
from app.integrations.messaging.pubsub import CompositeEventBus, GooglePubSubEventBus
from app.integrations.voice.providers import voice_provider
from app.repositories.access_repository import InMemoryPatientAccessSessionRepository
from app.repositories.file_store import (
    FileRecoveryEpisodeRepository,
    FileReviewRepository,
    FileStructuredLogger,
    FileSupplyRepository,
    JsonEpisodeStore,
)
from app.repositories.firestore_access_repository import FirestorePatientAccessSessionRepository
from app.repositories.operational_store import (
    FirestoreOperationalSchedulingStore,
    InMemoryOperationalSchedulingStore,
)
from app.repositories.patient_repository import InMemoryPatientRepository, PatientRepository
from app.repositories.recovery_repository import (
    InMemoryRecoveryEpisodeRepository,
    RecoveryEpisodeRepository,
)
from app.repositories.review_repository import InMemoryReviewRepository
from app.repositories.runtime_telemetry import (
    build_adk_runtime_telemetry_store,
    runtime_service_name,
)
from app.repositories.scheduler_idempotency import build_scheduler_idempotency_store
from app.repositories.supply_repository import (
    InMemorySupplyRepository,
    SupplyRepository,
)
from app.services.access_service import PatientAccessService
from app.services.appointment_service import AppointmentService
from app.services.supply_service import SupplyService
from app.services.voice_web_session import web_voice_enabled, web_voice_login

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


def _build_fhir_client(*, testing: bool, operational_store: Any) -> Any:
    local = LocalFhirClient()
    if testing or settings.fhir_mode != "gcp":
        return local
    return GoogleHealthcareFhirClient(
        project=settings.fhir_project,
        location=settings.fhir_location,
        dataset=settings.fhir_dataset,
        store=settings.fhir_store,
        fallback=local,
        fallback_on_miss=settings.fhir_fallback,
        operational_store=operational_store,
    )


class Container:
    def __init__(self) -> None:
        configure_genai_environment(
            use_vertexai=settings.google_genai_use_vertexai,
            use_enterprise=settings.google_genai_use_enterprise,
            project=settings.google_cloud_project,
            infra_location=settings.google_cloud_location,
            api_key=settings.google_api_key or None,
        )
        testing = _in_pytest()
        self.testing = testing
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

        if firestore_client is not None:
            from app.repositories.firestore_store import FirestoreSupplyRepository

            self.supply: SupplyRepository = FirestoreSupplyRepository(firestore_client)
        elif use_files:
            self.supply = FileSupplyRepository(data_dir / "supply.json")
        else:
            self.supply = InMemorySupplyRepository()

        self.store_mode = store_mode if not testing else "memory"
        self.scheduler_idempotency = build_scheduler_idempotency_store(
            firestore_client=firestore_client,
            testing=testing,
        )
        self.voice_idempotency = build_scheduler_idempotency_store(
            firestore_client=firestore_client,
            testing=testing,
            collection="eir_voice_callbacks",
        )
        self.adk_telemetry = build_adk_runtime_telemetry_store(
            firestore_client=firestore_client,
            testing=testing,
        )
        service_name = "local" if testing else runtime_service_name()
        prefer_managed = settings.environment == "production" and not testing
        armor = build_content_guard(
            project=settings.google_cloud_project,
            location=settings.model_armor_location,
            template=settings.model_armor_template,
            prefer_managed=prefer_managed and settings.google_genai_use_vertexai,
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
        self.supply_orchestrator = SupplyOrchestrator(
            registry=self.registry,
            safety=SafetyGate(armor=armor),
            logger=self.logger,
        )
        self.access_orchestrator = AccessOrchestrator()
        self.identity = DemoIdentityProvider(settings.session_secret)
        if firestore_client is not None and not testing:
            self.access_sessions = FirestorePatientAccessSessionRepository(firestore_client)
            operational_store = FirestoreOperationalSchedulingStore(firestore_client)
        else:
            self.access_sessions = InMemoryPatientAccessSessionRepository()
            operational_store = InMemoryOperationalSchedulingStore()
        fhir = _build_fhir_client(testing=testing, operational_store=operational_store)
        self.operational = operational_store
        self.fhir = fhir
        self.fhir_mode = "local" if testing else settings.fhir_mode
        self.appointments = AppointmentService(fhir)
        if firestore_client is not None and not testing:
            from app.repositories.platform_verification import FirestorePlatformVerificationStore

            self.platform_verification = FirestorePlatformVerificationStore(firestore_client)
        else:
            from app.repositories.platform_verification import InMemoryPlatformVerificationStore

            self.platform_verification = InMemoryPlatformVerificationStore()
        self.access = PatientAccessService(
            sessions=self.access_sessions,
            appointments=self.appointments,
            orchestrator=self.access_orchestrator,
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
            telemetry=self.adk_telemetry,
            service_name=service_name,
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
            voice=_build_voice(testing=testing),
            supply=self.supply,
        )
        self.supplier_voice = _build_supplier_voice(testing=testing)
        self.supply_runtime = SupplyWorkflowRuntime(
            event_bus=self.event_bus,
            supply=self.supply,
            orchestrator=self.supply_orchestrator,
            reviews=self.reviews,
            logger=self.logger,
            adk_runner=self.adk_runner,
            supplier_voice=self.supplier_voice,
            episode_store=self.episode_store,
            gateway=AgentGateway(armor=armor),
        )
        self.voice_status = _voice_status(testing=testing, voice=self.runtime.voice)
        self.adk_runner_mode = "direct" if testing else settings.adk_runner_mode
        self.adk_allow_direct_fallback = allow_fallback
        self.runtime_verification = verify_runtime(
            adk_runner_mode=self.adk_runner_mode,
            adk_allow_direct_fallback=self.adk_allow_direct_fallback,
            use_vertexai=settings.google_genai_use_vertexai,
            use_enterprise=settings.google_genai_use_enterprise,
            project=settings.google_cloud_project,
            infra_location=settings.google_cloud_location,
            gemini_location=settings.gemini_location,
            api_key=settings.google_api_key,
            skip_probe=testing,
        )
        self.workflow_subscriber = "local" if testing else settings.workflow_subscriber
        self.pubsub_handle = is_worker
        if bind_runtime:
            self.runtime.bind()
            self.supply_runtime.bind()

    def adapter_status(self) -> dict[str, Any]:
        report = self.adk_runner.last_report
        verification = self.runtime_verification
        shared_adk = self.adk_telemetry.latest()
        adk_runtime = {
            "mode": verification.adk_runner_mode,
            "allow_direct_fallback": verification.adk_allow_direct_fallback,
            "last_invocation_success": (
                shared_adk.get("success")
                if shared_adk is not None
                else report.adk_invocation_succeeded
            ),
            "tools_invoked": shared_adk.get("tools_invoked", report.tools_invoked)
            if shared_adk is not None
            else report.tools_invoked,
            "used_direct_fallback": (
                shared_adk.get("used_direct_fallback", report.used_direct_fallback)
                if shared_adk is not None
                else report.used_direct_fallback
            ),
            "shared_worker_telemetry": shared_adk,
        }
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
            "managed_model_armor_available": getattr(
                self.content_guard, "managed_available", False
            ),
            "model_armor": getattr(self.content_guard, "status", lambda: {})(),
            "runtime_verification": {
                "vertex_model_probe": {
                    "model": verification.model,
                    "location": verification.gemini_location,
                    "success": verification.vertex_model_probe_success,
                    "error": verification.probe_error,
                },
                "adk_runtime": adk_runtime,
                "enterprise": {
                    "configured": verification.enterprise_configured,
                    "runtime_region": verification.infra_location,
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
            "voice": getattr(self, "voice_status", {}),
            "supply": {
                "supplier_voice_provider": getattr(
                    self.supplier_voice, "provider_name", "unknown"
                ),
                "supplier_voice_mode": getattr(self.supplier_voice, "mode", "sync"),
                "synthetic_suppliers_only": True,
                "inventory_items": len(self.supply.list_items()),
                "open_replenishment_cases": len(
                    [
                        case
                        for case in self.supply.list_cases()
                        if case.status.value not in {"COMPLETED", "CANCELLED"}
                    ]
                ),
            },
            "platform_verification": self._platform_verification_status(),
        }

    def _platform_verification_status(self) -> dict[str, Any]:
        snapshot = self.platform_verification.snapshot()
        snapshot["managed_model_armor_verified"] = getattr(
            self.content_guard, "managed_available", False
        )
        return snapshot

    def seed(self) -> None:
        patients_path = MOCKS_DIR / "patients" / "patients.json"
        if patients_path.exists():
            self.patients.seed_from_file(patients_path)
        SupplyService(self.supply).seed(
            MOCKS_DIR / "inventory" / "inventory.json",
            MOCKS_DIR / "suppliers" / "suppliers.json",
        )

        from app.demo_ops import apply_demo_operations

        apply_demo_operations(
            episodes=self.episodes,
            reviews=self.reviews,
            operational=getattr(self, "operational", None),
        )


def _build_voice(*, testing: bool) -> Any:
    if testing:
        return voice_provider("mock")
    name = settings.voice_provider.strip().lower() or "synthetic"
    if name != "voximplant":
        return voice_provider(name)
    try:
        return voice_provider(
            "voximplant",
            credentials_source=settings.voximplant_runtime_credentials,
            rule_id=settings.voximplant_rule_id,
            application_id=settings.voximplant_application_id or None,
            demo_phone_e164=settings.eir_demo_phone_e164,
            caller_id_e164=settings.voximplant_caller_id_e164,
            gemini_live_model=settings.gemini_live_model,
            allow_non_synthetic=settings.voice_allow_non_synthetic,
        )
    except Exception:
        logger.exception("Voximplant voice provider unavailable; using synthetic fallback")
        return voice_provider("synthetic")


def _build_supplier_voice(*, testing: bool) -> Any:
    """Pick the vendor call adapter.

    Defaults to the scripted stub. There is no real-PSTN option here yet: the
    catalog phone numbers are fictional, so a live dial would fail rather than
    reach a supplier.
    """
    name = settings.supplier_voice_provider.strip().lower() or "synthetic"
    if name == "unreachable" and not testing:
        return UnavailableSupplierVoiceProvider()
    return SyntheticSupplierVoiceProvider()


def _voice_status(*, testing: bool, voice: Any) -> dict[str, Any]:
    provider = getattr(voice, "provider_name", "unknown")
    configured = settings.voice_provider.strip().lower() or "mock"
    if testing:
        configured = "mock"
    runtime_creds = bool(settings.voximplant_runtime_credentials.strip())
    admin_creds_name = "VOXIMPLANT_CREDENTIALS"
    return {
        "configured_provider": configured,
        "active_provider": provider,
        "mode": getattr(voice, "mode", "sync"),
        "pstn_enabled": provider == "voximplant",
        "synthetic_patients_only": True,
        "gemini_live_model": settings.gemini_live_model,
        "gemini_live_location": settings.gemini_live_location,
        "gemini_live_voice": settings.gemini_live_voice,
        "runtime_credentials_configured": runtime_creds if not testing else False,
        "admin_credentials_used_at_runtime": False,
        "admin_credentials_env": admin_creds_name,
        "rule_configured": bool(str(settings.voximplant_rule_id).strip()) if not testing else False,
        "application_configured": bool(str(settings.voximplant_application_id).strip())
        if not testing
        else False,
        "callback_token_configured": bool(settings.voximplant_callback_token)
        if not testing
        else False,
        "destination_configured": bool(settings.eir_demo_phone_e164) if not testing else False,
        "caller_id_configured": bool(settings.voximplant_caller_id_e164) if not testing else False,
        "voice_transport": "pstn" if testing else (settings.voximplant_voice_transport or "pstn"),
        # The in-page WebRTC check-in is independent of the PSTN path above: the
        # browser dials the scenario directly, so it works with no Caller ID.
        "browser_voice_enabled": web_voice_enabled() if not testing else False,
        "browser_voice_login_configured": bool(web_voice_login()) if not testing else False,
    }


@lru_cache
def get_container() -> Container:
    return Container()
