from eir_agents.orchestrator.handler import RecoveryOrchestrator
from eir_agents.registry.bootstrap import default_registry
from eir_agents.safety.handler import SafetyGate
from eir_shared.capabilities import Capability
from eir_shared.events import AdherenceConcernDetected, FollowUpDue


def test_orchestrator_delegates_follow_up_by_capability() -> None:
    registry = default_registry()
    orchestrator = RecoveryOrchestrator(registry=registry, safety=SafetyGate())
    event = FollowUpDue(episode_id="ep-42")

    decision = orchestrator.delegate("ep-42", event)

    assert decision.allowed is True
    assert decision.capability == Capability.PATIENT_CONTACT
    assert decision.agent_name == "outreach"
    assert decision.event_type == "FollowUpDue"


def test_orchestrator_routes_adherence_while_waiting_for_next_followup() -> None:
    orchestrator = RecoveryOrchestrator(registry=default_registry(), safety=SafetyGate())
    event = AdherenceConcernDetected(episode_id="ep-1")
    capability = orchestrator.plan_capability(
        event,
        {"status": "WAITING_FOR_NEXT_FOLLOWUP"},
    )
    assert capability == Capability.ADHERENCE_CHECK


def test_orchestrator_drops_adherence_when_episode_is_closed() -> None:
    orchestrator = RecoveryOrchestrator(registry=default_registry(), safety=SafetyGate())
    event = AdherenceConcernDetected(episode_id="ep-1")
    assert orchestrator.plan_capability(event, {"status": "ESCALATED"}) is None
    assert orchestrator.plan_capability(event, {"status": "COMPLETED"}) is None
    assert orchestrator.plan_capability(event, {"status": "CANCELLED"}) is None
