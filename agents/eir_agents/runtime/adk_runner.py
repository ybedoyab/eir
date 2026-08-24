"""ADK execution path: specialists invoke domain tools through Agent + Runner."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from eir_shared.capabilities import SUPPLY_CAPABILITIES, Capability
from eir_shared.events import DomainEvent
from eir_shared.gemini_config import (
    configure_genai_environment,
    resolve_gemini_location,
    resolve_gemini_model,
)
from eir_shared.memory import AgentMemory
from eir_shared.runtime_telemetry import AdkInvocationTelemetry, sanitize_error

from eir_agents.common.model import gemini_model
from eir_agents.common.types import HandlerResult
from eir_agents.outreach.llm import FollowUpSummarizer
from eir_agents.outreach.voice import VoiceProvider
from eir_agents.records.fhir_client import FhirClient
from eir_agents.runtime.domain_tools import DomainToolKit, required_tool_for

logger = logging.getLogger("eir.adk_runner")


def _invocation_prompt(ctx: InvocationContext, required_tool: str) -> str:
    """Capability-scoped instructions for the delegated step.

    Supply work never touches a patient record, so it must not be handed the
    clinical framing (or the patient id) that recovery steps get.
    """
    if ctx.capability in SUPPLY_CAPABILITIES:
        return (
            "Execute the delegated pharmacy supply step using domain tools only. "
            "You may call the read-only stock and supplier tools first to gather context. "
            f"You MUST call `{required_tool}` exactly once before finishing. "
            "Never state a price or availability figure a supplier did not give you, and "
            "never place an order that has not been authorized.\n"
            f"capability={ctx.capability}\n"
            f"event_type={ctx.event.event_type}\n"
            f"case_id={ctx.episode_id}\n"
            f"payload={json.dumps(ctx.event.payload)}"
        )
    return (
        "Execute the delegated recovery workflow step using domain tools only. "
        "You may call read-only FHIR tools first to gather context. "
        f"You MUST call `{required_tool}` exactly once before finishing. "
        "Do not diagnose. Do not skip the required action tool.\n"
        f"capability={ctx.capability}\n"
        f"event_type={ctx.event.event_type}\n"
        f"episode_id={ctx.episode_id}\n"
        f"patient_id={ctx.patient_id}\n"
        f"payload={json.dumps(ctx.event.payload)}"
    )


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
    supply: Any = None
    supplier_voice: Any = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class AdkRunReport:
    model: str = resolve_gemini_model()
    mode: str = "direct"
    adk_invocation_succeeded: bool = False
    enterprise_endpoint_active: bool = False
    tools_invoked: list[str] = field(default_factory=list)
    used_direct_fallback: bool = False
    error: str | None = None
    capability: str = ""
    agent_name: str = ""
    episode_id: str = ""
    model_location: str = resolve_gemini_location()


class AdkAgentRunner:
    """Runs delegated capabilities via ADK agents with real domain tools."""

    def __init__(
        self,
        *,
        mode: str = "direct",
        allow_direct_fallback: bool = True,
        telemetry: Any | None = None,
        service_name: str = "local",
    ) -> None:
        self.mode = mode if mode in {"direct", "adk"} else "direct"
        self.allow_direct_fallback = allow_direct_fallback
        self.last_report = AdkRunReport(mode=self.mode)
        self.tool_audit: list[str] = []
        self._telemetry = telemetry
        self._service_name = service_name

    async def invoke(self, ctx: InvocationContext) -> HandlerResult:
        if self.mode == "direct":
            return await self._invoke_direct(ctx)
        agent_name = self._agent_name_for(ctx.capability)
        try:
            result = await self._invoke_adk(ctx, agent_name=agent_name)
            self._record_telemetry(ctx, agent_name=agent_name, success=True, error=None)
            return result
        except Exception as exc:
            logger.exception("ADK runner failed for %s", ctx.capability)
            if not self.allow_direct_fallback:
                self.last_report = AdkRunReport(
                    model=resolve_gemini_model(),
                    mode="adk",
                    adk_invocation_succeeded=False,
                    enterprise_endpoint_active=False,
                    error=str(exc),
                    capability=ctx.capability,
                    agent_name=agent_name,
                    episode_id=ctx.episode_id,
                    model_location=resolve_gemini_location(),
                )
                self._record_telemetry(ctx, agent_name=agent_name, success=False, error=exc)
                raise
            self.last_report = AdkRunReport(
                model=resolve_gemini_model(),
                mode="adk",
                adk_invocation_succeeded=False,
                enterprise_endpoint_active=False,
                used_direct_fallback=True,
                error=str(exc),
                capability=ctx.capability,
                agent_name=agent_name,
                episode_id=ctx.episode_id,
                model_location=resolve_gemini_location(),
            )
            self._record_telemetry(ctx, agent_name=agent_name, success=False, error=exc)
            return await self._invoke_direct(ctx)

    async def _invoke_direct(self, ctx: InvocationContext) -> HandlerResult:
        toolkit = DomainToolKit(
            capability=ctx.capability,
            event=ctx.event,
            patient_id=ctx.patient_id,
            episode_id=ctx.episode_id,
            fhir=ctx.fhir,
            voice=ctx.voice,
            memory=ctx.memory,
            summarizer=ctx.summarizer,
            supply=ctx.supply,
            supplier_voice=ctx.supplier_voice,
        )
        required = toolkit.required_tool()
        tool = getattr(toolkit, required, None)
        if tool is None:
            return HandlerResult(summary=f"no handler for {ctx.capability}")
        payload = tool() if required != "schedule_appointment_request" else tool(
            str(ctx.extra.get("reason") or "synthetic follow-up visit")
        )
        self.last_report = AdkRunReport(
            model=resolve_gemini_model(),
            mode="direct",
            adk_invocation_succeeded=True,
            enterprise_endpoint_active=False,
            tools_invoked=list(toolkit.tools_invoked),
            capability=ctx.capability,
            agent_name=self._agent_name_for(ctx.capability),
            episode_id=ctx.episode_id,
            model_location=resolve_gemini_location(),
        )
        self.tool_audit.extend(toolkit.tools_invoked)
        return toolkit.handler_result or HandlerResult(summary=str(payload))

    async def _invoke_adk(self, ctx: InvocationContext, *, agent_name: str) -> HandlerResult:
        configure_genai_environment()
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService
        from google.genai import types

        toolkit = DomainToolKit(
            capability=ctx.capability,
            event=ctx.event,
            patient_id=ctx.patient_id,
            episode_id=ctx.episode_id,
            fhir=ctx.fhir,
            voice=ctx.voice,
            memory=ctx.memory,
            summarizer=ctx.summarizer,
            supply=ctx.supply,
            supplier_voice=ctx.supplier_voice,
        )
        tools = toolkit.tools_for_capability()
        agent = self._agent_for(ctx.capability, tools)
        required_tool = toolkit.required_tool()
        prompt = _invocation_prompt(ctx, required_tool)
        runner = Runner(
            agent=agent,
            app_name="eir-supply" if ctx.capability in SUPPLY_CAPABILITIES else "eir-recovery",
            session_service=InMemorySessionService(),
            auto_create_session=True,
        )
        async for _event in runner.run_async(
            user_id=ctx.episode_id,
            session_id=f"{ctx.episode_id}:{ctx.capability}:{ctx.event.event_id}",
            new_message=types.Content(
                role="user",
                parts=[types.Part(text=prompt)],
            ),
        ):
            pass

        if required_tool not in toolkit.tools_invoked:
            raise RuntimeError(
                f"ADK agent did not invoke required tool `{required_tool}` "
                f"(invoked={toolkit.tools_invoked})"
            )
        if toolkit.handler_result is None:
            raise RuntimeError("ADK tools ran but no HandlerResult was produced")

        self.last_report = AdkRunReport(
            model=resolve_gemini_model(),
            mode="adk",
            adk_invocation_succeeded=True,
            enterprise_endpoint_active=False,
            tools_invoked=list(toolkit.tools_invoked),
            capability=ctx.capability,
            agent_name=agent_name,
            episode_id=ctx.episode_id,
            model_location=resolve_gemini_location(),
        )
        self.tool_audit.extend(toolkit.tools_invoked)
        return toolkit.handler_result

    def _record_telemetry(
        self,
        ctx: InvocationContext,
        *,
        agent_name: str,
        success: bool,
        error: BaseException | None,
    ) -> None:
        if self._telemetry is None:
            return
        error_type, error_message = sanitize_error(error)
        self._telemetry.record(
            AdkInvocationTelemetry(
                timestamp=datetime.now(UTC).isoformat(),
                service=self._service_name,
                model=self.last_report.model,
                model_location=self.last_report.model_location,
                capability=ctx.capability,
                agent_name=agent_name,
                episode_id=ctx.episode_id,
                trace_id=ctx.event.event_id,
                tools_invoked=list(self.last_report.tools_invoked),
                success=success,
                used_direct_fallback=self.last_report.used_direct_fallback,
                error_type=error_type,
                error_message=error_message,
            )
        )

    def record_security_event(
        self,
        *,
        episode_id: str,
        capability: str,
        adapter: str,
        category: str,
        trace_id: str,
    ) -> None:
        if self._telemetry is None:
            return
        self._telemetry.record(
            AdkInvocationTelemetry(
                timestamp=datetime.now(UTC).isoformat(),
                service=self._service_name,
                model=resolve_gemini_model(),
                model_location=resolve_gemini_location(),
                capability=capability,
                agent_name="content_guard",
                episode_id=episode_id,
                trace_id=trace_id,
                tools_invoked=[],
                success=False,
                used_direct_fallback=False,
                security_adapter=adapter,
                security_category=category,
            )
        )

    def _agent_name_for(self, capability: str) -> str:
        templates = {
            Capability.PATIENT_CONTACT: "outreach_agent",
            Capability.RISK_ASSESS: "risk_agent",
            Capability.ESCALATION_REQUEST: "escalation_agent",
            Capability.ADHERENCE_CHECK: "adherence_agent",
            Capability.APPOINTMENT_SCHEDULE: "scheduling_agent",
            Capability.SUPPLY_FORECAST: "inventory_agent",
            Capability.SUPPLIER_CONTACT: "procurement_agent",
            Capability.PURCHASE_ORDER_DRAFT: "procurement_agent",
            Capability.PURCHASE_ORDER_APPROVE: "procurement_agent",
        }
        return templates.get(capability, "recovery_specialist")

    def _agent_for(self, capability: str, tools: list[Any]) -> Any:
        from google.adk import Agent

        from eir_agents.adherence.agent import root_agent as adherence_agent
        from eir_agents.escalation.agent import root_agent as escalation_agent
        from eir_agents.inventory.agent import root_agent as inventory_agent
        from eir_agents.outreach.agent import root_agent as outreach_agent
        from eir_agents.procurement.agent import root_agent as procurement_agent
        from eir_agents.risk.agent import root_agent as risk_agent
        from eir_agents.scheduling.agent import root_agent as scheduling_agent

        templates: dict[str, Any] = {
            Capability.PATIENT_CONTACT: outreach_agent,
            Capability.RISK_ASSESS: risk_agent,
            Capability.ESCALATION_REQUEST: escalation_agent,
            Capability.ADHERENCE_CHECK: adherence_agent,
            Capability.APPOINTMENT_SCHEDULE: scheduling_agent,
            Capability.SUPPLY_FORECAST: inventory_agent,
            Capability.SUPPLIER_CONTACT: procurement_agent,
            Capability.PURCHASE_ORDER_DRAFT: procurement_agent,
            Capability.PURCHASE_ORDER_APPROVE: procurement_agent,
        }
        template = templates.get(capability)
        required_tool = required_tool_for(capability)
        if capability in SUPPLY_CAPABILITIES:
            default_instruction = "Execute pharmacy supply workflow step."
            context_line = "You may inspect read-only stock and supplier tools first. "
        else:
            default_instruction = "Execute recovery workflow step."
            context_line = "You may inspect read-only FHIR tools before acting. "
        instruction = (
            f"{template.instruction if template else default_instruction} "
            f"{context_line}"
            f"Call `{required_tool}` exactly once."
        )
        if template is None:
            return Agent(
                model=gemini_model(),
                name="recovery_specialist",
                description="Executes a recovery capability via domain tools.",
                instruction=instruction,
                tools=tools,
            )
        return Agent(
            model=gemini_model(),
            name=template.name,
            description=template.description,
            instruction=instruction,
            tools=tools,
        )
