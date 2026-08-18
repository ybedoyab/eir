"""Transport contract for Voximplant PSTN vs Web Softphone preview."""

from __future__ import annotations

from pathlib import Path

from app.core.config import Settings, settings
from app.integrations.voice.voximplant_custom import (
    CUSTOM_DATA_LIMIT,
    PREVIEW_USERNAME,
    TRANSPORT_PSTN,
    TRANSPORT_USER,
    encode_script_custom_data,
    inspect_scenario_source,
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
