"""ADK execution path: specialists run through Agent + Runner with handler tools."""

from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from eir_shared.capabilities import Capability
from eir_shared.events import DomainEvent
from eir_shared.gemini_config import configure_genai_environment, resolve_gemini_model
from eir_shared.memory import AgentMemory

from eir_agents.adherence.handler import check_task_completion
from eir_agents.common.types import HandlerResult
from eir_agents.escalation.handler import request_human_review
from eir_agents.outreach.handler import handle_follow_up
from eir_agents.outreach.llm import FollowUpSummarizer
from eir_agents.outreach.voice import VoiceProvider
from eir_agents.records.fhir_client import FhirClient
from eir_agents.risk.handler import assess_response
from eir_agents.scheduling.handler import schedule_appointment

logger = logging.getLogger("eir.adk_runner")

HandlerFn = Callable[..., Awaitable[HandlerResult] | HandlerResult]


@dataclass
class InvocationContext:
    capability: str
    event: DomainEvent
    patient_id: str
    episode_id: str
    fhir: FhirClient
    voice: VoiceProvider
    memory: AgentMemory
    summarizer: FollowUpSummarizer
    handler_result: HandlerResult | None = None
    extra: dict[str, Any] = field(default_factory=dict)


class AdkAgentRunner:
    """Runs delegated capabilities via ADK agents (handlers exposed as tools)."""

    def __init__(self, *, mode: str = "direct") -> None:
        self.mode = mode if mode in {"direct", "adk"} else "direct"
        self._ctx: InvocationContext | None = None

    async def invoke(self, ctx: InvocationContext) -> HandlerResult:
        self._ctx = ctx
        if self.mode == "direct":
            return await self._invoke_direct(ctx)
        try:
            return await self._invoke_adk(ctx)
        except Exception:
            logger.exception(
                "ADK runner failed for %s; falling back to direct handler",
                ctx.capability,
            )
            return await self._invoke_direct(ctx)

    async def _invoke_direct(self, ctx: InvocationContext) -> HandlerResult:
        capability = ctx.capability
        event = ctx.event
        if capability == Capability.PATIENT_CONTACT:
            return await handle_follow_up(
                event,
                patient_id=ctx.patient_id,
                fhir=ctx.fhir,
                voice=ctx.voice,
                memory=ctx.memory,
                summarizer=ctx.summarizer,
            )
        if capability == Capability.RISK_ASSESS:
            return assess_response(event)
        if capability == Capability.ESCALATION_REQUEST:
            return request_human_review(event)
        if capability == Capability.ADHERENCE_CHECK:
            return check_task_completion(
                event,
                patient_id=ctx.patient_id,
                fhir=ctx.fhir,
            )
        if capability == Capability.APPOINTMENT_SCHEDULE:
            from eir_shared.events import AppointmentRequested

            appointment_event = (
                event
                if isinstance(event, AppointmentRequested)
                else AppointmentRequested(episode_id=ctx.episode_id)
            )
            return schedule_appointment(
                appointment_event,
                episode_id=ctx.episode_id,
                reason=str(ctx.extra.get("reason") or "synthetic follow-up visit"),
                patient_id=ctx.patient_id,
                fhir=ctx.fhir,
            )
        return HandlerResult(summary=f"no handler for {capability}")

    async def _invoke_adk(self, ctx: InvocationContext) -> HandlerResult:
        configure_genai_environment()
        ctx.handler_result = await self._invoke_direct(ctx)

        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService
        from google.adk.tools import FunctionTool
        from google.genai import types

        runner_ctx = self

        def execute_recovery_handler() -> dict[str, Any]:
            """Return the deterministic handler output for the delegated event."""
            assert runner_ctx._ctx is not None
            assert runner_ctx._ctx.handler_result is not None
            return runner_ctx._ctx.handler_result.model_dump(mode="json")

        agent = self._agent_for(ctx.capability, FunctionTool(execute_recovery_handler))
        session_service = InMemorySessionService()
        runner = Runner(
            agent=agent,
            app_name="eir-recovery",
            session_service=session_service,
            auto_create_session=True,
        )
        prompt = (
            "You are executing a delegated recovery workflow step. "
            "Call execute_recovery_handler exactly once, then reply with OK.\n"
            f"capability={ctx.capability}\n"
            f"event_type={ctx.event.event_type}\n"
            f"episode_id={ctx.episode_id}\n"
            f"patient_id={ctx.patient_id}\n"
            f"payload={json.dumps(ctx.event.payload)}"
        )
        async for _event in runner.run_async(
            user_id=ctx.episode_id,
            session_id=f"{ctx.episode_id}:{ctx.capability}",
            new_message=types.Content(
                role="user",
                parts=[types.Part(text=prompt)],
            ),
        ):
            pass

        return ctx.handler_result

    def _agent_for(self, capability: str, tool: Any) -> Any:
        from google.adk import Agent

        from eir_agents.adherence.agent import root_agent as adherence_agent
        from eir_agents.escalation.agent import root_agent as escalation_agent
        from eir_agents.outreach.agent import root_agent as outreach_agent
        from eir_agents.risk.agent import root_agent as risk_agent
        from eir_agents.scheduling.agent import root_agent as scheduling_agent

        templates: dict[str, Any] = {
            Capability.PATIENT_CONTACT: outreach_agent,
            Capability.RISK_ASSESS: risk_agent,
            Capability.ESCALATION_REQUEST: escalation_agent,
            Capability.ADHERENCE_CHECK: adherence_agent,
            Capability.APPOINTMENT_SCHEDULE: scheduling_agent,
        }
        template = templates.get(capability)
        if template is None:
            return Agent(
                model=resolve_gemini_model(),
                name="recovery_specialist",
                description="Executes a recovery capability via deterministic handler tool.",
                instruction="Call execute_recovery_handler once for the delegated event.",
                tools=[tool],
            )
        return Agent(
            model=template.model,
            name=template.name,
            description=template.description,
            instruction=template.instruction,
            tools=[tool],
        )
