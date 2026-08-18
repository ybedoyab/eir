"""Voice channel adapters."""

from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from eir_agents.outreach.voice import MockVoiceProvider, VoiceLaunchResult, VoiceMode

SYNTHETIC_PREFIX = "patient-synthetic-"


class SyntheticVoiceProvider(MockVoiceProvider):
    """Structured synthetic conversation stub — NOT Gemini Live telephony."""

    provider_name = "synthetic"
    mode: VoiceMode = "sync"

    async def start_outbound_call(
        self,
        *,
        to: str,
        episode_id: str,
        patient_id: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> VoiceLaunchResult:
        result = await super().start_outbound_call(
            to=to,
            episode_id=episode_id,
            patient_id=patient_id,
            metadata=metadata,
        )
        resolved_patient = patient_id or to.removeprefix("synthetic:")
        conversation = _synthetic_conversation(resolved_patient)
        self.calls[result.call_id]["provider"] = "synthetic-voice"
        self.calls[result.call_id]["conversation"] = conversation
        return VoiceLaunchResult(
            call_id=result.call_id,
            correlation_id=result.correlation_id,
            provider=self.provider_name,
            mode=self.mode,
            conversation=conversation,
        )


class VoximplantVoiceProvider:
    """Starts a VoxEngine scenario. Never waits for the phone conversation."""

    provider_name = "voximplant"
    mode: VoiceMode = "async"

    def __init__(
        self,
        *,
        api: Any,
        rule_id: int,
        application_id: int | None = None,
        demo_phone_e164: str = "",
        caller_id_e164: str = "",
        allow_non_synthetic: bool = False,
        gemini_live_model: str = "gemini-live-2.5-flash-native-audio",
    ) -> None:
        self._api = api
        self._rule_id = int(rule_id)
        self._application_id = int(application_id) if application_id not in (None, "") else None
        self._demo_phone = demo_phone_e164.strip()
        self._caller_id = caller_id_e164.strip()
        self._allow_non_synthetic = allow_non_synthetic
        self._model = gemini_live_model

    async def start_outbound_call(
        self,
        *,
        to: str,
        episode_id: str,
        patient_id: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> VoiceLaunchResult:
        resolved_patient = patient_id or to.removeprefix("synthetic:")
        if not resolved_patient.startswith(SYNTHETIC_PREFIX) and not self._allow_non_synthetic:
            raise PermissionError("hackathon PSTN is restricted to synthetic patients")
        if not self._demo_phone or not self._caller_id:
            raise RuntimeError("demo destination or caller ID is not configured")
        correlation_id = str(uuid4())
        display = str((metadata or {}).get("patient_display_name") or "Alex")
        custom = json.dumps(
            {
                "eid": episode_id,
                "cid": correlation_id,
                "n": display[:24],
            },
            separators=(",", ":"),
        )
        params: dict[str, Any] = {
            "rule_id": self._rule_id,
            "script_custom_data": custom,
        }
        if self._application_id:
            params["application_id"] = self._application_id
        response = self._api.call("StartScenarios", **params)
        if "error" in response:
            message = str((response.get("error") or {}).get("msg") or "start_scenarios_failed")
            raise RuntimeError(message)
        result = response.get("result") or {}
        media_session = result.get("media_session_access_url") or result.get(
            "call_session_history_id"
        )
        call_id = str(media_session or correlation_id)
        return VoiceLaunchResult(
            call_id=call_id,
            correlation_id=correlation_id,
            provider=self.provider_name,
            mode=self.mode,
            metadata={"gemini_live_model": self._model},
        )

    async def send_audio(self, call_id: str, audio: bytes) -> None:
        return None

    async def end_call(self, call_id: str) -> None:
        return None


def _synthetic_conversation(patient_id: str) -> list[dict[str, str]]:
    if patient_id.endswith("002"):
        return [
            {"role": "agent", "text": "How is your pain today on a scale of 0-10?"},
            {"role": "patient", "text": "It is an 8 and I noticed swelling near the incision."},
        ]
    return [
        {"role": "agent", "text": "How is your pain today on a scale of 0-10?"},
        {"role": "patient", "text": "About a 2, recovery is going fine."},
    ]


def voice_provider(name: str, **kwargs: Any) -> Any:
    if name in {"gemini", "synthetic", "mock"}:
        if name == "mock":
            return MockVoiceProvider()
        return SyntheticVoiceProvider()
    if name == "voximplant":
        from app.integrations.voice.voximplant_api import VoximplantAPI, load_credentials

        credentials_source = kwargs.get("credentials_source") or ""
        if not credentials_source:
            raise RuntimeError("VOXIMPLANT_RUNTIME_CREDENTIALS is required")
        api = VoximplantAPI(load_credentials(credentials_source))
        return VoximplantVoiceProvider(
            api=api,
            rule_id=int(kwargs["rule_id"]),
            application_id=kwargs.get("application_id"),
            demo_phone_e164=str(kwargs.get("demo_phone_e164") or ""),
            caller_id_e164=str(kwargs.get("caller_id_e164") or ""),
            gemini_live_model=str(
                kwargs.get("gemini_live_model") or "gemini-live-2.5-flash-native-audio"
            ),
            allow_non_synthetic=bool(kwargs.get("allow_non_synthetic")),
        )
    return MockVoiceProvider()
