from eir_shared.capabilities import Capability
from eir_shared.registry import AgentDescriptor, AgentRiskLevel

DESCRIPTOR = AgentDescriptor(
    name="adherence",
    version="0.1.0",
    capabilities=[Capability.ADHERENCE_CHECK],
    risk_level=AgentRiskLevel.LOW,
    description="Checks whether prescribed recovery tasks were completed.",
)
