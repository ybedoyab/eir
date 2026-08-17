"""Outreach: structured follow-up using synthetic records. No telephony, no diagnosis."""

from __future__ import annotations

from eir_shared.events import DomainEvent, PatientResponded
from eir_shared.memory import AgentMemory, InMemoryAgentMemory

from eir_agents.common.types import HandlerResult
from eir_agents.outreach.voice import MockVoiceProvider, VoiceProvider
from eir_agents.records.fhir_client import FhirClient, LocalFhirClient

# Synthetic demo profiles. Not real patients.
_ISSUE_PATIENTS = {"patient-synthetic-002"}


async def handle_follow_up(
    event: DomainEvent,
    *,
    patient_id: str,
    fhir: FhirClient | None = None,
    voice: VoiceProvider | None = None,
    memory: AgentMemory | None = None,
) -> HandlerResult:
    fhir = fhir or LocalFhirClient()
    voice = voice or MockVoiceProvider()
    memory = memory or InMemoryAgentMemory()

    care_plan = fhir.get_care_plan(patient_id)
    observations = fhir.get_observations(patient_id)
    observation = observations[0] if observations else {}

    reported_issue = patient_id in _ISSUE_PATIENTS
    pain_score = 8 if reported_issue else int(observation.get("valueInteger") or 2)
    care_plan_title = (care_plan or {}).get("title") or "none"

    call_id = await voice.start_outbound_call(
        to=f"synthetic:{patient_id}",
        episode_id=event.episode_id,
        metadata={"channel": "voice", "care_plan": care_plan_title},
    )
    await voice.end_call(call_id)

    payload = {
        "channel": "voice",
        "care_plan": care_plan_title,
        "pain_score": pain_score,
        "reported_issue": reported_issue,
        "synthetic": True,
    }
    await memory.set(event.episode_id, "outreach", "last_response", payload)

    responded = PatientResponded(
        episode_id=event.episode_id,
        channel="voice",
        payload=payload,
    )
    return HandlerResult(
        summary=f"Simulated follow-up for {patient_id}; pain_score={pain_score}",
        episode_status="WAITING",
        next_events=[responded],
    )
