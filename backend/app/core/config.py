from typing import Annotated, Self

from eir_shared.env import repo_root
from eir_shared.gemini_config import DEFAULT_GEMINI_MODEL
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

_ENV_FILE = repo_root() / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE if _ENV_FILE.is_file() else None,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = "development"
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]
    google_cloud_project: str = "eir-ata"
    google_cloud_location: str = "us-central1"
    gemini_model: str = DEFAULT_GEMINI_MODEL
    gemini_location: str = "global"
    google_genai_use_vertexai: bool = False
    google_genai_use_enterprise: bool = False
    adk_runner_mode: str = "direct"
    adk_allow_direct_fallback: bool = True
    google_api_key: str = ""
    scheduler_secret: str = ""
    fhir_project: str = "eir-ata"
    fhir_location: str = "us-central1"
    fhir_dataset: str = "eir"
    fhir_store: str = "fhir-r4"
    pubsub_topic: str = "eir-recovery-events"
    pubsub_subscription: str = "eir-recovery-events-worker"
    voice_provider: str = "mock"
    # Supplier calls are business calls, not patient calls. They get their own
    # provider so the patient voice path and its synthetic-patient guard are
    # never widened to reach a vendor.
    supplier_voice_provider: str = "synthetic"
    voximplant_runtime_credentials: str = ""
    voximplant_application_id: str = ""
    voximplant_rule_id: str = ""
    voximplant_caller_id_e164: str = ""
    eir_demo_phone_e164: str = ""
    voximplant_callback_token: str = ""
    gemini_live_model: str = "gemini-live-2.5-flash-native-audio"
    gemini_live_location: str = "us-central1"
    gemini_live_voice: str = "Sulafat"
    voice_allow_non_synthetic: bool = False
    voximplant_voice_transport: str = "pstn"
    voximplant_account_name: str = ""
    voximplant_application_name: str = "eir-recovery"
    voximplant_web_user: str = "eir-preview-user"
    voximplant_web_password: str = ""
    voximplant_web_number: str = "eir-checkin"
    event_bus: str = "memory"
    episode_store: str = "memory"
    fhir_mode: str = "local"
    fhir_fallback: bool = True
    outreach_llm: bool = False
    workflow_subscriber: str = "local"
    pubsub_handle: bool = False
    data_dir: str = "data"
    model_armor_location: str = "us-central1"
    model_armor_template: str = "eir-agent-guard"
    session_secret: str = "local-dev-session-secret"
    adk_capture_message_content_in_spans: bool = False
    adk_otel_enabled: bool = True
    agent_runtime_audience: str = "https://eir-api-658898892127.us-central1.run.app"
    # Off by default: only fires quota-costing Veo calls when explicitly enabled.
    recovery_video_enabled: bool = False
    # Must be a model id this project can actually reach in `veo_location`: Vertex answers
    # an unavailable one with 404 NOT_FOUND at generate time, not at startup, so a wrong id
    # here surfaces as a failed clip rather than a boot error. `veo-3.1-fast-generate-preview`
    # is not served to this project and was exactly that failure.
    veo_model: str = "veo-3.1-lite-generate-001"
    veo_location: str = "us-central1"
    recovery_video_bucket: str = ""
    recovery_video_max_wait_seconds: int = 90
    # Veo 3 accepts a small set of clip lengths (4/6/8s) — confirm against the live model id
    # before changing this.
    recovery_video_duration_seconds: int = 8
    # Server-side guards. The frontend's disabled button is not a rate limit; these are.
    recovery_video_cooldown_seconds: int = 60
    recovery_video_daily_limit: int = 25

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> list[str]:
        if isinstance(value, str):
            parts: list[str] = []
            for chunk in value.replace(";", ",").split(","):
                item = chunk.strip()
                if item:
                    parts.append(item)
            return parts
        return value  # type: ignore[return-value]

    @model_validator(mode="after")
    def validate_production_session_secret(self) -> Self:
        if self.environment.strip().lower() != "production":
            return self
        secret = self.session_secret.strip()
        insecure = {"", "local-dev-session-secret", "change-me", "dev", "test"}
        if secret.lower() in insecure or len(secret) < 32:
            raise ValueError(
                "SESSION_SECRET must be a secure Secret Manager value in production"
            )
        return self


settings = Settings()
