from eir_agents.registry.bootstrap import default_registry
from eir_shared.capabilities import Capability


def test_find_scheduling_by_capability() -> None:
    registry = default_registry()
    found = registry.find_by_capability(Capability.APPOINTMENT_SCHEDULE)
    assert found is not None
    assert found.name == "scheduling"
    assert Capability.APPOINTMENT_SCHEDULE in found.capabilities
