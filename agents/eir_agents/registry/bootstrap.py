from eir_agents.access.descriptor import DESCRIPTOR as PATIENT_ACCESS
from eir_agents.adherence.descriptor import DESCRIPTOR as ADHERENCE
from eir_agents.escalation.descriptor import DESCRIPTOR as ESCALATION
from eir_agents.inventory.descriptor import DESCRIPTOR as INVENTORY
from eir_agents.orchestrator.descriptor import DESCRIPTOR as ORCHESTRATOR
from eir_agents.outreach.descriptor import DESCRIPTOR as OUTREACH
from eir_agents.procurement.descriptor import DESCRIPTOR as PROCUREMENT
from eir_agents.records.descriptor import DESCRIPTOR as RECORDS
from eir_agents.recovery_video.descriptor import DESCRIPTOR as RECOVERY_VIDEO
from eir_agents.registry.service import AgentRegistry
from eir_agents.risk.descriptor import DESCRIPTOR as RISK
from eir_agents.scheduling.descriptor import DESCRIPTOR as SCHEDULING
from eir_agents.supply.descriptor import DESCRIPTOR as SUPPLY_ORCHESTRATOR


def default_registry() -> AgentRegistry:
    registry = AgentRegistry()
    for descriptor in (
        ORCHESTRATOR,
        PATIENT_ACCESS,
        OUTREACH,
        ADHERENCE,
        RISK,
        SCHEDULING,
        RECORDS,
        RECOVERY_VIDEO,
        ESCALATION,
        SUPPLY_ORCHESTRATOR,
        INVENTORY,
        PROCUREMENT,
    ):
        registry.register(descriptor)
    return registry
