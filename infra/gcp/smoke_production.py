"""Production smoke checks using synthetic fixtures only."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request

DEFAULT_API = "https://eir-api-658898892127.us-central1.run.app"


def _get(url: str, *, token: str = "") -> dict:
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _post(url: str, payload: dict, *, token: str = "") -> dict:
    body = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=60) as response:
        raw = response.read().decode("utf-8")
        return json.loads(raw) if raw else {}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run EIR production smoke checks")
    parser.add_argument("--api-url", default=DEFAULT_API)
    args = parser.parse_args()
    api = args.api_url.rstrip("/")
    failures: list[str] = []

    try:
        health = _get(f"{api}/health")
    except urllib.error.URLError as exc:
        print(f"FAIL health: {exc}", file=sys.stderr)
        return 1

    adapters = health.get("adapters") or {}
    for key, expected in (
        ("fhir_mode", "gcp"),
        ("episode_store", "firestore"),
        ("event_bus", "pubsub"),
        ("adk_runner_mode", "adk"),
    ):
        actual = adapters.get(key)
        if actual != expected:
            failures.append(f"{key}={actual!r} expected {expected!r}")

    if adapters.get("managed_model_armor_available") is not True:
        failures.append("managed_model_armor_available is false")

    otel = adapters.get("otel") or {}
    if otel.get("capture_message_content_in_spans") is not False:
        failures.append("ADK message content capture must be disabled")

    try:
        login = _post(
            f"{api}/api/v1/auth/login",
            {"username": "alex", "password": "demo-alex"},
        )
        token = login.get("token") or ""
        if not token:
            failures.append("demo patient login missing token")
    except urllib.error.URLError as exc:
        failures.append(f"demo login failed: {exc}")
        token = ""

    if token:
        try:
            appointments = _get(f"{api}/api/v1/appointments", token=token)
            if not isinstance(appointments, list):
                failures.append("appointments response not a list")
        except urllib.error.URLError as exc:
            failures.append(f"appointments read failed: {exc}")

        try:
            session = _post(f"{api}/api/v1/access/sessions", {"channel": "web"}, token=token)
            session_id = session.get("id")
            if not session_id:
                failures.append("access session create missing id")
            else:
                loaded = _get(f"{api}/api/v1/access/sessions/{session_id}", token=token)
                if loaded.get("id") != session_id:
                    failures.append("access session reload mismatch")
        except urllib.error.URLError as exc:
            failures.append(f"access session failed: {exc}")

        try:
            slots = _get(
                f"{api}/api/v1/appointments/availability?specialty=Cardiology&limit=3",
                token=token,
            )
            if not isinstance(slots, list) or not slots:
                failures.append("cardiology availability empty")
            else:
                slot_id = str(slots[0]["id"])
                booked = _post(
                    f"{api}/api/v1/appointments",
                    {"slot_id": slot_id},
                    token=token,
                )
                appointment_id = booked.get("id")
                if not appointment_id:
                    failures.append("book appointment missing id")
                else:
                    alt = next(
                        (item for item in slots[1:] if item.get("id") != slot_id),
                        None,
                    )
                    if alt:
                        _post(
                            f"{api}/api/v1/appointments/{appointment_id}/reschedule",
                            {"slot_id": alt["id"]},
                            token=token,
                        )
                    cancelled = _post(
                        f"{api}/api/v1/appointments/{appointment_id}/cancel",
                        {"reason": "synthetic-smoke", "confirmed": True},
                        token=token,
                    )
                    if cancelled.get("status") not in {"cancelled", "canceled"}:
                        failures.append(f"cancel status={cancelled.get('status')!r}")
        except urllib.error.HTTPError as exc:
            failures.append(f"appointment mutation failed: {exc.code} {exc.read()[:200]!r}")
        except urllib.error.URLError as exc:
            failures.append(f"appointment mutation failed: {exc}")

        try:
            bootstrap = _post(
                f"{api}/api/v1/demo/bootstrap",
                {"patient_id": "patient-synthetic-001", "fast_forward": False},
            )
            if not bootstrap.get("episode_id"):
                failures.append("recovery bootstrap missing episode_id")
        except urllib.error.URLError as exc:
            failures.append(f"recovery bootstrap failed: {exc}")

    if failures:
        for item in failures:
            print(f"FAIL {item}", file=sys.stderr)
        return 1

    print(json.dumps({"status": "ok", "api": api, "checks": "production smoke passed"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
