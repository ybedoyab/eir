"""Structured workflow tracing.

Fields map later to Gemini Enterprise Agent Observability / Cloud Trace / Cloud Logging.
This is a logger, not a custom observability platform.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

TraceStatus = Literal["started", "ok", "error", "delegated", "blocked"]


class WorkflowTrace(BaseModel):
    workflow_id: str
    episode_id: str
    trace_id: str
    agent_name: str
    event_type: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    status: TraceStatus


class StructuredLogger:
    def __init__(self, name: str = "eir") -> None:
        self._logger = logging.getLogger(name)
        if not self._logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("%(message)s"))
            self._logger.addHandler(handler)
            self._logger.setLevel(logging.INFO)

    def emit(self, trace: WorkflowTrace) -> None:
        self._logger.info(json.dumps(trace.model_dump(mode="json"), default=str))
