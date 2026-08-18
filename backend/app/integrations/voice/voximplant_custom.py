"""Compact VoxEngine custom data. Never include phones, tokens, or FHIR."""

from __future__ import annotations

import json
import re
from typing import Any, Literal

CUSTOM_DATA_LIMIT = 200
TRANSPORT_PSTN = "pstn"
TRANSPORT_USER = "voximplant_user"
PREVIEW_USERNAME = "eir-preview-user"
PIPELINE_EVENTS = (
    "VoiceCallStarted",
    "VoiceCallConnected",
    "VoiceCallCompleted",
    "PatientResponded",
    "RiskEscalated",
    "HumanReviewRequested",
)
VoiceTransport = Literal["pstn", "voximplant_user"]

_USER_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{1,49}$")
_PHONE_RE = re.compile(r"^\+?\d{7,15}$")


def missing_pipeline_events(event_types: list[str]) -> list[str]:
    seen = set(event_types)
    return [name for name in PIPELINE_EVENTS if name not in seen]


def sanitize_preview_username(value: str | None) -> str:
    user = str(value or PREVIEW_USERNAME).strip()
    if not user or _PHONE_RE.match(user) or "@" in user or user.startswith("+"):
        return PREVIEW_USERNAME
    if not _USER_RE.match(user):
        return PREVIEW_USERNAME
    return user[:40]


def encode_script_custom_data(
    *,
    episode_id: str,
    correlation_id: str,
    display_name: str = "Alex",
    transport: str = TRANSPORT_PSTN,
    destination_user: str | None = None,
    **ignored: Any,
) -> str:
    """Build StartScenarios custom data. Extra kwargs (including phones) are dropped."""
    del ignored
    payload: dict[str, str] = {
        "eid": str(episode_id),
        "cid": str(correlation_id),
        "n": str(display_name or "Alex")[:24],
    }
    resolved = TRANSPORT_USER if transport == TRANSPORT_USER else TRANSPORT_PSTN
    if resolved == TRANSPORT_USER:
        payload["t"] = "user"
        payload["u"] = sanitize_preview_username(destination_user)
    raw = json.dumps(payload, separators=(",", ":"))
    if len(raw.encode("utf-8")) > CUSTOM_DATA_LIMIT:
        raise ValueError("Voximplant custom data exceeds 200 bytes")
    return raw


def parse_script_custom_data(raw: str) -> dict[str, str]:
    data = json.loads(raw or "{}")
    if not isinstance(data, dict):
        raise ValueError("invalid_custom_data")
    transport = (
        TRANSPORT_USER
        if data.get("t") == "user" or data.get("transport") == TRANSPORT_USER
        else TRANSPORT_PSTN
    )
    return {
        "episode_id": str(data.get("eid") or ""),
        "correlation_id": str(data.get("cid") or ""),
        "display_name": str(data.get("n") or "Alex")[:24],
        "transport": transport,
        "destination_user": sanitize_preview_username(str(data.get("u") or PREVIEW_USERNAME)),
    }


def inspect_scenario_source(source: str) -> dict[str, Any]:
    """Static contract for the shared VoxEngine scenario."""
    start_fn = source.find("function startDestinationCall")
    gemini_fn = source.find("function startGeminiLive")
    connected = source.find("CallEvents.Connected")
    return {
        "has_start_destination_call": start_fn != -1,
        "has_shared_gemini": gemini_fn != -1,
        "call_user_count": source.count("VoxEngine.callUser"),
        "call_pstn_count": source.count("VoxEngine.callPSTN"),
        "gemini_client_count": source.count("Gemini.createLiveAPIClient"),
        "send_media_count": source.count("VoxEngine.sendMediaBetween"),
        "call_user_inside_start": "VoxEngine.callUser" in source[start_fn : start_fn + 800]
        if start_fn != -1
        else False,
        "call_pstn_inside_start": "VoxEngine.callPSTN" in source[start_fn : start_fn + 800]
        if start_fn != -1
        else False,
        "gemini_after_connected": gemini_fn != -1 and connected != -1,
        "pstn_secrets_required_for_user": False,
        "reads_destination_from_custom_data": "data.destination" in source
        or "data.phone" in source,
        "model": "gemini-live-2.5-flash-native-audio" in source,
        "vertex_backend": "Gemini.Backend.VERTEX_AI" in source,
        "parses_vertex_credentials_json": "JSON.parse(secret('EIR_GEMINI_VERTEX_CREDENTIALS'))"
        in source,
        "credentials_string": "var credentials = secret('EIR_GEMINI_VERTEX_CREDENTIALS')" in source,
        "privacy_mode": "privacy: true" in source,
        "trace_disabled": "trace: false" in source,
        "uses_send_realtime_input": "sendRealtimeInput" in source,
        "starts_media_without_setup_complete": "startConversation();" in source,
        "uses_native_tts_greeting": "call.say(" in source,
        "binds_media_on_setup_complete": "LiveAPIEvents.SetupComplete" in source
        and "bindCallAudio" in source,
    }
