from eir_agents.adherence.handler import check_task_completion
from eir_agents.risk.handler import assess_response
from eir_shared.events import AdherenceConcernDetected, PatientResponded
from eir_shared.supply import InventoryItem


class _Supply:
    def __init__(self, items: list[InventoryItem]) -> None:
        self._items = items

    def get_item(self, sku: str) -> InventoryItem | None:
        return next((item for item in self._items if item.sku == sku), None)

    def list_items(self) -> list[InventoryItem]:
        return list(self._items)


def _catalog() -> list[InventoryItem]:
    return [
        InventoryItem(
            sku="MED-ENOX-40",
            name="Enoxaparin sodium",
            critical=True,
            rxnorm_code="67108",
        ),
        InventoryItem(
            sku="MED-PARA-500",
            name="Paracetamol",
            critical=False,
            rxnorm_code="161",
        ),
    ]


def test_risk_emits_adherence_concern_before_pain_escalation() -> None:
    event = PatientResponded(
        episode_id="ep-1",
        payload={
            "reported_issue": True,
            "pain_score": 8,
            "medication_adherence": "no",
        },
    )
    result = assess_response(event)
    assert [item.event_type for item in result.next_events] == [
        "AdherenceConcernDetected",
        "RiskEscalated",
    ]


def test_risk_stays_low_without_issue() -> None:
    event = PatientResponded(
        episode_id="ep-1",
        payload={"reported_issue": False, "pain_score": 2},
    )
    result = assess_response(event)
    assert result.risk_level == "LOW"
    assert result.next_events == []


def test_risk_records_adherence_no_without_pain_escalation() -> None:
    event = PatientResponded(
        episode_id="ep-1",
        payload={"reported_issue": False, "pain_score": 2, "medication_adherence": "no"},
    )
    result = assess_response(event)
    assert result.risk_level == "LOW"
    assert result.episode_status == "WAITING_FOR_NEXT_FOLLOWUP"
    assert len(result.next_events) == 1
    assert result.next_events[0].event_type == "AdherenceConcernDetected"


def test_adherence_escalates_when_critical_drug_is_skipped() -> None:
    event = AdherenceConcernDetected(
        episode_id="ep-1",
        payload={"medication_adherence": "no"},
    )
    result = check_task_completion(
        event,
        patient_id="patient-synthetic-001",
        supply=_Supply(_catalog()),
    )
    assert result.risk_level == "HIGH"
    assert result.next_events
    assert result.next_events[0].event_type == "RiskEscalated"
    assert result.next_events[0].payload["reason"] == "critical_medication_adherence"


def test_adherence_does_not_escalate_for_non_critical_skip() -> None:
    event = AdherenceConcernDetected(
        episode_id="ep-2",
        payload={"medication_adherence": "no"},
    )
    result = check_task_completion(
        event,
        patient_id="patient-synthetic-002",
        supply=_Supply(_catalog()),
    )
    assert result.risk_level == "LOW"
    assert result.next_events == []
    assert result.episode_status == "WAITING_FOR_NEXT_FOLLOWUP"
