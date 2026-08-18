from eir_shared.gemini_config import (
    DEFAULT_GEMINI_LOCATION,
    resolve_gemini_location,
    resolve_infra_location,
)
from eir_shared.redaction import redact_command_args


def test_resolve_gemini_location_defaults_to_global() -> None:
    assert resolve_gemini_location("global") == "global"
    assert DEFAULT_GEMINI_LOCATION == "global"


def test_infra_and_gemini_locations_are_distinct() -> None:
    assert resolve_infra_location("us-central1") == "us-central1"
    assert resolve_gemini_location("global") != resolve_infra_location("us-central1")


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
