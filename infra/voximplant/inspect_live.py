"""Print sanitized markers from the latest Voximplant session logs."""

from __future__ import annotations

import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.integrations.voice.voximplant_api import VoximplantAPI, load_credentials


def _load_env() -> None:
    env = ROOT / ".env"
    if not env.is_file():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def main() -> int:
    _load_env()
    api = VoximplantAPI(load_credentials(os.environ["VOXIMPLANT_CREDENTIALS"]))
    info = api.call("GetAccountInfo")
    if info.get("api_address"):
        api.use_host(info["api_address"])
    hist = api.call("GetCallHistory", count=5)
    rows = hist.get("result") or []
    if not isinstance(rows, list):
        print("no_history")
        return 0
    for index, item in enumerate(rows[:5]):
        url = item.get("log_file_url") or ""
        print("call", index, "duration", item.get("duration"), "log", bool(url))
        if not url:
            continue
        with urllib.request.urlopen(url, timeout=30) as response:
            log = response.read().decode("utf-8", "replace")
        flags = {
            "media_started": "MediaEventStarted" in log,
            "media_ended": "MediaEventEnded" in log,
            "pcm16": "PCM16" in log,
            "send_media": "sendMediaBetween" in log or "SendMedia" in log,
            "create_ws": "CreateWebSocket" in log,
            "ws_close": "WebSocket.Close" in log,
            "startConversation": "startConversation" in log,
        }
        print(" flags", flags)
        for line in log.splitlines():
            if any(
                token in line
                for token in (
                    "MediaEvent",
                    "CreateWebSocket",
                    "SendMessageWebSocket",
                    "sendMedia",
                    "Playback",
                    "say",
                    "Error",
                    "error",
                )
            ):
                if "BEGIN" in line or "private_key" in line:
                    continue
                print(" ", line[:220])
        print("---")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
