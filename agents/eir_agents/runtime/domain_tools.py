"""Domain operations exposed as ADK tools. Policy/safety stays outside the LLM."""

from __future__ import annotations

import asyncio
import concurrent.futures
import json
from dataclasses import dataclass, field
from typing import Any

from eir_shared.capabilities import Capability
from eir_shared.events import AppointmentRequested, DomainEvent

from eir_agents.adherence.handler import check_task_completion
from eir_agents.common.types import HandlerResult
from eir_agents.escalation.handler import request_human_review
from eir_agents.outreach.handler import handle_follow_up
from eir_agents.risk.handler import assess_response
from eir_agents.scheduling.handler import schedule_appointment


def _run_async(coro: Any) -> Any:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()


@dataclass
class DomainToolKit:
    """Binds workflow context to callable ADK tools."""

    capability: str
    event: DomainEvent
    patient_id: str
    episode_id: str
    fhir: Any
    voice: Any
    memory: Any
    summarizer: Any
    handler_result: HandlerResult | None = None
    tools_invoked: list[str] = field(default_factory=list)

    def _record(self, tool_name: str, result: HandlerResult) -> dict[str, Any]:
        self.tools_invoked.append(tool_name)
        self.handler_result = result
        return result.model_dump(mode="json")

    def read_patient(self) -> dict[str, Any]:
        """Read the patient FHIR resource for the current episode."""
        patient = self.fhir.get_patient(self.patient_id)
        return patient or {"status": "not_found", "patient_id": self.patient_id}

    def read_care_plan(self) -> dict[str, Any]:
        """Read the active care plan for the current patient."""
        plan = self.fhir.get_care_plan(self.patient_id)
        return plan or {"status": "not_found", "patient_id": self.patient_id}

    def read_observations(self) -> list[dict[str, Any]]:
        """Read FHIR observations for the current patient."""
        return self.fhir.get_observations(self.patient_id)

    def read_medications(self) -> list[dict[str, Any]]:
        """Read medication requests for the current patient."""
        return self.fhir.get_medications(self.patient_id)

    def write_follow_up_observation(self, observation_json: str) -> dict[str, Any]:
        """Write a follow-up Observation resource (JSON string)."""
        payload = json.loads(observation_json)
        stored = self.fhir.append_follow_up_observation(payload)
        return stored

    def conduct_outreach(self) -> dict[str, Any]:
        """Run outbound recovery follow-up contact for the current episode."""
        result = _run_async(
            handle_follow_up(
                self.event,
                patient_id=self.patient_id,
                fhir=self.fhir,
                voice=self.voice,
                memory=self.memory,
                summarizer=self.summarizer,
            )
        )
        return self._record("conduct_outreach", result)

    def assess_patient_response(self) -> dict[str, Any]:
        """Assess structured patient response signals for escalation."""
        result = assess_response(self.event)
        return self._record("assess_patient_response", result)

    def request_escalation(self) -> dict[str, Any]:
        """Request human review / escalation for the current episode."""
        result = request_human_review(self.event)
        return self._record("request_escalation", result)

    def check_adherence(self) -> dict[str, Any]:
        """Check medication adherence for the current episode."""
        result = check_task_completion(
            self.event,
            patient_id=self.patient_id,
            fhir=self.fhir,
        )
        return self._record("check_adherence", result)

    def schedule_appointment_request(self, reason: str) -> dict[str, Any]:
        """Create a synthetic FHIR Appointment and request clinician approval."""
        appointment_event = (
            self.event
            if isinstance(self.event, AppointmentRequested)
            else AppointmentRequested(episode_id=self.episode_id)
        )
        result = schedule_appointment(
            appointment_event,
            episode_id=self.episode_id,
            reason=reason,
            patient_id=self.patient_id,
            fhir=self.fhir,
        )
        return self._record("schedule_appointment_request", result)

    def tools_for_capability(self) -> list[Any]:
        from google.adk.tools import FunctionTool

        common = [
            FunctionTool(self.read_patient),
            FunctionTool(self.read_care_plan),
            FunctionTool(self.read_observations),
            FunctionTool(self.read_medications),
            FunctionTool(self.write_follow_up_observation),
        ]
        by_capability: dict[str, list[Any]] = {
            Capability.PATIENT_CONTACT: common + [FunctionTool(self.conduct_outreach)],
            Capability.RISK_ASSESS: common + [FunctionTool(self.assess_patient_response)],
            Capability.ESCALATION_REQUEST: [FunctionTool(self.request_escalation)],
            Capability.ADHERENCE_CHECK: common + [FunctionTool(self.check_adherence)],
            Capability.APPOINTMENT_SCHEDULE: common
            + [FunctionTool(self.schedule_appointment_request)],
        }
        return by_capability.get(self.capability, common)

    def required_tool(self) -> str:
        mapping = {
            Capability.PATIENT_CONTACT: "conduct_outreach",
            Capability.RISK_ASSESS: "assess_patient_response",
            Capability.ESCALATION_REQUEST: "request_escalation",
            Capability.ADHERENCE_CHECK: "check_adherence",
            Capability.APPOINTMENT_SCHEDULE: "schedule_appointment_request",
        }
        return mapping.get(self.capability, "")


REQUIRED_TOOL_BY_CAPABILITY = {
    Capability.PATIENT_CONTACT: "conduct_outreach",
    Capability.RISK_ASSESS: "assess_patient_response",
    Capability.ESCALATION_REQUEST: "request_escalation",
    Capability.ADHERENCE_CHECK: "check_adherence",
    Capability.APPOINTMENT_SCHEDULE: "schedule_appointment_request",
}


def required_tool_for(capability: str) -> str:
    return REQUIRED_TOOL_BY_CAPABILITY.get(capability, "")
