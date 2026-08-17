import asyncio

from eir_agents.outreach.handler import handle_follow_up
from eir_agents.risk.handler import assess_response
from eir_shared.events import FollowUpDue, PatientResponded


def test_outreach_uses_synthetic_care_plan() -> None:
    event = FollowUpDue(episode_id="ep-1")
    result = asyncio.run(handle_follow_up(event, patient_id="patient-synthetic-001"))
    assert result.next_events
    responded = result.next_events[0]
    assert isinstance(responded, PatientResponded)
    assert responded.payload["synthetic"] is True
    assert responded.payload["reported_issue"] is False


def test_risk_escalates_on_reported_issue() -> None:
    event = PatientResponded(
        episode_id="ep-1",
        payload={"reported_issue": True, "pain_score": 8},
    )
    result = assess_response(event)
    assert result.risk_level == "HIGH"
    assert result.next_events[0].event_type == "RiskEscalated"


def test_risk_stays_low_without_issue() -> None:
    event = PatientResponded(
        episode_id="ep-1",
        payload={"reported_issue": False, "pain_score": 2},
    )
    result = assess_response(event)
    assert result.risk_level == "LOW"
    assert result.next_events == []
