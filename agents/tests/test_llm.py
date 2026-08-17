import asyncio

from eir_agents.outreach.handler import handle_follow_up
from eir_agents.outreach.llm import TemplateFollowUpSummarizer
from eir_shared.events import FollowUpDue


class FixedSummarizer:
    def summarize(self, payload: dict) -> str:
        return "synthetic clinician summary"


def test_template_summarizer_does_not_invent_diagnosis() -> None:
    text = TemplateFollowUpSummarizer().summarize(
        {"care_plan": "knee recovery", "pain_score": 2, "reported_issue": False}
    )
    assert "pain_score=2" in text
    assert "diagnos" not in text.lower()


def test_outreach_keeps_deterministic_risk_fields() -> None:
    event = FollowUpDue(episode_id="ep-1")
    result = asyncio.run(
        handle_follow_up(
            event,
            patient_id="patient-synthetic-001",
            summarizer=FixedSummarizer(),
        )
    )
    payload = result.next_events[0].payload
    assert payload["pain_score"] == 2
    assert payload["reported_issue"] is False
    assert payload["llm_summary"] == "synthetic clinician summary"
    assert result.summary == "synthetic clinician summary"
