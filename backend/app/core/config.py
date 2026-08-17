from eir_shared.env import repo_root
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = repo_root() / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE if _ENV_FILE.is_file() else None,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = "development"
    cors_origins: list[str] = ["http://localhost:3000"]
    google_cloud_project: str = "eir-ata"
    google_cloud_location: str = "us-central1"
    gemini_model: str = "gemini-2.5-flash"
    google_api_key: str = ""
    fhir_project: str = "eir-ata"
    fhir_location: str = "us-central1"
    fhir_dataset: str = "eir"
    fhir_store: str = "fhir-r4"
    pubsub_topic: str = "eir-recovery-events"
    voice_provider: str = "mock"
    event_bus: str = "memory"
    episode_store: str = "memory"
    fhir_mode: str = "local"
    outreach_llm: bool = False
    data_dir: str = "data"


settings = Settings()
