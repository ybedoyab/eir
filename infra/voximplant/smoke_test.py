"""Preflight and optional smoke for Voximplant outreach.

PSTN path (default) still requires Caller ID, destination, and --place-call.
User/preview path does not place PSTN and does not require phone secrets.

Never prints phone numbers, tokens, passwords, or credential JSON.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(ROOT / "backend"))
if str(ROOT / "infra" / "voximplant") not in sys.path:
    sys.path.insert(0, str(ROOT / "infra" / "voximplant"))

from app.integrations.voice.voximplant_api import VoximplantAPI, load_credentials  # noqa: E402
from app.integrations.voice.voximplant_custom import (  # noqa: E402
    PREVIEW_USERNAME,
    TRANSPORT_PSTN,
    TRANSPORT_USER,
    encode_script_custom_data,
    missing_pipeline_events,
)

from provision import (  # noqa: E402
    API_URL,
    CALLBACK_PATH,
    GCP_RUNTIME_SECRET,
    GOOGLE_PROJECT,
    PREVIEW_ENV,
    PREVIEW_USER,
    _gcloud_run,
    discover,
    route_price,
    verified_caller_ids,
)

UI_URL = "https://eir-ui-658898892127.us-central1.run.app"
WEB_SOFTPHONE_URL = "https://phone.voximplant.com"
VOICE_PREVIEW_URL = f"{UI_URL}/voice-preview"


def _load_env_file(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def _load_env() -> None:
    _load_env_file(ROOT / ".env")
    _load_env_file(ROOT / ".cursor" / "voximplant-runtime.env")
    _load_env_file(PREVIEW_ENV)


def _minute_price(groups: list[dict[str, Any]]) -> float | None:
    prices: list[float] = []
    for group in groups:
        for key in ("price", "num_price", "installation_price"):
            raw = group.get(key)
            if raw is None:
                continue
            try:
                prices.append(float(raw))
            except (TypeError, ValueError):
                continue
        nested = group.get("price_groups") or group.get("prices") or []
        if isinstance(nested, list):
            for item in nested:
                if not isinstance(item, dict):
                    continue
                raw = item.get("price") or item.get("num_price")
                if raw is None:
                    continue
                try:
                    prices.append(float(raw))
                except (TypeError, ValueError):
                    continue
    if not prices:
        return None
    return min(p for p in prices if p >= 0)


def _runtime_credentials_source() -> str:
    env = os.environ.get("VOXIMPLANT_RUNTIME_CREDENTIALS", "").strip()
    if env:
        return env
    local = ROOT / ".cursor" / "eir-runtime-caller.json"
    if local.is_file():
        return str(local)
    pulled = _gcloud_run(
        [
            "gcloud",
            "secrets",
            "versions",
            "access",
            "latest",
            f"--secret={GCP_RUNTIME_SECRET}",
            f"--project={GOOGLE_PROJECT}",
        ],
        check=False,
    )
    if pulled.returncode != 0 or not (pulled.stdout or "").strip():
        return ""
    local.parent.mkdir(parents=True, exist_ok=True)
    local.write_text(pulled.stdout.strip(), encoding="utf-8")
    return str(local)


def _rule_id(info: dict[str, Any]) -> str:
    env = os.environ.get("VOXIMPLANT_RULE_ID", "").strip()
    if env:
        return env
    for item in info.get("rules") or []:
        if item.get("name") == "eir-outbound" and item.get("id"):
            return str(item["id"])
    return ""


def preview_custom_data(*, episode_id: str, correlation_id: str) -> str:
    return encode_script_custom_data(
        episode_id=episode_id,
        correlation_id=correlation_id,
        display_name="Alex",
        transport=TRANSPORT_USER,
        destination_user=PREVIEW_USERNAME,
        destination="+15555550199",
        caller_id="+15555550100",
    )


def preflight(api: VoximplantAPI, *, transport: str) -> dict[str, Any]:
    info = discover(api)
    destination = os.environ.get("EIR_DEMO_PHONE_E164", "").strip()
    caller = os.environ.get("VOXIMPLANT_CALLER_ID_E164", "").strip()
    runtime = _runtime_credentials_source()
    if runtime:
        os.environ.setdefault("VOXIMPLANT_RUNTIME_CREDENTIALS", runtime)
    rule_id = _rule_id(info)
    if rule_id:
        os.environ.setdefault("VOXIMPLANT_RULE_ID", rule_id)
    per_minute = None
    estimated = None
    if transport == TRANSPORT_PSTN and destination:
        price_info = route_price(api, destination)
        per_minute = _minute_price(price_info.get("groups") or [])
        estimated = None if per_minute is None else round(per_minute * 2, 4)
    live = info.get("live_balance")
    try:
        balance = float(live) if live is not None else None
    except (TypeError, ValueError):
        balance = None
    users_ok = False
    if transport == TRANSPORT_USER:
        app_id = next(
            (
                item.get("id")
                for item in info.get("applications") or []
                if "eir-recovery" in str(item.get("name") or "")
            ),
            None,
        )
        params: dict[str, Any] = {"user_name": PREVIEW_USER}
        if app_id is not None:
            params["application_id"] = app_id
        users = api.call("GetUsers", **params)
        result = users.get("result") if "error" not in users else []
        if isinstance(result, list):
            users_ok = any(
                str(item.get("user_name") or "").split("@")[0] == PREVIEW_USER
                for item in result
                if isinstance(item, dict)
            )
        elif isinstance(result, dict):
            users_ok = str(result.get("user_name") or "").split("@")[0] == PREVIEW_USER
    return {
        "transport": transport,
        "balance": balance,
        "per_minute": per_minute,
        "estimated_two_minutes": estimated,
        "verified_caller_ids": len(verified_caller_ids(api)),
        "destination_configured": bool(destination),
        "caller_id_configured": bool(caller),
        "runtime_credentials_configured": bool(runtime),
        "rule_configured": bool(rule_id),
        "preview_user_configured": users_ok if transport == TRANSPORT_USER else True,
        "preview_env_present": PREVIEW_ENV.is_file(),
        "callback_url": API_URL + CALLBACK_PATH,
        "applications": info["applications"],
        "scenarios": info["scenarios"],
        "rules": info["rules"],
    }


def report(result: dict[str, Any]) -> list[str]:
    manuals: list[str] = []
    transport = result["transport"]
    print(f"Voice smoke preflight ({transport})")
    print(f"  live_balance: {result['balance']}")
    print("  pstn_calls_this_run: 0")
    if transport == TRANSPORT_PSTN:
        print(f"  route_price_per_minute: {result['per_minute']}")
        print(f"  estimated_2min: {result['estimated_two_minutes']}")
        print(f"  verified_caller_ids: {result['verified_caller_ids']}")
        print(f"  destination_secret: {'yes' if result['destination_configured'] else 'no'}")
        print(f"  caller_id_secret: {'yes' if result['caller_id_configured'] else 'no'}")
    else:
        print(f"  preview_user: {PREVIEW_USER}")
        print(f"  preview_user_exists: {'yes' if result['preview_user_configured'] else 'no'}")
        print(f"  preview_credentials_file: {PREVIEW_ENV.name}")
        print(f"  voice_preview: {VOICE_PREVIEW_URL}")
        print("  close hosted webphone: yes")
    print(f"  runtime_credentials: {'yes' if result['runtime_credentials_configured'] else 'no'}")
    print(f"  rule_id: {'yes' if result['rule_configured'] else 'no'}")
    if transport == TRANSPORT_USER:
        if not result["preview_user_configured"]:
            manuals.append(
                "Run uv run python infra/voximplant/provision.py to create eir-preview-user."
            )
        if not result["preview_env_present"]:
            manuals.append(
                "Preview login is stored at .voximplant-preview.env (gitignored). "
                "Rerun the provisioner if that file is missing."
            )
        if not result["runtime_credentials_configured"]:
            manuals.append("VOXIMPLANT_RUNTIME_CREDENTIALS is required to StartScenarios.")
        if not result["rule_configured"]:
            manuals.append("VOXIMPLANT_RULE_ID is missing. Rerun the provisioner.")
        return manuals
    if result["verified_caller_ids"] < 1:
        manuals.append(
            "Voximplant Control Panel -> Caller IDs -> verify a number by phone/code.\n"
            "Then set VOXIMPLANT_CALLER_ID_E164 and rerun provisioning."
        )
    if not result["destination_configured"]:
        manuals.append("Set EIR_DEMO_PHONE_E164 locally (not in Git) and store it in Secret Manager.")
    if result["balance"] is not None and result["estimated_two_minutes"] is not None:
        if result["balance"] < result["estimated_two_minutes"]:
            needed = max(5.0, result["estimated_two_minutes"] * 10)
            manuals.append(
                f"Current balance: {result['balance']}\n"
                f"Route price per minute: {result['per_minute']}\n"
                f"Estimated 2-minute smoke: {result['estimated_two_minutes']}\n"
                f"Minimum sensible top-up: ${needed:.2f}\n"
                "Do not place the call until the account is topped up. Never auto-pay."
            )
    return manuals


def _start_scenarios(*, custom: str) -> None:
    runtime_source = _runtime_credentials_source()
    if not runtime_source:
        raise RuntimeError("VOXIMPLANT_RUNTIME_CREDENTIALS is required to place a smoke call")
    rule_id = os.environ.get("VOXIMPLANT_RULE_ID", "").strip()
    if not rule_id:
        raise RuntimeError("VOXIMPLANT_RULE_ID is required")
    runtime = VoximplantAPI(load_credentials(runtime_source))
    response = runtime.call("StartScenarios", rule_id=int(rule_id), script_custom_data=custom)
    if "error" in response:
        raise RuntimeError(str((response.get("error") or {}).get("msg") or "start_scenarios_failed"))
    print("StartScenarios accepted (conversation continues asynchronously).")


def place_pstn_call() -> None:
    custom = encode_script_custom_data(
        episode_id="smoke",
        correlation_id="smoke-correlation",
        display_name="Alex",
        transport=TRANSPORT_PSTN,
    )
    _start_scenarios(custom=custom)


def _http_json(url: str, *, data: dict[str, Any] | None = None) -> Any:
    payload = None if data is None else json.dumps(data).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST" if data is not None else "GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        exc.read()
        raise RuntimeError(f"http_{exc.code}") from exc


def bootstrap_preview_episode() -> str:
    body = _http_json(f"{API_URL}/api/v1/demo/bootstrap", data={"fast_forward": False})
    episode_id = str(body.get("episode_id") or "")
    if not episode_id:
        raise RuntimeError("demo bootstrap did not return episode_id")
    return episode_id


def _event_types(episode_id: str) -> list[str]:
    body = _http_json(f"{API_URL}/api/v1/recovery/{episode_id}/events")
    items = body if isinstance(body, list) else body.get("events") or body.get("items") or []
    return [str(item.get("event_type") or "") for item in items if isinstance(item, dict)]


def wait_for_pipeline(episode_id: str, *, timeout_s: int = 180) -> tuple[list[str], list[str]]:
    deadline = time.time() + timeout_s
    types: list[str] = []
    while time.time() < deadline:
        types = _event_types(episode_id)
        missing = missing_pipeline_events(types)
        print(f"  events: {', '.join(t for t in types if t)}")
        if not missing:
            print("Preview pipeline complete.")
            return types, []
        time.sleep(5)
    missing = missing_pipeline_events(types)
    print("Preview pipeline incomplete. Missing expected events:")
    print("  " + ", ".join(missing) if missing else "  (unknown)")
    return types, missing


def place_user_call() -> str:
    episode_id = bootstrap_preview_episode()
    correlation_id = str(uuid4())
    custom = preview_custom_data(episode_id=episode_id, correlation_id=correlation_id)
    parsed = json.loads(custom)
    if "destination" in parsed or any(str(value).startswith("+") for value in parsed.values()):
        raise RuntimeError("preview custom data must not include phone numbers")
    print(f"Preview episode: {episode_id}")
    print(f"Recovery page: {UI_URL}/recovery/{episode_id}")
    print(f"Answer on {VOICE_PREVIEW_URL} (close phone.voximplant.com first).")
    _start_scenarios(custom=custom)
    return episode_id


def main() -> int:
    _load_env()
    parser = argparse.ArgumentParser(description="Voximplant EIR voice smoke preflight")
    parser.add_argument(
        "--transport",
        choices=(TRANSPORT_PSTN, "user", TRANSPORT_USER),
        default=TRANSPORT_PSTN,
        help="pstn (production) or user/voximplant_user (Web Softphone preview)",
    )
    parser.add_argument("--place-call", action="store_true", help="Place the smoke call after preflight")
    parser.add_argument(
        "--wait",
        action="store_true",
        help="After a user preview call, poll production events until PatientResponded",
    )
    args = parser.parse_args()
    transport = TRANSPORT_USER if args.transport in {"user", TRANSPORT_USER} else TRANSPORT_PSTN
    creds = os.environ.get("VOXIMPLANT_CREDENTIALS", "").strip()
    if not creds:
        print("MANUAL_ACTION_REQUIRED")
        print()
        print("Voximplant:")
        print("Settings -> Service accounts -> Add")
        print("name: eir-bootstrap")
        print("role: Admin")
        print("Generate key")
        print("save JSON locally")
        print("set VOXIMPLANT_CREDENTIALS to its path")
        return 2
    api = VoximplantAPI(load_credentials(creds))
    result = preflight(api, transport=transport)
    manuals = report(result)
    if manuals:
        print()
        print("MANUAL_ACTION_REQUIRED")
        print()
        for item in manuals:
            print(item)
            print()
        return 2
    if transport == TRANSPORT_USER and not args.place_call:
        print("Preflight OK. Open the EIR voice preview, connect, then re-run with:")
        print("  uv run python infra/voximplant/smoke_test.py --transport user --place-call --wait")
        print(f"Voice preview: {VOICE_PREVIEW_URL}")
        print("Login and password are in .voximplant-preview.env (not printed).")
        print(f"Do not use {WEB_SOFTPHONE_URL} for this preview.")
        return 0
    if args.place_call and transport == TRANSPORT_PSTN:
        place_pstn_call()
        print("PSTN StartScenarios accepted. This run placed exactly one PSTN attempt.")
        return 0
    if args.place_call and transport == TRANSPORT_USER:
        episode_id = place_user_call()
        print("Preview StartScenarios accepted. PSTN calls placed: 0")
        if args.wait:
            print("Waiting for callback -> PatientResponded -> risk pipeline...")
            types, missing = wait_for_pipeline(episode_id)
            print("Final event types (sanitized):")
            print("  " + ", ".join(types) if types else "  (none yet)")
            if missing:
                print("Missing expected events:")
                print("  " + ", ".join(missing))
                return 2
        return 0
    print("Preflight OK. Re-run with --place-call to place exactly one smoke call.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
