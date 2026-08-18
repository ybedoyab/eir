import os
import threading

from eir_agents.common.model import gemini_model
from eir_shared.gemini_config import configure_genai_environment, resolve_gemini_location


def _client_location(model: object) -> str:
    client = model.api_client  # type: ignore[attr-defined]
    return client._api_client.location  # noqa: SLF001


def _configure_vertex_test_env() -> None:
    configure_genai_environment(
        use_vertexai=True,
        project="test-project",
        infra_location="us-central1",
    )
    os.environ["GEMINI_LOCATION"] = "global"
    os.environ["GEMINI_MODEL"] = "gemini-3.5-flash"
    gemini_model.cache_clear()


def test_gemini_model_client_uses_global_without_env_mutation() -> None:
    _configure_vertex_test_env()
    model = gemini_model()
    assert model.model == "gemini-3.5-flash"
    assert _client_location(model) == "global"
    assert os.environ["GOOGLE_CLOUD_LOCATION"] == "us-central1"


def test_concurrent_gemini_model_clients_keep_global_location() -> None:
    _configure_vertex_test_env()
    locations: list[str] = []
    lock = threading.Lock()

    def worker() -> None:
        model = gemini_model()
        location = _client_location(model)
        with lock:
            locations.append(location)
        assert os.environ["GOOGLE_CLOUD_LOCATION"] == "us-central1"

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert locations == ["global", "global", "global", "global"]
    assert resolve_gemini_location() == "global"
