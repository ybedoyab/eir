"""Preflight (and optional single paid smoke) for Voximplant PSTN outreach.

Never prints phone numbers, tokens, or credential JSON.
Does not place a call unless --place-call is passed AND preflight succeeds.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(ROOT / "backend"))
if str(ROOT / "infra" / "voximplant") not in sys.path:
    sys.path.insert(0, str(ROOT / "infra" / "voximplant"))

from app.integrations.voice.voximplant_api import VoximplantAPI, load_credentials  # noqa: E402

from provision import (  # noqa: E402
    API_URL,
    CALLBACK_PATH,
    discover,
    route_price,
    verified_caller_ids,
)


def _load_env_file() -> None:
    env_file = ROOT / ".env"
    if not env_file.is_file():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


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


def preflight(api: VoximplantAPI) -> dict[str, Any]:
    info = discover(api)
    destination = os.environ.get("EIR_DEMO_PHONE_E164", "").strip()
    caller = os.environ.get("VOXIMPLANT_CALLER_ID_E164", "").strip()
    runtime = os.environ.get("VOXIMPLANT_RUNTIME_CREDENTIALS", "").strip()
    rule_id = os.environ.get("VOXIMPLANT_RULE_ID", "").strip()
    price_info = route_price(api, destination) if destination else {"groups": []}
    per_minute = _minute_price(price_info.get("groups") or [])
    estimated = None if per_minute is None else round(per_minute * 2, 4)
    live = info.get("live_balance")
    try:
        balance = float(live) if live is not None else None
    except (TypeError, ValueError):
        balance = None
    return {
        "balance": balance,
        "per_minute": per_minute,
        "estimated_two_minutes": estimated,
        "verified_caller_ids": len(verified_caller_ids(api)),
        "destination_configured": bool(destination),
        "caller_id_configured": bool(caller),
        "runtime_credentials_configured": bool(runtime),
        "rule_configured": bool(rule_id),
        "callback_url": API_URL + CALLBACK_PATH,
        "applications": info["applications"],
        "scenarios": info["scenarios"],
        "rules": info["rules"],
    }


def report(result: dict[str, Any]) -> list[str]:
    manuals: list[str] = []
    print("Voice smoke preflight")
    print(f"  live_balance: {result['balance']}")
    print(f"  route_price_per_minute: {result['per_minute']}")
    print(f"  estimated_2min: {result['estimated_two_minutes']}")
    print(f"  verified_caller_ids: {result['verified_caller_ids']}")
    print(f"  destination_secret: {'yes' if result['destination_configured'] else 'no'}")
    print(f"  caller_id_secret: {'yes' if result['caller_id_configured'] else 'no'}")
    print(f"  runtime_credentials: {'yes' if result['runtime_credentials_configured'] else 'no'}")
    print(f"  rule_id: {'yes' if result['rule_configured'] else 'no'}")
    if result["verified_caller_ids"] < 1:
        manuals.append(
            "Voximplant Control Panel → Caller IDs → verify a number by phone/code.\n"
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


def place_call(api: VoximplantAPI) -> None:
    runtime_source = os.environ.get("VOXIMPLANT_RUNTIME_CREDENTIALS", "").strip()
    if not runtime_source:
        raise RuntimeError("VOXIMPLANT_RUNTIME_CREDENTIALS is required to place a smoke call")
    rule_id = os.environ.get("VOXIMPLANT_RULE_ID", "").strip()
    if not rule_id:
        raise RuntimeError("VOXIMPLANT_RULE_ID is required")
    runtime = VoximplantAPI(load_credentials(runtime_source))
    custom = '{"eid":"smoke","cid":"smoke-correlation","n":"Alex"}'
    response = runtime.call("StartScenarios", rule_id=int(rule_id), script_custom_data=custom)
    if "error" in response:
        raise RuntimeError(str((response.get("error") or {}).get("msg") or "start_scenarios_failed"))
    print("StartScenarios accepted (conversation continues asynchronously).")


def main() -> int:
    _load_env_file()
    parser = argparse.ArgumentParser(description="Voximplant EIR voice smoke preflight")
    parser.add_argument("--place-call", action="store_true", help="Place exactly one paid PSTN smoke call")
    args = parser.parse_args()
    creds = os.environ.get("VOXIMPLANT_CREDENTIALS", "").strip()
    if not creds:
        print("MANUAL_ACTION_REQUIRED")
        print()
        print("Voximplant:")
        print("Settings → Service accounts → Add")
        print("name: eir-bootstrap")
        print("role: Admin")
        print("Generate key")
        print("save JSON locally")
        print("set VOXIMPLANT_CREDENTIALS to its path")
        return 2
    api = VoximplantAPI(load_credentials(creds))
    result = preflight(api)
    manuals = report(result)
    if manuals:
        print()
        print("MANUAL_ACTION_REQUIRED")
        print()
        for item in manuals:
            print(item)
            print()
        return 2
    if args.place_call:
        place_call(api)
    else:
        print("Preflight OK. Re-run with --place-call to place exactly one smoke call.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
