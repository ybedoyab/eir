from typing import Annotated

from eir_shared.env import repo_root
from eir_shared.gemini_config import DEFAULT_GEMINI_MODEL
from pydantic import field_validator
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


settings = Settings()
