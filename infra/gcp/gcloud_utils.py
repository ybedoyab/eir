"""Shared helpers for GCP deploy/provision scripts."""

from __future__ import annotations

import os

_REDACTED = "***REDACTED***"


def redact_command_args(args: list[str]) -> list[str]:
    redacted: list[str] = []
    for arg in args:
        if arg.startswith("--headers=X-Scheduler-Token="):
            redacted.append(f"--headers=X-Scheduler-Token={_REDACTED}")
        elif arg.startswith("X-Scheduler-Token="):
            redacted.append(f"X-Scheduler-Token={_REDACTED}")
        else:
            redacted.append(arg)
    return redacted


def model_armor_gcloud_env(location: str = "us-central1") -> dict[str, str]:
    env = os.environ.copy()
    env["CLOUDSDK_API_ENDPOINT_OVERRIDES_MODELARMOR"] = (
        f"https://modelarmor.{location}.rep.googleapis.com/"
    )
    return env
