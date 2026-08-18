"""Shared ADK runtime telemetry payload."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class AdkInvocationTelemetry:
    timestamp: str
    service: str
    model: str
    model_location: str
    capability: str
    agent_name: str
    episode_id: str
    trace_id: str
    tools_invoked: list[str]
    success: bool
    used_direct_fallback: bool
    error_type: str | None = None
    error_message: str | None = None
    security_adapter: str | None = None
    security_category: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def sanitize_error(exc: BaseException | None) -> tuple[str | None, str | None]:
    if exc is None:
        return None, None
    message = str(exc).strip()
    if len(message) > 240:
        message = message[:237] + "..."
    return type(exc).__name__, message or type(exc).__name__
