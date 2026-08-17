from eir_agents.adherence.descriptor import DESCRIPTOR as ADHERENCE
from eir_agents.escalation.descriptor import DESCRIPTOR as ESCALATION
from eir_agents.orchestrator.descriptor import DESCRIPTOR as ORCHESTRATOR
from eir_agents.outreach.descriptor import DESCRIPTOR as OUTREACH
from eir_agents.records.descriptor import DESCRIPTOR as RECORDS
from eir_agents.registry.service import AgentRegistry
from eir_agents.risk.descriptor import DESCRIPTOR as RISK
from eir_agents.scheduling.descriptor import DESCRIPTOR as SCHEDULING


def default_registry() -> AgentRegistry:
    registry = AgentRegistry()
    for descriptor in (
        ORCHESTRATOR,
        OUTREACH,
        ADHERENCE,
        RISK,
        SCHEDULING,
        RECORDS,
        ESCALATION,
    ):
        registry.register(descriptor)
    return registry
