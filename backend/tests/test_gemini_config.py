import os
import threading

from eir_shared.gemini_config import (
    genai_client_kwargs,
    resolve_gemini_location,
    resolve_infra_location,
)
from eir_shared.redaction import redact_command_args


def test_resolve_gemini_location_defaults_to_global() -> None:
    assert resolve_gemini_location("global") == "global"


def test_infra_and_gemini_locations_are_distinct() -> None:
    assert resolve_infra_location("us-central1") == "us-central1"
    assert resolve_gemini_location("global") != resolve_infra_location("us-central1")


def test_genai_client_kwargs_use_global_without_mutating_infra_env() -> None:
    os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"
    os.environ["GEMINI_LOCATION"] = "global"
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "TRUE"
    kwargs = genai_client_kwargs(location="global")
    assert kwargs["location"] == "global"
    assert os.environ["GOOGLE_CLOUD_LOCATION"] == "us-central1"


def test_concurrent_genai_client_kwargs_remain_global() -> None:
    os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"
    os.environ["GEMINI_LOCATION"] = "global"
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "TRUE"
    results: list[str] = []

    def worker() -> None:
        kwargs = genai_client_kwargs(location=resolve_gemini_location())
        results.append(kwargs["location"])
        assert os.environ["GOOGLE_CLOUD_LOCATION"] == "us-central1"

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert results == ["global", "global", "global", "global"]


def test_redact_command_args_hides_scheduler_token() -> None:
    args = [
        "gcloud",
        "scheduler",
        "jobs",
        "create",
        "http",
        "job",
        "--headers=X-Scheduler-Token=super-secret-value",
    ]
    redacted = redact_command_args(args)
    assert "super-secret-value" not in " ".join(redacted)
    assert redacted[-1] == "--headers=X-Scheduler-Token=***REDACTED***"
