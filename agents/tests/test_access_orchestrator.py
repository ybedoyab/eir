from eir_agents.access.orchestrator import AccessOrchestrator
from eir_shared.capabilities import Capability


def test_access_orchestrator_routes_booking_intent() -> None:
    plan = AccessOrchestrator().plan("I need a cardiology appointment next week.")
    assert plan.capability == Capability.APPOINTMENT_AVAILABILITY_READ


def test_access_orchestrator_routes_recovery_without_episode() -> None:
    plan = AccessOrchestrator().plan("I need help recovering after surgery")
    assert plan.capability == Capability.RECOVERY_ORCHESTRATE
