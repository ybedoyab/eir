"""Transport contract for Voximplant PSTN vs Web Softphone preview."""

from __future__ import annotations

from pathlib import Path

from app.core.config import Settings, settings
from app.integrations.voice.voximplant_custom import (
    CUSTOM_DATA_LIMIT,
    PIPELINE_EVENTS,
    PREVIEW_USERNAME,
    TRANSPORT_PSTN,
    TRANSPORT_USER,
    encode_script_custom_data,
    inspect_scenario_source,
    missing_pipeline_events,
    parse_script_custom_data,
    sanitize_preview_username,
)

SCENARIO = Path(__file__).resolve().parents[2] / "infra" / "voximplant" / "scenario.js"


def test_production_default_transport_is_pstn() -> None:
    assert Settings.model_fields["voximplant_voice_transport"].default == TRANSPORT_PSTN
    assert settings.voximplant_voice_transport in {TRANSPORT_PSTN, TRANSPORT_USER}


def test_pstn_custom_data_omits_transport_and_phones() -> None:
    raw = encode_script_custom_data(
        episode_id="ep-1",
        correlation_id="cid-1",
        display_name="Alex",
        transport=TRANSPORT_PSTN,
        destination="+15555550199",
        caller_id="+15555550100",
        phone="+573001112233",
    )
    parsed = parse_script_custom_data(raw)
    assert parsed["transport"] == TRANSPORT_PSTN
    assert set(parsed) == {
        "episode_id",
        "correlation_id",
        "display_name",
        "transport",
        "destination_user",
    }
    assert "+" not in raw
    assert "15555550199" not in raw
    assert "destination" not in raw
    assert '"t"' not in raw
    assert len(raw.encode("utf-8")) <= CUSTOM_DATA_LIMIT


def test_user_transport_chooses_preview_user_without_phone() -> None:
    raw = encode_script_custom_data(
        episode_id="ep-1",
        correlation_id="cid-1",
        transport=TRANSPORT_USER,
        destination_user="+573001112233",
        destination="+15555550199",
    )
    parsed = parse_script_custom_data(raw)
    assert parsed["transport"] == TRANSPORT_USER
    assert parsed["destination_user"] == PREVIEW_USERNAME
    assert '"t"' in raw
    assert "+" not in raw
    assert "1555" not in raw
    assert "57300" not in raw


def test_sanitize_preview_username_rejects_phone_data() -> None:
    assert sanitize_preview_username("+15555550199") == PREVIEW_USERNAME
    assert sanitize_preview_username("15555550199") == PREVIEW_USERNAME
    assert sanitize_preview_username("eir-preview-user") == PREVIEW_USERNAME
    assert sanitize_preview_username("alice") == "alice"


def test_scenario_shares_gemini_after_transport_split() -> None:
    source = SCENARIO.read_text(encoding="utf-8")
    info = inspect_scenario_source(source)
    assert info["has_start_destination_call"] is True
    assert info["has_shared_gemini"] is True
    assert info["call_user_count"] == 1
    assert info["call_pstn_count"] == 1
    assert info["gemini_client_count"] == 1
    assert info["send_media_count"] == 1
    assert info["call_user_inside_start"] is True
    assert info["call_pstn_inside_start"] is True
    assert info["gemini_after_connected"] is True
    assert info["reads_destination_from_custom_data"] is False
    assert info["model"] is True
    assert info["vertex_backend"] is True
    assert info["parses_vertex_credentials_json"] is False
    assert info["credentials_string"] is True
    assert info["privacy_mode"] is True
    assert info["trace_disabled"] is True
    assert info["uses_send_realtime_input"] is True
    assert info["starts_media_without_setup_complete"] is False
    assert info["uses_native_tts_greeting"] is False
    assert info["binds_media_on_setup_complete"] is True
    pstn_secret = source.find("secret('EIR_DEMO_PHONE_E164')")
    gate = source.find("session.transport !== 'voximplant_user'")
    assert gate != -1
    assert pstn_secret != -1
    assert gate < pstn_secret
    user_branch = source[source.find("function startDestinationCall") :]
    user_branch = user_branch[: user_branch.find("function notify")]
    assert "callUser" in user_branch
    assert "callPSTN" in user_branch
    assert "createLiveAPIClient" not in user_branch


def test_missing_pipeline_events_reports_exact_gaps() -> None:
    assert missing_pipeline_events(["VoiceCallStarted", "PatientResponded"]) == [
        "VoiceCallConnected",
        "VoiceCallCompleted",
        "RiskEscalated",
        "HumanReviewRequested",
    ]
    assert missing_pipeline_events(list(PIPELINE_EVENTS)) == []


def test_provisioner_can_sync_scenario_without_pstn_secrets() -> None:
    source = (
        Path(__file__).resolve().parents[2] / "infra" / "voximplant" / "provision.py"
    ).read_text(encoding="utf-8")
    workflow = (
        Path(__file__).resolve().parents[2] / ".github" / "workflows" / "ci.yml"
    ).read_text(encoding="utf-8")
    assert "--sync-scenario" in source
    assert "def sync_scenario" in source
    assert "provision.py --sync-scenario" in workflow
    assert "uv run --package eir-backend" in workflow
    assert "VOXIMPLANT_CREDENTIALS" in workflow
    assert "infra/gcp/deploy.py --services-only" in workflow


def test_voice_preview_page_uses_node2_and_not_hosted_webphone() -> None:
    root = Path(__file__).resolve().parents[2]
    page = (root / "frontend" / "src" / "app" / "voice-preview" / "VoicePreviewClient.tsx").read_text(
        encoding="utf-8"
    )
    helper = (root / "frontend" / "src" / "lib" / "voximplantPreview.ts").read_text(encoding="utf-8")
    smoke = (root / "infra" / "voximplant" / "smoke_test.py").read_text(encoding="utf-8")
    assert "ConnectionNode.NODE_2" in page
    assert "unmutePlayback" in page
    assert "phone.voximplant.com" in page
    assert 'VOX_PREVIEW_NODE = "NODE_2"' in helper
    assert "/voice-preview" in smoke


def test_scenario_forwards_transcript_without_logging_it() -> None:
    source = SCENARIO.read_text(encoding="utf-8")
    assert "outputAudioTranscription" in source
    assert "inputAudioTranscription" in source
    assert "call.sendMessage" in source
    assert "mergeUtterance" in source
    assert "transcriptionFinished" in source
    assert "PlaybackFinished" not in source
    assert "transcript: transcript" in source
    assert "Logger.write" not in source
    assert "privacy: true" in source
    assert "trace: false" in source
