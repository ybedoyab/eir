"""Outreach: structured follow-up using synthetic records. No diagnosis.

Synchronous voice providers (mock/synthetic) may return PatientResponded
immediately. Asynchronous PSTN providers only start the call; the recovery
check-in arrives later through the event bus.
"""

from __future__ import annotations

from eir_shared.events import DomainEvent, PatientResponded, VoiceCallStarted
from eir_shared.memory import AgentMemory, InMemoryAgentMemory

from eir_agents.common.types import HandlerResult
from eir_agents.outreach.conversation import signals_from_conversation
from eir_agents.outreach.llm import FollowUpSummarizer, TemplateFollowUpSummarizer
from eir_agents.outreach.voice import MockVoiceProvider, VoiceProvider
from eir_agents.records.fhir_client import FhirClient, LocalFhirClient
from eir_agents.records.fhir_utils import (
    pain_score_from_observation,
    reported_issue_from_observation,
)


async def handle_follow_up(
    event: DomainEvent,
    *,
    patient_id: str,
    fhir: FhirClient | None = None,
    voice: VoiceProvider | None = None,
    memory: AgentMemory | None = None,
    summarizer: FollowUpSummarizer | None = None,
) -> HandlerResult:
    fhir = fhir or LocalFhirClient()
    voice = voice or MockVoiceProvider()
    memory = memory or InMemoryAgentMemory()
    summarizer = summarizer or TemplateFollowUpSummarizer()

    care_plan = fhir.get_care_plan(patient_id)
    observations = fhir.get_observations(patient_id)
    observation = observations[0] if observations else {}
    care_plan_title = (care_plan or {}).get("title") or "none"
    display_name = _patient_display_name(fhir.get_patient(patient_id))

    launch = await voice.start_outbound_call(
        to=f"synthetic:{patient_id}",
        episode_id=event.episode_id,
        patient_id=patient_id,
        metadata={
            "channel": "voice",
            "care_plan": care_plan_title,
            "patient_display_name": display_name,
            "care_plan_context": "post-procedure recovery follow-up",
        },
    )
    await memory.set(
        event.episode_id,
        "outreach",
        "last_call",
        {
            "call_id": launch.call_id,
            "correlation_id": launch.correlation_id,
            "provider": launch.provider,
            "mode": launch.mode,
        },
    )

    started = VoiceCallStarted(
        episode_id=event.episode_id,
        payload={
            "provider": launch.provider,
            "correlation_id": launch.correlation_id,
            "mode": launch.mode,
            "call_id": launch.call_id,
            "gemini_live_model": (launch.metadata or {}).get("gemini_live_model"),
            "transport": (launch.metadata or {}).get("transport") or (
                "webrtc" if launch.provider == "voximplant-web" else None
            ),
        },
    )

    if launch.mode == "async":
        return HandlerResult(
            summary="Outbound voice call started; waiting for callback",
            episode_status="ACTIVE",
            next_events=[started],
        )

    await voice.end_call(launch.call_id)
    conversation = launch.conversation or []
    if conversation:
        reported_issue, pain_from_conversation, adherence = signals_from_conversation(
            conversation
        )
        pain_score = pain_from_conversation if pain_from_conversation is not None else 2
    else:
        reported_issue = reported_issue_from_observation(observation)
        pain_score = pain_score_from_observation(
            observation,
            default=2 if not reported_issue else 8,
        )
        adherence = None

    payload = {
        "channel": "voice",
        "care_plan": care_plan_title,
        "pain_score": pain_score,
        "reported_issue": reported_issue,
        "synthetic": True,
        "provider": launch.provider,
    }
    if adherence is not None:
        payload["medication_adherence"] = adherence
    payload["llm_summary"] = summarizer.summarize(payload)
    await memory.set(event.episode_id, "outreach", "last_response", payload)

    responded = PatientResponded(
        episode_id=event.episode_id,
        channel="voice",
        payload=payload,
    )
    return HandlerResult(
        summary=payload["llm_summary"],
        episode_status="WAITING_FOR_NEXT_FOLLOWUP",
        next_events=[started, responded],
    )


def _patient_display_name(resource: dict | None) -> str:
    if not resource:
        return "Alex"
    names = resource.get("name") or []
    if names:
        given = names[0].get("given") or []
        if given:
            return str(given[0])[:24]
        family = names[0].get("family")
        if family:
            return str(family)[:24]
    return "Alex"
