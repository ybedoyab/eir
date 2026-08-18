"""Redact sensitive values from logged shell commands."""

from __future__ import annotations

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
