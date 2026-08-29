"""Verify GCP prerequisites and refresh documented exceptions.

Terraform owns static infrastructure. This script verifies readiness and
updates scheduler targets when the API URL changes.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))
from gcloud_utils import redact_command_args  # noqa: E402

PROJECT = "eir-ata"
LOCATION = "us-central1"
TOPIC = "eir-recovery-events"
SUBSCRIPTION = "eir-recovery-events-worker"
DATASET = "eir"
FHIR_STORE = "fhir-r4"
RUNTIME_SA = f"eir-runtime@{PROJECT}.iam.gserviceaccount.com"
SCHEDULER_JOB = "eir-process-due-follow-ups"
SCHEDULER_SECRET_NAME = "eir-scheduler-secret"
API_SERVICE = "eir-api"


def _run(args: list[str], *, ok_codes: set[int] | None = None) -> int:
    import shutil

    ok_codes = ok_codes or {0}
    gcloud = shutil.which("gcloud") or "gcloud"
    if args and args[0] == "gcloud":
        args = [gcloud, *args[1:]]
    print("+", " ".join(redact_command_args(args)), flush=True)
    completed = subprocess.run(args, check=False)
    return completed.returncode if completed.returncode in ok_codes else 1


def _gcloud_output(args: list[str]) -> str:
    import shutil

    gcloud = shutil.which("gcloud") or "gcloud"
    if args and args[0] == "gcloud":
        args = [gcloud, *args[1:]]
    completed = subprocess.run(args, capture_output=True, text=True, check=False)
    return completed.stdout.strip() if completed.returncode == 0 else ""


def _project_number() -> str:
    number = _gcloud_output(
        ["gcloud", "projects", "describe", PROJECT, "--format=value(projectNumber)"]
    )
    return number or "658898892127"


def _service_url(service: str) -> str:
    return f"https://{service}-{_project_number()}.{LOCATION}.run.app"


def _recovery_video_bucket() -> str:
    """Must match google_storage_bucket.recovery_media and deploy.py."""
    return f"eir-ata-recovery-media-{_project_number()}"


def _scheduler_secret() -> str:
    token = os.environ.get("SCHEDULER_SECRET", "").strip()
    if token:
        return token
    return _gcloud_output(
        [
            "gcloud",
            "secrets",
            "versions",
            "access",
            "latest",
            f"--secret={SCHEDULER_SECRET_NAME}",
            f"--project={PROJECT}",
        ]
    )


def _ensure_scheduler(api_url: str) -> None:
    target = f"{api_url}/api/v1/recovery/process-due-follow-ups"
    token = _scheduler_secret()
    common = [
        f"--location={LOCATION}",
        "--schedule=*/15 * * * *",
        f"--uri={target}",
        "--http-method=POST",
        f"--oidc-service-account-email={RUNTIME_SA}",
        f"--oidc-token-audience={api_url}",
        f"--project={PROJECT}",
    ]
    if token:
        common.append(f"--headers=X-Scheduler-Token={token}")
    describe = _run(
        [
            "gcloud",
            "scheduler",
            "jobs",
            "describe",
            SCHEDULER_JOB,
            f"--location={LOCATION}",
            f"--project={PROJECT}",
        ],
        ok_codes={0, 1},
    )
    verb = "update" if describe == 0 else "create"
    _run(["gcloud", "scheduler", "jobs", verb, "http", SCHEDULER_JOB, *common], ok_codes={0, 1})
    print(json.dumps({"scheduler_job": SCHEDULER_JOB, "target": target}))


def _verify_gemini_access() -> int:
    script = """
import os
from google import genai
from eir_shared.gemini_config import (
    configure_genai_environment,
    genai_client_kwargs,
    resolve_gemini_model,
)
configure_genai_environment(
    use_vertexai=True,
    use_enterprise=True,
    project=os.environ['GOOGLE_CLOUD_PROJECT'],
    infra_location=os.environ.get('GOOGLE_CLOUD_LOCATION', 'us-central1'),
)
client = genai.Client(**genai_client_kwargs(location=os.environ.get('GEMINI_LOCATION', 'global')))
model = resolve_gemini_model()
response = client.models.generate_content(model=model, contents='Reply with exactly: ok')
print(model, os.environ.get('GEMINI_LOCATION', 'global'), (response.text or '').strip())
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        env={
            "GOOGLE_CLOUD_PROJECT": PROJECT,
            "GOOGLE_CLOUD_LOCATION": LOCATION,
            "GEMINI_LOCATION": "global",
            "GOOGLE_GENAI_USE_VERTEXAI": "TRUE",
            "GOOGLE_GENAI_USE_ENTERPRISE": "TRUE",
            "GEMINI_MODEL": "gemini-3.5-flash",
        },
    )
    return completed.returncode


def main() -> int:
    checks = {
        "runtime_service_account": _run(
            ["gcloud", "iam", "service-accounts", "describe", RUNTIME_SA, f"--project={PROJECT}"]
        )
        == 0,
        "recovery_topic": _run(
            ["gcloud", "pubsub", "topics", "describe", TOPIC, f"--project={PROJECT}"]
        )
        == 0,
        "recovery_subscription": _run(
            [
                "gcloud",
                "pubsub",
                "subscriptions",
                "describe",
                SUBSCRIPTION,
                f"--project={PROJECT}",
            ]
        )
        == 0,
        "firestore": _run(
            [
                "gcloud",
                "firestore",
                "databases",
                "describe",
                f"--project={PROJECT}",
                "--database=(default)",
            ]
        )
        == 0,
        "recovery_video_bucket": _run(
            [
                "gcloud",
                "storage",
                "buckets",
                "describe",
                f"gs://{_recovery_video_bucket()}",
                f"--project={PROJECT}",
            ]
        )
        == 0,
        "fhir_store": _run(
            [
                "gcloud",
                "healthcare",
                "fhir-stores",
                "describe",
                FHIR_STORE,
                f"--dataset={DATASET}",
                f"--location={LOCATION}",
                f"--project={PROJECT}",
            ]
        )
        == 0,
    }
    missing = [name for name, ok in checks.items() if not ok]
    if missing:
        print(
            json.dumps(
                {
                    "status": "missing_prerequisites",
                    "missing": missing,
                    "hint": "Apply infra/terraform before running provision.py",
                }
            ),
            file=sys.stderr,
        )
        return 1

    api_url = _service_url(API_SERVICE)
    print(json.dumps({"api_url": api_url}))
    _ensure_scheduler(api_url)
    verify_code = _verify_gemini_access()
    if verify_code != 0:
        print("warning: gemini verification failed", file=sys.stderr)
    print("provision verify finished")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
