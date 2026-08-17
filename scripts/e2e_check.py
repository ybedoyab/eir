"""Live E2E check against a running API (default http://localhost:8000)."""

from __future__ import annotations

import json
import os
import sys
import time

import httpx

BASE = os.getenv("EIR_API_URL", "http://localhost:8000")
POLL_TIMEOUT = float(os.getenv("E2E_POLL_TIMEOUT", "90"))


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def ok(message: str) -> None:
    print(f"OK: {message}")


def purge_pubsub_backlog() -> None:
    from datetime import UTC, datetime

    from eir_shared.env import load_root_env

    load_root_env()
    from app.core.config import settings
    from google.cloud import pubsub_v1
    from google.protobuf import timestamp_pb2

    subscriber = pubsub_v1.SubscriberClient()
    path = subscriber.subscription_path(
        settings.google_cloud_project,
        settings.pubsub_subscription,
    )
    now = timestamp_pb2.Timestamp()
    now.FromDatetime(datetime.now(UTC))
    subscriber.seek(request={"subscription": path, "time": now})
    ok(f"seek subscription {settings.pubsub_subscription} to now")


def wait_for_episode(
    client: httpx.Client,
    episode_id: str,
    *,
    status: str | None = None,
    risk_level: str | None = None,
) -> dict:
    deadline = time.time() + POLL_TIMEOUT
    last: dict = {}
    while time.time() < deadline:
        response = client.get(f"/api/v1/recovery/{episode_id}")
        if response.status_code != 200:
            time.sleep(1)
            continue
        last = response.json()
        if status is not None and last.get("status") == status:
            if risk_level is None or last.get("risk_level") == risk_level:
                return last
        elif status is None:
            return last
        time.sleep(1)
    fail(
        f"timeout waiting for episode {episode_id} status={status} risk={risk_level}; last={last}"
    )
    return last


def main() -> int:
    split_mode = os.getenv("E2E_SPLIT", "").lower() in {"1", "true", "yes"}
    if split_mode:
        purge_pubsub_backlog()
        time.sleep(2)
    with httpx.Client(base_url=BASE, timeout=120.0) as client:
        health = client.get("/health")
        if health.status_code != 200:
            fail(f"/health returned {health.status_code}")
        body = health.json()
        adapters = body.get("adapters", {})
        ok(f"health adapters={json.dumps(adapters)}")
        if split_mode:
            if adapters.get("workflow_subscriber") != "pubsub":
                fail("split mode expects workflow_subscriber=pubsub on API")
            if adapters.get("pubsub_handle") is not False:
                fail("API must not handle Pub/Sub in split mode")
        if adapters.get("episode_store") not in {"firestore", "file", "memory"}:
            fail(f"unexpected episode_store: {adapters}")

        created = client.post(
            "/api/v1/recovery",
            json={"patient_id": "patient-synthetic-001"},
        )
        if created.status_code != 201:
            fail(f"create recovery: {created.status_code} {created.text}")
        episode_id = created.json()["id"]
        ok(f"created episode {episode_id}")

        follow_up = client.post(f"/api/v1/recovery/{episode_id}/follow-up")
        if follow_up.status_code != 200:
            fail(f"follow-up: {follow_up.status_code} {follow_up.text}")
        ok("follow-up triggered")

        wait_for_episode(
            client,
            episode_id,
            status="WAITING",
            risk_level="LOW",
        )
        ok("low-risk patient reached WAITING")

        events = client.get(f"/api/v1/recovery/{episode_id}/events").json()
        types = [item["event_type"] for item in events]
        for expected in ("RecoveryEpisodeStarted", "FollowUpDue", "PatientResponded"):
            if expected not in types:
                fail(f"missing event {expected} in {types}")
        ok(f"events present: {types}")

        created2 = client.post(
            "/api/v1/recovery",
            json={"patient_id": "patient-synthetic-002"},
        )
        episode_id2 = created2.json()["id"]
        client.post(f"/api/v1/recovery/{episode_id2}/follow-up")
        wait_for_episode(client, episode_id2, status="ESCALATED", risk_level="HIGH")
        ok("high-risk patient escalated")

        reviews = client.get("/api/v1/reviews").json()
        pending = [item for item in reviews if item["episode_id"] == episode_id2]
        if not pending:
            fail("no pending review for escalated episode")
        review_id = pending[0]["id"]
        resolved = client.post(
            f"/api/v1/reviews/{review_id}/resolve",
            json={"note": "e2e clinician review"},
        )
        if resolved.status_code != 200:
            fail(f"resolve review: {resolved.status_code} {resolved.text}")
        wait_for_episode(client, episode_id2, status="ACTIVE")
        ok("human review resolved and episode resumed")

        traces = client.get("/api/v1/traces").json()
        if not any(item["episode_id"] == episode_id for item in traces):
            if split_mode:
                deadline = time.time() + 15
                while time.time() < deadline:
                    traces = client.get("/api/v1/traces").json()
                    if any(item["episode_id"] == episode_id for item in traces):
                        break
                    time.sleep(1)
            if not any(item["episode_id"] == episode_id for item in traces):
                fail("no workflow traces for episode")
        ok(f"traces recorded ({len(traces)} total)")

    print("E2E passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
