"""Idempotent Patient Access Agent Runtime deploy. Uses ADC. Never prints tokens."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

from eir_agents.access.constants import DEFAULT_API_BASE_URL, GEMINI_MODEL, RUNTIME_DISPLAY_NAME
from eir_agents.access.runtime_app import (
    ENTRYPOINT_MODULE,
    ENTRYPOINT_OBJECT,
    IDENTITY_TYPE,
    build_adk_app,
)

PROJECT = "eir-ata"
PROJECT_NUMBER = "658898892127"
LOCATION = "us-central1"
STAGING_BUCKET = f"gs://eir-ata-agent-runtime-{PROJECT_NUMBER}"
REPO_ROOT = Path(__file__).resolve().parents[3]
AGENTS_ROOT = REPO_ROOT / "agents"
SHARED_ROOT = REPO_ROOT / "shared"
REQUIREMENTS_FILE = Path(__file__).resolve().parent / "requirements-runtime.txt"
COLLECTION = "eir_platform_verification"
DOC_ID = "managed"
MEMORY_MODEL = f"projects/{PROJECT}/locations/global/publishers/google/models/{GEMINI_MODEL}"
EMBEDDING_MODEL = (
    f"projects/{PROJECT}/locations/{LOCATION}/publishers/google/models/text-embedding-005"
)


def _client():
    import vertexai

    return vertexai.Client(
        project=PROJECT,
        location=LOCATION,
        http_options={"api_version": "v1beta1"},
    )


def _requirements() -> list[str]:
    return [
        line.strip()
        for line in REQUIREMENTS_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def _stage_source() -> Path:
    dest = Path(__file__).resolve().parent / ".runtime_src"
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache", "tests")
    shutil.copytree(AGENTS_ROOT / "eir_agents", dest / "eir_agents", ignore=ignore)
    shutil.copytree(SHARED_ROOT / "eir_shared", dest / "eir_shared", ignore=ignore)
    (dest / "setup.py").write_text(
        "from setuptools import find_packages, setup\n\n"
        "setup(\n"
        "    name='eir-patient-access-runtime',\n"
        "    version='0.1.0',\n"
        "    packages=find_packages(),\n"
        ")\n",
        encoding="utf-8",
    )
    requirements = REQUIREMENTS_FILE.read_text(encoding="utf-8").rstrip() + "\n.\n"
    (dest / "requirements.txt").write_text(requirements, encoding="utf-8")
    return dest


def _class_methods(app) -> list[dict]:
    from vertexai._genai import _agent_engines_utils

    operations = _agent_engines_utils._get_registered_operations(agent=app)
    specs = _agent_engines_utils._generate_class_methods_spec_or_raise(
        agent=app, operations=operations
    )
    return [_agent_engines_utils._to_dict(item) for item in specs]


def _memory_bank_config() -> dict:
    return {
        "generation_config": {"model": MEMORY_MODEL},
        "similarity_search_config": {"embedding_model": EMBEDDING_MODEL},
        "ttl_config": {"default_ttl": f"{30 * 24 * 60 * 60}s"},
        "customization_configs": [
            {
                "memory_topics": [
                    {"managed_memory_topic": {"managed_topic_enum": "USER_PREFERENCES"}},
                    {
                        "managed_memory_topic": {
                            "managed_topic_enum": "EXPLICIT_INSTRUCTIONS"
                        }
                    },
                ]
            }
        ],
    }


def _env_vars() -> dict[str, str]:
    return {
        "EIR_API_BASE_URL": os.environ.get("EIR_API_BASE_URL", DEFAULT_API_BASE_URL),
        "EIR_API_AUDIENCE": os.environ.get("EIR_API_AUDIENCE", DEFAULT_API_BASE_URL),
        "GEMINI_MODEL": GEMINI_MODEL,
        "GOOGLE_GENAI_USE_VERTEXAI": "TRUE",
        "ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS": "false",
        # Required to inject Agent Identity tokens into application headers.
        "GOOGLE_API_PREVENT_AGENT_TOKEN_SHARING_FOR_GCP_SERVICES": "false",
    }


def _resource_name(engine) -> str:
    resource = getattr(engine, "api_resource", engine)
    return getattr(resource, "name", None) or str(engine)


def _effective_identity(engine) -> str | None:
    resource = getattr(engine, "api_resource", engine)
    spec = getattr(resource, "spec", None)
    if spec is None:
        return None
    identity = getattr(spec, "effective_identity", None) or getattr(
        spec, "effectiveIdentity", None
    )
    return str(identity) if identity else None


def _has_agent_code(engine) -> bool:
    resource = getattr(engine, "api_resource", engine)
    spec = getattr(resource, "spec", None)
    if spec is None:
        return False
    package = getattr(spec, "package_spec", None) or getattr(spec, "packageSpec", None)
    source = getattr(spec, "source_code_spec", None) or getattr(spec, "sourceCodeSpec", None)
    pickle_uri = getattr(package, "pickle_object_gcs_uri", None) if package else None
    return bool(pickle_uri or source)


def _delete_engine(client, engine) -> None:
    name = _resource_name(engine)
    try:
        client.agent_engines.delete(name=name, force=True)
    except TypeError:
        client.agent_engines.delete(name=name)


def _find_all(client) -> list:
    found = []
    for engine in client.agent_engines.list():
        resource = getattr(engine, "api_resource", engine)
        display = getattr(resource, "display_name", "") or getattr(engine, "display_name", "")
        if display == RUNTIME_DISPLAY_NAME:
            found.append(engine)
    return found


def _find_existing(client) -> object | None:
    items = _find_all(client)
    return items[0] if items else None


def _gcloud() -> str:
    found = shutil.which("gcloud.cmd") or shutil.which("gcloud")
    if not found:
        raise FileNotFoundError("gcloud not found on PATH")
    return found


def _adc_account() -> str:
    completed = subprocess.run(
        [_gcloud(), "config", "get-value", "account"],
        check=False,
        capture_output=True,
        text=True,
    )
    return (completed.stdout or "").strip()


def bootstrap_allowlist(extra: list[str] | None = None) -> list[str]:
    from google.cloud import firestore

    principals = []
    account = _adc_account()
    if account:
        principals.append(account)
    runtime_sa = "eir-runtime@eir-ata.iam.gserviceaccount.com"
    if runtime_sa not in principals:
        principals.append(runtime_sa)
    for item in extra or []:
        if item and item not in principals:
            principals.append(item)
    client = firestore.Client(project=PROJECT)
    snapshot = client.collection(COLLECTION).document(DOC_ID).get()
    existing = []
    if snapshot.exists:
        existing = list((snapshot.to_dict() or {}).get("allowed_principals") or [])
    merged = list(dict.fromkeys([*existing, *principals]))
    client.collection(COLLECTION).document(DOC_ID).set(
        {"allowed_principals": merged},
        merge=True,
    )
    return merged


def deploy(*, force_update: bool = False) -> dict:
    from vertexai import types

    client = _client()
    existing_all = _find_all(client)
    if existing_all and not force_update:
        existing = existing_all[0]
        if _has_agent_code(existing):
            return {
                "status": "exists",
                "resource": _resource_name(existing),
                "display_name": RUNTIME_DISPLAY_NAME,
                "identity_type": IDENTITY_TYPE,
                "effective_identity": _effective_identity(existing),
            }
    for engine in existing_all:
        _delete_engine(client, engine)
    existing = None

    source = _stage_source()
    app = build_adk_app()
    config = {
        "display_name": RUNTIME_DISPLAY_NAME,
        "description": "EIR Patient Access ADK agent on Agent Runtime",
        "identity_type": types.IdentityType.AGENT_IDENTITY,
        "python_version": "3.12",
        "agent_framework": "google-adk",
        "env_vars": _env_vars(),
        "context_spec": {"memory_bank_config": _memory_bank_config()},
    }
    previous_cwd = os.getcwd()
    os.chdir(source)
    try:
        try:
            payload = {
                **config,
                "source_packages": ["."],
                "entrypoint_module": ENTRYPOINT_MODULE,
                "entrypoint_object": ENTRYPOINT_OBJECT,
                "requirements_file": "requirements.txt",
                "class_methods": _class_methods(app),
            }
            remote = client.agent_engines.create(config=payload)
            status = "created-source"
        except Exception as source_error:
            payload = {
                **config,
                "requirements": _requirements(),
                "extra_packages": ["eir_agents", "eir_shared"],
                "staging_bucket": STAGING_BUCKET,
            }
            remote = client.agent_engines.create(agent=app, config=payload)
            status = f"created-pickle:{type(source_error).__name__}:{str(source_error)[:180]}"
    finally:
        os.chdir(previous_cwd)
    identity = _effective_identity(remote)
    if identity:
        bootstrap_allowlist([identity])
    ensure_memory_bank_config(_resource_name(remote))
    return {
        "status": status,
        "resource": _resource_name(remote),
        "display_name": RUNTIME_DISPLAY_NAME,
        "identity_type": IDENTITY_TYPE,
        "effective_identity": identity,
        "entrypoint_module": ENTRYPOINT_MODULE,
    }


def ensure_memory_bank_config(resource_name: str) -> None:
    import json
    import urllib.request

    import google.auth
    import google.auth.transport.requests

    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds.refresh(google.auth.transport.requests.Request())
    body = {
        "contextSpec": {
            "memoryBankConfig": {
                "generationConfig": {"model": MEMORY_MODEL},
                "similaritySearchConfig": {"embeddingModel": EMBEDDING_MODEL},
                "ttlConfig": {"defaultTtl": f"{30 * 24 * 60 * 60}s"},
                "customizationConfigs": [
                    {
                        "memoryTopics": [
                            {
                                "managedMemoryTopic": {
                                    "managedTopicEnum": "USER_PREFERENCES"
                                }
                            },
                            {
                                "managedMemoryTopic": {
                                    "managedTopicEnum": "EXPLICIT_INSTRUCTIONS"
                                }
                            },
                        ]
                    }
                ],
            }
        }
    }
    url = (
        "https://us-central1-aiplatform.googleapis.com/v1beta1/"
        f"{resource_name}?updateMask=contextSpec"
    )
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        method="PATCH",
        headers={
            "Authorization": f"Bearer {creds.token}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        response.read()


def _member(principal: str) -> str:
    value = principal.strip()
    if value.startswith(("principal://", "user:", "serviceAccount:")):
        return value
    if value.startswith("agents.global."):
        return f"principal://{value}"
    if "@" in value:
        return f"user:{value}"
    return value


def grant_tool_boundary(principal: str) -> None:
    subprocess.run(
        [
            _gcloud(),
            "run",
            "services",
            "add-iam-policy-binding",
            "eir-api",
            f"--project={PROJECT}",
            f"--region={LOCATION}",
            f"--member={_member(principal)}",
            "--role=roles/run.invoker",
        ],
        check=False,
        capture_output=True,
        text=True,
    )


def main() -> int:
    import sys

    force = "--update" in sys.argv
    if "--bootstrap-allowlist" in sys.argv:
        principals = bootstrap_allowlist()
        print(json.dumps({"status": "allowlist", "count": len(principals)}))
        return 0
    result = deploy(force_update=force)
    identity = result.get("effective_identity")
    if identity:
        grant_tool_boundary(str(identity))
    print(json.dumps(result, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
