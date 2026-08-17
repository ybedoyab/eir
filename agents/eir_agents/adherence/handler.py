"""Adherence stubs. No medical reasoning."""

from eir_shared.events import DomainEvent

from eir_agents.common.types import HandlerResult


def check_task_completion(event: DomainEvent) -> HandlerResult:
    completed = bool((event.payload or {}).get("completed", True))
    return HandlerResult(
        summary="Recovery task completion recorded (synthetic).",
        episode_status="WAITING",
        next_events=[],
        risk_level=None if completed else "MEDIUM",
    )
