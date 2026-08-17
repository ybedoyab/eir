from eir_agents.orchestrator.handler import RecoveryOrchestrator
from eir_agents.registry.bootstrap import default_registry
from eir_agents.safety.handler import SafetyGate
from eir_shared.capabilities import Capability
from eir_shared.events import FollowUpDue


def test_orchestrator_delegates_follow_up_by_capability() -> None:
    registry = default_registry()
    orchestrator = RecoveryOrchestrator(registry=registry, safety=SafetyGate())
    event = FollowUpDue(episode_id="ep-42")

    decision = orchestrator.delegate("ep-42", event)

    assert decision.allowed is True
    assert decision.capability == Capability.PATIENT_CONTACT
    assert decision.agent_name == "outreach"
    assert decision.event_type == "FollowUpDue"
