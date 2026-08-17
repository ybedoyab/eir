"""Deploy EIR API and Pub/Sub worker to Cloud Run (project eir-ata)."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

PROJECT = "eir-ata"
REGION = "us-central1"
REPOSITORY = "eir"
IMAGE = f"{REGION}-docker.pkg.dev/{PROJECT}/{REPOSITORY}/backend:latest"
API_SERVICE = "eir-api"
WORKER_SERVICE = "eir-worker"
RUNTIME_SA = f"eir-runtime@{PROJECT}.iam.gserviceaccount.com"

SHARED_ENV = [
    "GOOGLE_CLOUD_PROJECT=eir-ata",
    "GOOGLE_CLOUD_LOCATION=us-central1",
    "EPISODE_STORE=firestore",
    "FHIR_MODE=gcp",
    "FHIR_FALLBACK=true",
    "FHIR_PROJECT=eir-ata",
    "FHIR_LOCATION=us-central1",
    "FHIR_DATASET=eir",
    "FHIR_STORE=fhir-r4",
    "EVENT_BUS=pubsub",
    "PUBSUB_TOPIC=eir-recovery-events",
    "PUBSUB_SUBSCRIPTION=eir-recovery-events-worker",
    "OUTREACH_LLM=true",
    "GEMINI_MODEL=gemini-2.0-flash",
    "ENVIRONMENT=production",
]


def _gcloud() -> str:
    found = shutil.which("gcloud")
    if found:
        return found
    if sys.platform == "win32":
        candidate = Path.home() / "AppData/Local/Google/Cloud SDK/google-cloud-sdk/bin/gcloud.cmd"
        if candidate.is_file():
            return str(candidate)
    return "gcloud"


def _run(args: list[str], *, ok_codes: set[int] | None = None) -> int:
    ok_codes = ok_codes or {0}
    if args and args[0] == "gcloud":
        args = [_gcloud(), *args[1:]]
    print("+", " ".join(args), flush=True)
    completed = subprocess.run(args, check=False)
    if completed.returncode not in ok_codes:
        print(f"command failed with {completed.returncode}", file=sys.stderr)
        return completed.returncode
    return 0


def _ensure_artifact_registry() -> int:
    _run(
        [
            "gcloud",
            "services",
            "enable",
            "run.googleapis.com",
            "artifactregistry.googleapis.com",
            "cloudbuild.googleapis.com",
            "secretmanager.googleapis.com",
            f"--project={PROJECT}",
        ]
    )
    if (
        _run(
            [
                "gcloud",
                "artifacts",
                "repositories",
                "describe",
                REPOSITORY,
                f"--location={REGION}",
                f"--project={PROJECT}",
            ]
        )
        != 0
    ):
        _run(
            [
                "gcloud",
                "artifacts",
                "repositories",
                "create",
                REPOSITORY,
                f"--location={REGION}",
                "--repository-format=docker",
                f"--project={PROJECT}",
            ]
        )
    return 0


def _ensure_runtime_service_account() -> int:
    describe = ["gcloud", "iam", "service-accounts", "describe", RUNTIME_SA, f"--project={PROJECT}"]
    if _run(describe) != 0:
        _run(
            [
                "gcloud",
                "iam",
                "service-accounts",
                "create",
                "eir-runtime",
                f"--project={PROJECT}",
                "--display-name=EIR runtime",
            ]
        )
    for role in (
        "roles/datastore.user",
        "roles/pubsub.publisher",
        "roles/pubsub.subscriber",
        "roles/healthcare.fhirResourceEditor",
    ):
        _run(
            [
                "gcloud",
                "projects",
                "add-iam-policy-binding",
                PROJECT,
                f"--member=serviceAccount:{RUNTIME_SA}",
                f"--role={role}",
            ]
        )
    return 0


def _ensure_secret() -> int:
    name = "eir-gemini-api-key"
    if _run(["gcloud", "secrets", "describe", name, f"--project={PROJECT}"]) != 0:
        if _run(["gcloud", "secrets", "create", name, f"--project={PROJECT}"]) != 0:
            return 1

    versions = subprocess.run(
        [_gcloud(), "secrets", "versions", "list", name, f"--project={PROJECT}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if versions.returncode != 0 or not versions.stdout.strip():
        key = ""
        env_path = Path(".env")
        if env_path.is_file():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                if line.startswith("GOOGLE_API_KEY="):
                    key = line.split("=", 1)[1].strip()
                    break
        if not key:
            print("GOOGLE_API_KEY missing in .env; create secret version manually", file=sys.stderr)
            return 1
        tmp = Path(".cursor/eir-gemini-key.tmp")
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(key, encoding="utf-8")
        code = _run(
            [
                "gcloud",
                "secrets",
                "versions",
                "add",
                name,
                f"--project={PROJECT}",
                f"--data-file={tmp}",
            ]
        )
        tmp.unlink(missing_ok=True)
        if code != 0:
            return code
    _run(
        [
            "gcloud",
            "secrets",
            "add-iam-policy-binding",
            name,
            f"--project={PROJECT}",
            f"--member=serviceAccount:{RUNTIME_SA}",
            "--role=roles/secretmanager.secretAccessor",
        ]
    )
    return 0


def _build_image() -> int:
    return _run(
        [
            "gcloud",
            "builds",
            "submit",
            ".",
            "--config=infra/gcp/cloudbuild.yaml",
            f"--substitutions=_IMAGE={IMAGE}",
            f"--project={PROJECT}",
        ]
    )


def _deploy_api() -> int:
    env = [*SHARED_ENV, "WORKFLOW_SUBSCRIBER=pubsub", "PUBSUB_HANDLE=false"]
    return _run(
        [
            "gcloud",
            "run",
            "deploy",
            API_SERVICE,
            f"--image={IMAGE}",
            f"--region={REGION}",
            f"--project={PROJECT}",
            f"--service-account={RUNTIME_SA}",
            "--allow-unauthenticated",
            "--port=8080",
            "--memory=1Gi",
            "--timeout=300",
            "--min-instances=0",
            "--max-instances=3",
            "--set-env-vars",
            ",".join(env),
            "--set-secrets",
            "GOOGLE_API_KEY=eir-gemini-api-key:latest",
        ]
    )


def _deploy_worker() -> int:
    env = [*SHARED_ENV, "WORKFLOW_SUBSCRIBER=pubsub", "PUBSUB_HANDLE=true"]
    return _run(
        [
            "gcloud",
            "run",
            "deploy",
            WORKER_SERVICE,
            f"--image={IMAGE}",
            f"--region={REGION}",
            f"--project={PROJECT}",
            f"--service-account={RUNTIME_SA}",
            "--no-allow-unauthenticated",
            "--port=8080",
            "--command=uv",
            "--args=run,--package,eir-backend,python,-m,app.worker,--handle",
            "--memory=1Gi",
            "--timeout=3600",
            "--min-instances=1",
            "--max-instances=1",
            "--no-cpu-throttling",
            "--set-env-vars",
            ",".join(env),
            "--set-secrets",
            "GOOGLE_API_KEY=eir-gemini-api-key:latest",
        ]
    )


def main() -> int:
    for step in (
        _ensure_artifact_registry,
        _ensure_runtime_service_account,
        _ensure_secret,
        _build_image,
        _deploy_api,
        _deploy_worker,
    ):
        if step() != 0:
            return 1
    print("deploy finished")
    _run(
        [
            "gcloud",
            "run",
            "services",
            "describe",
            API_SERVICE,
            f"--region={REGION}",
            f"--project={PROJECT}",
            "--format=value(status.url)",
        ]
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
