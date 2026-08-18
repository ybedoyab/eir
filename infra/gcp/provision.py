"""Idempotent GCP bootstrap for project eir-ata."""

from __future__ import annotations

import json
import os
import subprocess
import sys

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
    ok_codes = ok_codes or {0}
    print("+", " ".join(args), flush=True)
    completed = subprocess.run(args, check=False)
    if completed.returncode not in ok_codes:
        print(f"command failed with {completed.returncode}", file=sys.stderr)
    return completed.returncode


def _gcloud_output(args: list[str]) -> str:
    completed = subprocess.run(args, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        return ""
    return completed.stdout.strip()


def _service_url(service: str) -> str:
    number = _gcloud_output(
        ["gcloud", "projects", "describe", PROJECT, "--format=value(projectNumber)"]
    )
    return f"https://{service}-{number}.{LOCATION}.run.app"


def _enable_apis() -> None:
    _run(
        [
            "gcloud",
            "services",
            "enable",
            "pubsub.googleapis.com",
            "healthcare.googleapis.com",
            "firestore.googleapis.com",
            "aiplatform.googleapis.com",
            "cloudscheduler.googleapis.com",
            "run.googleapis.com",
            "iamcredentials.googleapis.com",
            f"--project={PROJECT}",
        ]
    )


def _grant_runtime_roles() -> None:
    for role in (
        "roles/aiplatform.user",
        "roles/datastore.user",
        "roles/pubsub.subscriber",
        "roles/pubsub.publisher",
        "roles/healthcare.fhirResourceEditor",
        "roles/logging.logWriter",
        "roles/secretmanager.secretAccessor",
    ):
        _run(
            [
                "gcloud",
                "projects",
                "add-iam-policy-binding",
                PROJECT,
                f"--member=serviceAccount:{RUNTIME_SA}",
                f"--role={role}",
            ],
            ok_codes={0, 1},
        )


def _verify_gemini_access() -> int:
    script = """
import os
from google import genai
from eir_shared.gemini_config import configure_genai_environment, resolve_gemini_model, genai_client_kwargs
configure_genai_environment(use_vertexai=True, use_enterprise=True, project=os.environ['GOOGLE_CLOUD_PROJECT'], location=os.environ.get('GOOGLE_CLOUD_LOCATION', 'us-central1'))
client = genai.Client(**genai_client_kwargs())
model = resolve_gemini_model()
response = client.models.generate_content(model=model, contents='Reply with exactly: ok')
print(model, (response.text or '').strip())
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        env={
            "GOOGLE_CLOUD_PROJECT": PROJECT,
            "GOOGLE_CLOUD_LOCATION": LOCATION,
            "GOOGLE_GENAI_USE_VERTEXAI": "TRUE",
            "GOOGLE_GENAI_USE_ENTERPRISE": "TRUE",
            "GEMINI_MODEL": "gemini-3.5-flash",
        },
    )
    return completed.returncode


def _scheduler_secret() -> str:
    token = os.environ.get("SCHEDULER_SECRET", "").strip()
    if token:
        return token
    value = _gcloud_output(
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
    if not value:
        print(
            f"warning: {SCHEDULER_SECRET_NAME} unavailable; scheduler header auth may fail",
            file=sys.stderr,
        )
        return ""
    return value


def _ensure_scheduler(api_url: str) -> None:
    target = f"{api_url}/api/v1/recovery/process-due-follow-ups"
    token = _scheduler_secret()
    common = [
        f"--location={LOCATION}",
        f"--schedule=*/15 * * * *",
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
    if describe == 0:
        args = [
            "gcloud",
            "scheduler",
            "jobs",
            "update",
            "http",
            SCHEDULER_JOB,
            *common,
        ]
    else:
        args = [
            "gcloud",
            "scheduler",
            "jobs",
            "create",
            "http",
            SCHEDULER_JOB,
            *common,
        ]
    _run(args, ok_codes={0, 1})
    print(json.dumps({"scheduler_job": SCHEDULER_JOB, "target": target}))


def main() -> int:
    _enable_apis()
    if _run(["gcloud", "pubsub", "topics", "describe", TOPIC, f"--project={PROJECT}"]) != 0:
        _run(["gcloud", "pubsub", "topics", "create", TOPIC, f"--project={PROJECT}"])
    if (
        _run(
            [
                "gcloud",
                "pubsub",
                "subscriptions",
                "describe",
                SUBSCRIPTION,
                f"--project={PROJECT}",
            ]
        )
        != 0
    ):
        _run(
            [
                "gcloud",
                "pubsub",
                "subscriptions",
                "create",
                SUBSCRIPTION,
                f"--topic={TOPIC}",
                "--ack-deadline=60",
                f"--project={PROJECT}",
            ]
        )
    firestore = _run(
        [
            "gcloud",
            "firestore",
            "databases",
            "describe",
            f"--project={PROJECT}",
            "--database=(default)",
        ]
    )
    if firestore != 0:
        _run(
            [
                "gcloud",
                "firestore",
                "databases",
                "create",
                f"--project={PROJECT}",
                f"--location={LOCATION}",
                "--type=firestore-native",
            ]
        )
    dataset = _run(
        [
            "gcloud",
            "healthcare",
            "datasets",
            "describe",
            DATASET,
            f"--location={LOCATION}",
            f"--project={PROJECT}",
        ]
    )
    if dataset != 0:
        _run(
            [
                "gcloud",
                "healthcare",
                "datasets",
                "create",
                DATASET,
                f"--location={LOCATION}",
                f"--project={PROJECT}",
            ]
        )
    store = _run(
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
    if store != 0:
        _run(
            [
                "gcloud",
                "healthcare",
                "fhir-stores",
                "create",
                FHIR_STORE,
                f"--dataset={DATASET}",
                f"--location={LOCATION}",
                "--version=R4",
                f"--project={PROJECT}",
            ]
        )
    _grant_runtime_roles()
    verify_code = _verify_gemini_access()
    if verify_code != 0:
        print("warning: gemini verification failed; check runtime service account permissions", file=sys.stderr)
    api_url = _service_url(API_SERVICE)
    print(json.dumps({"api_url": api_url}))
    _ensure_scheduler(api_url)
    print("provision finished")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
