"""Idempotent in-place Agent Gateway attach. Never recreates the live ReasoningEngine."""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime

import google.auth
import google.auth.transport.requests

PROJECT = "eir-ata"
PROJECT_NUMBER = "658898892127"
LOCATION = "us-central1"
ENGINE_ID = "3041998479602745344"
GATEWAY_ID = "eir-agent-egress"
RESOURCE = f"projects/{PROJECT_NUMBER}/locations/{LOCATION}/reasoningEngines/{ENGINE_ID}"
GATEWAY = f"projects/{PROJECT}/locations/{LOCATION}/agentGateways/{GATEWAY_ID}"
CUTOFF = datetime.fromisoformat("2026-04-29T00:00:00+00:00")


def _creds():
    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds.refresh(google.auth.transport.requests.Request())
    return creds


def _request(method: str, url: str, body: dict | None = None) -> dict:
    creds = _creds()
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {creds.token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:800]
        raise RuntimeError(f"{method} {url} failed HTTP {exc.code}: {detail}") from exc
    return json.loads(payload or "{}")


def describe_engine() -> dict:
    url = f"https://{LOCATION}-aiplatform.googleapis.com/v1/{RESOURCE}"
    return _request("GET", url)


def describe_gateway() -> dict:
    url = (
        "https://networkservices.googleapis.com/v1/"
        f"projects/{PROJECT}/locations/{LOCATION}/agentGateways/{GATEWAY_ID}"
    )
    return _request("GET", url)


def _bound_gateway(engine: dict) -> str:
    spec = ((engine.get("spec") or {}).get("deploymentSpec") or {})
    return (
        ((spec.get("agentGatewayConfig") or {}).get("agentToAnywhereConfig") or {}).get(
            "agentGateway"
        )
        or ""
    )


def _wait_operation(operation: dict) -> dict:
    name = operation.get("name") or ""
    if "/operations/" not in name:
        return operation
    url = f"https://{LOCATION}-aiplatform.googleapis.com/v1beta1/{name}"
    for _ in range(36):
        current = _request("GET", url)
        if current.get("done"):
            if current.get("error"):
                raise RuntimeError(f"Gateway bind operation failed: {current['error']}")
            return current
        time.sleep(10)
    raise RuntimeError(f"Gateway bind operation timed out: {name}")


def attach() -> dict:
    engine = describe_engine()
    create_time = engine.get("createTime") or ""
    if create_time:
        created = datetime.fromisoformat(create_time.replace("Z", "+00:00"))
        if created < CUTOFF:
            raise RuntimeError(
                f"engine created {create_time} is before the 2026-04-29 "
                "Gateway cutoff; refuse replace"
            )
    current = _bound_gateway(engine)
    if current and GATEWAY_ID not in current:
        raise RuntimeError(f"engine already bound to a different gateway: {current}")
    if GATEWAY_ID in current:
        return {
            "status": "already-attached",
            "resource": engine.get("name"),
            "gateway": current,
            "create_time": create_time,
            "same_engine": True,
            "identity": ((engine.get("spec") or {}).get("effectiveIdentity")),
        }
    body = {
        "spec": {
            "deploymentSpec": {
                "agentGatewayConfig": {
                    "agentToAnywhereConfig": {"agentGateway": GATEWAY}
                }
            }
        }
    }
    url = (
        f"https://{LOCATION}-aiplatform.googleapis.com/v1beta1/{RESOURCE}"
        "?updateMask=spec.deploymentSpec.agentGatewayConfig"
    )
    operation = _request("PATCH", url, body)
    _wait_operation(operation)
    updated = describe_engine()
    bound = _bound_gateway(updated)
    if GATEWAY_ID not in bound:
        raise RuntimeError("Gateway bind returned null agentGatewayConfig; Runtime did not attach")
    resource_name = updated.get("name") or RESOURCE
    return {
        "status": "attached",
        "resource": resource_name,
        "gateway": bound,
        "create_time": create_time,
        "same_engine": resource_name.endswith(ENGINE_ID),
        "identity": ((updated.get("spec") or {}).get("effectiveIdentity")),
    }


def rebuild_pickle_with_gateway() -> dict:
    """In-place package update so the managed image trusts Agent Gateway CA."""
    import os
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent))

    from deploy_patient_access import (
        STAGING_BUCKET,
        _client,
        _env_vars,
        _memory_bank_config,
        _requirements,
        _stage_source,
        ensure_memory_bank_config,
    )
    from eir_agents.access.runtime_app import build_adk_app
    from vertexai import types

    source = _stage_source()
    app = build_adk_app()
    client = _client()
    previous_cwd = os.getcwd()
    os.chdir(source)
    try:
        remote = client.agent_engines.update(
            name=RESOURCE,
            agent=app,
            config={
                "identity_type": types.IdentityType.AGENT_IDENTITY,
                "python_version": "3.12",
                "agent_framework": "google-adk",
                "env_vars": _env_vars(),
                "requirements": _requirements(),
                "extra_packages": ["eir_agents", "eir_shared"],
                "staging_bucket": STAGING_BUCKET,
                "context_spec": {"memory_bank_config": _memory_bank_config()},
                "agent_gateway_config": {
                    "agent_to_anywhere_config": {"agent_gateway": GATEWAY}
                },
            },
        )
    finally:
        os.chdir(previous_cwd)
    updated = describe_engine()
    bound = _bound_gateway(updated)
    if GATEWAY_ID not in bound:
        raise RuntimeError("in-place update did not keep Agent Gateway binding")
    ensure_memory_bank_config(RESOURCE)
    spec = updated.get("spec") or {}
    return {
        "status": "rebuilt-pickle-with-gateway",
        "resource": updated.get("name") or RESOURCE,
        "gateway": bound,
        "same_engine": True,
        "identity": spec.get("effectiveIdentity"),
        "remote": getattr(remote, "name", None),
    }


def main() -> int:
    rebuild = "--rebuild-pickle" in sys.argv
    try:
        gateway = describe_gateway()
        result = rebuild_pickle_with_gateway() if rebuild else attach()
    except Exception as exc:
        print(json.dumps({"status": "fail", "error": str(exc)}), file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "status": "ok",
                **result,
                "gateway_resource": gateway.get("name"),
                "governed_access_path": (
                    (gateway.get("googleManaged") or {}).get("governedAccessPath")
                ),
            },
            default=str,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
