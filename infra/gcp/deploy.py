"""Deploy EIR API, worker, and frontend to Cloud Run (project eir-ata)."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

PROJECT = "eir-ata"
REGION = "us-central1"
REPOSITORY = "eir"
BACKEND_IMAGE = f"{REGION}-docker.pkg.dev/{PROJECT}/{REPOSITORY}/backend:latest"
FRONTEND_IMAGE = f"{REGION}-docker.pkg.dev/{PROJECT}/{REPOSITORY}/frontend:latest"
API_SERVICE = "eir-api"
WORKER_SERVICE = "eir-worker"
UI_SERVICE = "eir-ui"
RUNTIME_SA = f"eir-runtime@{PROJECT}.iam.gserviceaccount.com"
SCHEDULER_SECRET_NAME = "eir-scheduler-secret"
DEPLOY_SECRETS = (
    "GOOGLE_API_KEY=eir-gemini-api-key:latest,"
    f"SCHEDULER_SECRET={SCHEDULER_SECRET_NAME}:latest"
)

BASE_ENV = [
    "GOOGLE_CLOUD_PROJECT=eir-ata",
    "GOOGLE_CLOUD_LOCATION=us-central1",
    "EPISODE_STORE=firestore",
    "FHIR_MODE=gcp",
    "FHIR_FALLBACK=false",
    "FHIR_PROJECT=eir-ata",
    "FHIR_LOCATION=us-central1",
    "FHIR_DATASET=eir",
    "FHIR_STORE=fhir-r4",
    "EVENT_BUS=pubsub",
    "PUBSUB_TOPIC=eir-recovery-events",
    "PUBSUB_SUBSCRIPTION=eir-recovery-events-worker",
    "OUTREACH_LLM=true",
    "GEMINI_MODEL=gemini-3.5-flash",
    "GOOGLE_GENAI_USE_VERTEXAI=TRUE",
    "GOOGLE_GENAI_USE_ENTERPRISE=TRUE",
    "ADK_RUNNER_MODE=adk",
    "ADK_ALLOW_DIRECT_FALLBACK=false",
    "VOICE_PROVIDER=synthetic",
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


def _gcloud_output(args: list[str]) -> str:
    if args and args[0] == "gcloud":
        args = [_gcloud(), *args[1:]]
    completed = subprocess.run(args, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        return ""
    return completed.stdout.strip()


def _project_number() -> str:
    number = _gcloud_output(
        ["gcloud", "projects", "describe", PROJECT, "--format=value(projectNumber)"]
    )
    return number or "658898892127"


def _service_url(service: str, project_number: str) -> str:
    return f"https://{service}-{project_number}.{REGION}.run.app"


def _shared_env(project_number: str) -> list[str]:
    ui_url = _service_url(UI_SERVICE, project_number)
    return [
        *BASE_ENV,
        f"CORS_ORIGINS=http://localhost:3000,{ui_url}",
    ]


def _write_env_file(env: list[str], name: str) -> Path:
    path = Path(".cursor") / name
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{key}: '{value}'" for key, value in (item.split("=", 1) for item in env)]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


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
        "roles/aiplatform.user",
        "roles/datastore.user",
        "roles/pubsub.publisher",
        "roles/pubsub.subscriber",
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


def _ensure_scheduler_secret() -> int:
    if _run(["gcloud", "secrets", "describe", SCHEDULER_SECRET_NAME, f"--project={PROJECT}"]) != 0:
        if _run(["gcloud", "secrets", "create", SCHEDULER_SECRET_NAME, f"--project={PROJECT}"]) != 0:
            return 1

    versions = subprocess.run(
        [_gcloud(), "secrets", "versions", "list", SCHEDULER_SECRET_NAME, f"--project={PROJECT}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if versions.returncode != 0 or not versions.stdout.strip():
        import secrets

        token = secrets.token_urlsafe(32)
        tmp = Path(".cursor/eir-scheduler-secret.tmp")
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(token, encoding="utf-8")
        code = _run(
            [
                "gcloud",
                "secrets",
                "versions",
                "add",
                SCHEDULER_SECRET_NAME,
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
            SCHEDULER_SECRET_NAME,
            f"--project={PROJECT}",
            f"--member=serviceAccount:{RUNTIME_SA}",
            "--role=roles/secretmanager.secretAccessor",
        ]
    )
    return 0


def _wait_for_build(build_id: str) -> int:
    terminal = {"SUCCESS", "FAILURE", "CANCELLED", "EXPIRED", "INTERNAL_ERROR", "TIMEOUT"}
    while True:
        completed = subprocess.run(
            [
                _gcloud(),
                "builds",
                "describe",
                build_id,
                f"--project={PROJECT}",
                "--format=value(status)",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        status = completed.stdout.strip()
        if status == "SUCCESS":
            print(f"cloud build {build_id} succeeded")
            return 0
        if status in terminal:
            print(f"cloud build {build_id} ended with {status}", file=sys.stderr)
            if completed.stderr:
                print(completed.stderr, file=sys.stderr)
            return 1
        time.sleep(5)


def _cloud_build_submit(*, config: str, substitutions: str) -> int:
    completed = subprocess.run(
        [
            _gcloud(),
            "builds",
            "submit",
            ".",
            f"--config={config}",
            f"--substitutions={substitutions}",
            f"--project={PROJECT}",
            "--async",
            "--format=value(id)",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        print(completed.stderr or completed.stdout, file=sys.stderr)
        return completed.returncode
    build_id = completed.stdout.strip()
    if not build_id:
        print("cloud build did not return a build id", file=sys.stderr)
        return 1
    print(f"cloud build {build_id} started")
    return _wait_for_build(build_id)


def _build_backend_image() -> int:
    return _cloud_build_submit(
        config="infra/gcp/cloudbuild.yaml",
        substitutions=f"_IMAGE={BACKEND_IMAGE}",
    )


def _build_frontend_image(api_url: str) -> int:
    return _cloud_build_submit(
        config="infra/gcp/cloudbuild-frontend.yaml",
        substitutions=f"_IMAGE={FRONTEND_IMAGE},_API_URL={api_url}",
    )


def _deploy_api(shared_env: list[str]) -> int:
    env = [*shared_env, "WORKFLOW_SUBSCRIBER=pubsub", "PUBSUB_HANDLE=false"]
    env_file = _write_env_file(env, "cloudrun-api-env.yaml")
    return _run(
        [
            "gcloud",
            "run",
            "deploy",
            API_SERVICE,
            f"--image={BACKEND_IMAGE}",
            f"--region={REGION}",
            f"--project={PROJECT}",
            f"--service-account={RUNTIME_SA}",
            "--allow-unauthenticated",
            "--port=8080",
            "--memory=1Gi",
            "--timeout=300",
            "--min-instances=0",
            "--max-instances=3",
            f"--env-vars-file={env_file}",
            "--set-secrets",
            DEPLOY_SECRETS,
        ]
    )


def _deploy_worker(shared_env: list[str]) -> int:
    env = [*shared_env, "WORKFLOW_SUBSCRIBER=pubsub", "PUBSUB_HANDLE=true"]
    env_file = _write_env_file(env, "cloudrun-worker-env.yaml")
    return _run(
        [
            "gcloud",
            "run",
            "deploy",
            WORKER_SERVICE,
            f"--image={BACKEND_IMAGE}",
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
            f"--env-vars-file={env_file}",
            "--set-secrets",
            DEPLOY_SECRETS,
        ]
    )


def _deploy_frontend() -> int:
    return _run(
        [
            "gcloud",
            "run",
            "deploy",
            UI_SERVICE,
            f"--image={FRONTEND_IMAGE}",
            f"--region={REGION}",
            f"--project={PROJECT}",
            "--allow-unauthenticated",
            "--port=8080",
            "--memory=512Mi",
            "--timeout=300",
            "--min-instances=0",
            "--max-instances=2",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Deploy EIR to Cloud Run")
    parser.add_argument(
        "--services-only",
        action="store_true",
        help="Skip artifact registry and secret bootstrap. IAM roles still applied. Use in CI.",
    )
    args = parser.parse_args()

    project_number = _project_number()
    api_url = _service_url(API_SERVICE, project_number)
    shared_env = _shared_env(project_number)

    steps: list = [_ensure_runtime_service_account]
    if not args.services_only:
        steps.extend([_ensure_artifact_registry, _ensure_secret, _ensure_scheduler_secret])
    steps.extend(
        [
            _build_backend_image,
            lambda: _deploy_api(shared_env),
            lambda: _deploy_worker(shared_env),
            lambda: _build_frontend_image(api_url),
            _deploy_frontend,
        ]
    )

    for step in steps:
        if step() != 0:
            return 1

    print("deploy finished")
    print(f"API: {api_url}")
    print(f"UI:  {_service_url(UI_SERVICE, project_number)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
