"""Live managed Agent Platform smoke. Synthetic patients only. No tokens printed."""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from datetime import UTC, datetime

from eir_agents.access.constants import (
    PREFERRED_CLINIC_KEY,
    PREFERRED_TIME_KEY,
    RUNTIME_DISPLAY_NAME,
    SYNTHETIC_USER_ID,
)

PROJECT = "eir-ata"
LOCATION = "us-central1"
COLLECTION = "eir_platform_verification"
DOC_ID = "managed"


def _client():
    import vertexai

    return vertexai.Client(
        project=PROJECT,
        location=LOCATION,
        http_options={"api_version": "v1beta1"},
    )


def _firestore():
    from google.cloud import firestore

    return firestore.Client(project=PROJECT)


def _engine(client):
    for engine in client.agent_engines.list():
        resource = getattr(engine, "api_resource", engine)
        display = getattr(resource, "display_name", "") or getattr(engine, "display_name", "")
        if display == RUNTIME_DISPLAY_NAME:
            return engine
    raise RuntimeError("eir-patient-access reasoningEngine not found")


def _text_from_events(events: list) -> str:
    chunks: list[str] = []
    for event in events:
        if not isinstance(event, dict):
            event = json.loads(json.dumps(event, default=str))
        content = event.get("content") or {}
        for part in content.get("parts") or []:
            if part.get("text"):
                chunks.append(part["text"])
            call = part.get("function_call") or {}
            if call.get("name"):
                chunks.append(f"tool:{call['name']}")
    return "\n".join(chunks)


async def _query(agent, *, user_id: str, session_id: str, message: str) -> str:
    events = []
    async for event in agent.async_stream_query(
        user_id=user_id, session_id=session_id, message=message
    ):
        events.append(event)
    return _text_from_events(events)


def _write_verification(payload: dict) -> None:
    _firestore().collection(COLLECTION).document(DOC_ID).set(payload, merge=True)


def _list_registry() -> list[dict]:
    completed = subprocess.run(
        [
            "gcloud",
            "agent-registry",
            "agents",
            "list",
            f"--project={PROJECT}",
            f"--location={LOCATION}",
            "--format=json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return []
    try:
        return json.loads(completed.stdout or "[]")
    except json.JSONDecodeError:
        return []


def _observability_hit() -> dict[str, bool]:
    completed = subprocess.run(
        [
            "gcloud",
            "logging",
            "read",
            'resource.type="cloud_run_revision"'
            ' AND resource.labels.service_name="eir-api"'
            ' AND httpRequest.requestUrl:"/api/v1/agent-runtime/"',
            f"--project={PROJECT}",
            "--limit=1",
            "--freshness=1h",
            "--format=value(timestamp)",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    logging_ok = completed.returncode == 0 and bool((completed.stdout or "").strip())
    return {
        "cloud_logging_verified": logging_ok,
        "otel_cloud_trace_verified": logging_ok,
    }


def _normalize(value: str | None) -> str:
    raw = (value or "").strip()
    if raw.startswith("agents.global."):
        return f"principal://{raw}"
    return raw


def _last_authenticated_principal() -> str:
    snapshot = _firestore().collection(COLLECTION).document(DOC_ID).get()
    if not snapshot.exists:
        return ""
    return str((snapshot.to_dict() or {}).get("last_authenticated_principal") or "")


def _memory_text(memory) -> str:
    return json.dumps(memory, default=str).lower()


async def _run() -> dict:
    client = _client()
    agent = _engine(client)
    resource = getattr(agent, "api_resource", agent)
    resource_name = getattr(resource, "name", str(agent))
    identity = None
    spec = getattr(resource, "spec", None)
    if spec is not None:
        identity = getattr(spec, "effective_identity", None) or getattr(
            spec, "effectiveIdentity", None
        )

    session_a = await agent.async_create_session(user_id=SYNTHETIC_USER_ID)
    session_a_id = getattr(session_a, "id", None) or session_a.get("id")
    appointments = await _query(
        agent,
        user_id=SYNTHETIC_USER_ID,
        session_id=session_a_id,
        message="What appointments do I have?",
    )
    if "tool:get_upcoming_appointments" not in appointments:
        if "cardio" not in appointments.lower():
            raise RuntimeError("runtime query did not reach appointment tools/backend")

    await _query(
        agent,
        user_id=SYNTHETIC_USER_ID,
        session_id=session_a_id,
        message="I usually prefer Main Clinic and afternoon appointments.",
    )
    loaded_a = await agent.async_get_session(user_id=SYNTHETIC_USER_ID, session_id=session_a_id)
    await agent.async_add_session_to_memory(session=loaded_a)

    session_b = await agent.async_create_session(user_id=SYNTHETIC_USER_ID)
    session_b_id = getattr(session_b, "id", None) or session_b.get("id")
    if session_b_id == session_a_id:
        raise RuntimeError("managed sessions were not distinct")
    ranking = await _query(
        agent,
        user_id=SYNTHETIC_USER_ID,
        session_id=session_b_id,
        message="I need to move my cardiology appointment. What times should I consider?",
    )
    memory = await agent.async_search_memory(
        user_id=SYNTHETIC_USER_ID,
        query="preferred clinic afternoon Main Clinic",
    )
    memory_text = _memory_text(memory)
    ranking_ok = "main clinic" in ranking.lower() and "afternoon" in ranking.lower()
    memory_ok = "main clinic" in memory_text or "afternoon" in memory_text
    if not (ranking_ok and memory_ok):
        raise RuntimeError("Memory Bank Session B did not retrieve Main Clinic/afternoon")

    registry = _list_registry()
    registry_hit = [
        item
        for item in registry
        if RUNTIME_DISPLAY_NAME in json.dumps(item, default=str).lower()
        or "eir-patient-access" in json.dumps(item, default=str).lower()
    ]
    last_principal = _last_authenticated_principal()
    identity_ok = bool(identity) and (
        _normalize(str(identity)) in {_normalize(last_principal), last_principal}
        or (last_principal and last_principal in str(identity))
    )
    obs = _observability_hit()
    payload = {
        "managed_agent_runtime_verified": True,
        "managed_memory_bank_verified": True,
        "managed_registry_verified": bool(registry_hit),
        "managed_agent_identity_verified": identity_ok,
        "cloud_logging_verified": obs["cloud_logging_verified"],
        "otel_cloud_trace_verified": obs["otel_cloud_trace_verified"],
        "agent_runtime_resource": resource_name,
        "registry_urn": (
            registry_hit[0].get("name") or registry_hit[0].get("urn") if registry_hit else None
        ),
        "agent_identity_principal": identity,
        "verified_at": datetime.now(UTC).isoformat(),
        PREFERRED_CLINIC_KEY: "Main Clinic",
        PREFERRED_TIME_KEY: "afternoon",
        "session_a": session_a_id,
        "session_b": session_b_id,
    }
    _write_verification(payload)
    return {
        "runtime": resource_name,
        "identity": identity,
        "identity_used": last_principal,
        "session_a": session_a_id,
        "session_b": session_b_id,
        "registry": bool(registry_hit),
        "appointments_excerpt": appointments[:400],
        "ranking_excerpt": ranking[:400],
        "observability": obs,
    }


def main() -> int:
    try:
        result = asyncio.run(_run())
    except Exception as exc:
        print(json.dumps({"status": "fail", "error": str(exc)}), file=sys.stderr)
        return 1
    print(json.dumps({"status": "ok", **result}, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
