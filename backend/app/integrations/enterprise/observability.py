"""Enterprise observability hooks."""

from __future__ import annotations

from uuid import uuid4

from eir_shared.observability import StructuredLogger, WorkflowTrace


class EnterpriseObservability:
    def __init__(self, logger: StructuredLogger) -> None:
        self.logger = logger

    def emit_span(
        self,
        *,
        episode_id: str,
        agent_name: str,
        event_type: str,
        status: str,
        parent_trace_id: str | None = None,
    ) -> str:
        trace_id = str(uuid4())
        self.logger.emit(
            WorkflowTrace(
                workflow_id=episode_id,
                episode_id=episode_id,
                trace_id=trace_id,
                agent_name=agent_name,
                event_type=event_type,
                status=status,  # type: ignore[arg-type]
            )
        )
        if parent_trace_id:
            self.logger.emit(
                WorkflowTrace(
                    workflow_id=episode_id,
                    episode_id=episode_id,
                    trace_id=f"{parent_trace_id}>{trace_id}",
                    agent_name=agent_name,
                    event_type=f"span:{event_type}",
                    status="started",  # type: ignore[arg-type]
                )
            )
        return trace_id
