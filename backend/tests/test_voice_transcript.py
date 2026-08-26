"""Transcript merge helpers used by the voice preview page."""

from __future__ import annotations

from pathlib import Path


def test_transcript_merge_helpers_present() -> None:
    source = (
        Path(__file__).resolve().parents[2] / "frontend" / "src" / "lib" / "voiceTranscript.ts"
    ).read_text(encoding="utf-8")
    assert "appendTranscript" in source
    assert "pending" in source


def test_voice_preview_uses_sdk_auto_render() -> None:
    page = (
        Path(__file__).resolve().parents[2]
        / "frontend"
        / "src"
        / "app"
        / "voice-preview"
        / "VoicePreviewClient.tsx"
    ).read_text(encoding="utf-8")
    assert "micRequired: true" in page
    assert "attachRecordingDevice" not in page
    assert "Mic sending" in page
    assert "MediaElementCreated" in page
    assert "appendTranscript" in page
    assert "playToneScript" not in page
    # The browser dials out, so nothing rings on this side any more.
    assert "createLocalRinger" not in page
    assert not (
        Path(__file__).resolve().parents[2] / "frontend" / "src" / "lib" / "voiceRingtone.ts"
    ).exists()
