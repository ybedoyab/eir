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
    assert parsed["outbound"] is True
    assert set(parsed) == {
        "episode_id",
        "correlation_id",
        "display_name",
        "transport",
        "destination_user",
        "outbound",
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


def test_scenario_fetches_medication_context_without_packing_names() -> None:
    source = SCENARIO.read_text(encoding="utf-8")
    assert "function loadCallContext" in source
    assert "/context" in source
    assert "medications:" in source
    assert "medication_adherence" in source
    assert "function systemPromptFor" in source


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
    assert "GCP_SA_KEY" not in workflow
    assert "google-github-actions/auth@v3" in workflow
    assert "eir-infra-ci@eir-ata.iam.gserviceaccount.com" in workflow


def test_voice_page_dials_out_and_never_holds_a_password() -> None:
    root = Path(__file__).resolve().parents[2]
    preview_client = root / "frontend" / "src" / "app" / "voice-preview" / "VoicePreviewClient.tsx"
    page = preview_client.read_text(encoding="utf-8")
    helper_path = root / "frontend" / "src" / "lib" / "voximplantPreview.ts"
    helper = helper_path.read_text(encoding="utf-8")
    assert "ConnectionNode.NODE_2" in page
    assert "unmutePlayback" in page
    assert 'VOX_PREVIEW_NODE = "NODE_2"' in helper
    # The browser dials the application; it no longer waits to be rung.
    assert "sdk.call(" in page
    assert "IncomingCall" not in page
    # Login is a server-signed one-time key, never a password typed into the page.
    assert "loginWithOneTimeKey" in page
    assert "requestOneTimeLoginKey" in page
    assert 'type="password"' not in page
    assert "sdk.login(" not in page


def test_scenario_forwards_transcript_without_logging_it() -> None:
    source = SCENARIO.read_text(encoding="utf-8")
    assert "outputAudioTranscription" in source
    assert "inputAudioTranscription" in source
    assert "call.sendMessage" in source
    assert "pushTranscript" in source
    assert "transcriptionFinished" in source
    assert "PlaybackFinished" not in source
    assert "transcript: transcript" in source
    assert "Logger.write" not in source
    assert "privacy: true" in source
    assert "trace: false" in source


def test_browser_custom_data_omits_the_outbound_marker() -> None:
    """The browser leg must not look like a StartScenarios launch.

    VoxEngine promotes an inbound leg's customData to scenario-level custom
    data, so AppEvents.Started fires for a browser check-in too and sees the
    same {eid,cid,n} shape an outbound PSTN dial uses. Without a marker it read
    the browser's payload as a dial request, hit the demo-phone secret, and
    terminated the session milliseconds after CallAlerting had answered.
    """
    web = encode_script_custom_data(
        episode_id="ep-1",
        correlation_id="web-abc123",
        display_name="Alex",
        outbound=False,
    )
    assert '"o"' not in web
    assert parse_script_custom_data(web)["outbound"] is False

    dialled = encode_script_custom_data(episode_id="ep-1", correlation_id="cid-1")
    assert parse_script_custom_data(dialled)["outbound"] is True

    for raw in (web, dialled):
        assert len(raw.encode("utf-8")) <= CUSTOM_DATA_LIMIT


def test_scenario_started_handler_stands_down_for_inbound_legs() -> None:
    """The outbound entry point must gate on the marker, not on event ordering."""
    source = SCENARIO.read_text(encoding="utf-8")
    gate = source.find("custom.outbound")
    pstn_secret = source.find("secret('EIR_DEMO_PHONE_E164')")
    assert gate != -1, "Started must check the outbound marker"
    assert pstn_secret != -1
    # Standing down has to happen before any PSTN secret is touched, or a browser
    # leg throws missing_secret and failStart kills the answered call.
    assert gate < pstn_secret
    assert "outbound: data.o === 1" in source
