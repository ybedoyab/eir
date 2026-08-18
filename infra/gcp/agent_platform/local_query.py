"""Local AdkApp query against the live EIR API. Synthetic patients only."""

from __future__ import annotations

import asyncio
import json
import os
import sys

from eir_agents.access.constants import SYNTHETIC_USER_ID
from eir_agents.access.runtime_app import build_adk_app

os.environ.setdefault("EIR_ALLOW_IMPERSONATE_TOOL_SA", "true")


async def _collect(app, message: str, session_id: str | None = None) -> str:
    chunks: list[str] = []
    kwargs = {"user_id": SYNTHETIC_USER_ID, "message": message}
    if session_id:
        kwargs["session_id"] = session_id
    async for event in app.async_stream_query(**kwargs):
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


async def _run() -> dict:
    app = build_adk_app()
    session = await app.async_create_session(user_id=SYNTHETIC_USER_ID)
    session_id = getattr(session, "id", None) or session.get("id")
    appointments = await _collect(
        app, "What appointments do I have?", session_id=session_id
    )
    if "tool:get_upcoming_appointments" not in appointments:
        if "cardio" not in appointments.lower():
            raise RuntimeError("local query did not reach Patient Access tools")
    availability = await _collect(
        app,
        "Show me cardiology availability in the afternoon.",
        session_id=session_id,
    )
    if (
        "tool:search_appointment_availability" not in availability
        and "cardio" not in availability.lower()
    ):
        raise RuntimeError("local availability query did not reach backend tools")
    return {
        "session_id": session_id,
        "appointments_excerpt": appointments[:500],
        "availability_excerpt": availability[:500],
        "note": "local AdkApp uses in-memory sessions; managed proof is remote smoke",
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
