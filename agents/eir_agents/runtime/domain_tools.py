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
from eir_agents.inventory.handler import forecast_replenishment
from eir_agents.outreach.handler import handle_follow_up
from eir_agents.procurement.handler import commit_purchase_order, contact_suppliers
from eir_agents.procurement.handler import (
    draft_purchase_order as draft_purchase_order_handler,
)
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
    supply: Any = None
    supplier_voice: Any = None
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

    def read_stock_levels(self) -> dict[str, Any]:
        """Read the inventory record for the SKU on the current replenishment case."""
        if self.supply is None:
            return {"status": "unavailable"}
        case = self.supply.get_case(self.episode_id)
        if case is None:
            return {"status": "case_not_found", "case_id": self.episode_id}
        item = self.supply.get_item(case.sku)
        if item is None:
            return {"status": "not_found", "sku": case.sku}
        return item.model_dump(mode="json")

    def read_replenishment_case(self) -> dict[str, Any]:
        """Read the current replenishment case, including any recorded quotes."""
        if self.supply is None:
            return {"status": "unavailable"}
        case = self.supply.get_case(self.episode_id)
        if case is None:
            return {"status": "not_found", "case_id": self.episode_id}
        return case.model_dump(mode="json")

    def list_supplier_catalog(self) -> list[dict[str, Any]]:
        """List suppliers that carry the SKU on the current case."""
        if self.supply is None:
            return []
        case = self.supply.get_case(self.episode_id)
        sku = case.sku if case else None
        return [
            supplier.model_dump(mode="json")
            for supplier in self.supply.list_suppliers(sku)
        ]

    def size_replenishment(self) -> dict[str, Any]:
        """Size the replenishment order against usage, lead time, and target level."""
        result = forecast_replenishment(self.event, supply=self.supply)
        return self._record("size_replenishment", result)

    def call_suppliers(self) -> dict[str, Any]:
        """Place outbound supplier calls and record the quotes they state."""
        result = _run_async(
            contact_suppliers(
                self.event,
                supply=self.supply,
                voice=self.supplier_voice,
            )
        )
        return self._record("call_suppliers", result)

    def draft_purchase_order(self) -> dict[str, Any]:
        """Select a supplier from recorded quotes and draft a purchase order."""
        result = draft_purchase_order_handler(self.event, supply=self.supply)
        return self._record("draft_purchase_order", result)

    def place_purchase_order(self) -> dict[str, Any]:
        """Place the drafted order. Reachable only after human authorization."""
        result = commit_purchase_order(self.event, supply=self.supply)
        return self._record("place_purchase_order", result)

    def tools_for_capability(self) -> list[Any]:
        from google.adk.tools import FunctionTool

        common = [
            FunctionTool(self.read_patient),
            FunctionTool(self.read_care_plan),
            FunctionTool(self.read_observations),
            FunctionTool(self.read_medications),
            FunctionTool(self.write_follow_up_observation),
        ]
        # Supply capabilities never touch patient records, so they get their own
        # read-only set rather than the clinical one.
        supply_common = [
            FunctionTool(self.read_stock_levels),
            FunctionTool(self.read_replenishment_case),
            FunctionTool(self.list_supplier_catalog),
        ]
        by_capability: dict[str, list[Any]] = {
            Capability.PATIENT_CONTACT: common + [FunctionTool(self.conduct_outreach)],
            Capability.RISK_ASSESS: common + [FunctionTool(self.assess_patient_response)],
            Capability.ESCALATION_REQUEST: [FunctionTool(self.request_escalation)],
            Capability.ADHERENCE_CHECK: common + [FunctionTool(self.check_adherence)],
            Capability.APPOINTMENT_SCHEDULE: common
            + [FunctionTool(self.schedule_appointment_request)],
            Capability.SUPPLY_FORECAST: supply_common
            + [FunctionTool(self.size_replenishment)],
            Capability.SUPPLIER_CONTACT: supply_common + [FunctionTool(self.call_suppliers)],
            Capability.PURCHASE_ORDER_DRAFT: supply_common
            + [FunctionTool(self.draft_purchase_order)],
            Capability.PURCHASE_ORDER_APPROVE: supply_common
            + [FunctionTool(self.place_purchase_order)],
        }
        return by_capability.get(self.capability, common)

    def required_tool(self) -> str:
        mapping = {
            Capability.PATIENT_CONTACT: "conduct_outreach",
            Capability.RISK_ASSESS: "assess_patient_response",
            Capability.ESCALATION_REQUEST: "request_escalation",
            Capability.ADHERENCE_CHECK: "check_adherence",
            Capability.APPOINTMENT_SCHEDULE: "schedule_appointment_request",
            Capability.SUPPLY_FORECAST: "size_replenishment",
            Capability.SUPPLIER_CONTACT: "call_suppliers",
            Capability.PURCHASE_ORDER_DRAFT: "draft_purchase_order",
            Capability.PURCHASE_ORDER_APPROVE: "place_purchase_order",
        }
        return mapping.get(self.capability, "")


REQUIRED_TOOL_BY_CAPABILITY = {
    Capability.PATIENT_CONTACT: "conduct_outreach",
    Capability.RISK_ASSESS: "assess_patient_response",
    Capability.ESCALATION_REQUEST: "request_escalation",
    Capability.ADHERENCE_CHECK: "check_adherence",
    Capability.APPOINTMENT_SCHEDULE: "schedule_appointment_request",
    Capability.SUPPLY_FORECAST: "size_replenishment",
    Capability.SUPPLIER_CONTACT: "call_suppliers",
    Capability.PURCHASE_ORDER_DRAFT: "draft_purchase_order",
    Capability.PURCHASE_ORDER_APPROVE: "place_purchase_order",
}


def required_tool_for(capability: str) -> str:
    return REQUIRED_TOOL_BY_CAPABILITY.get(capability, "")
