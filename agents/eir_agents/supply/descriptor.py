from eir_shared.capabilities import Capability
from eir_shared.registry import AgentDescriptor, AgentRiskLevel

DESCRIPTOR = AgentDescriptor(
    name="supply_orchestrator",
    version="0.1.0",
    capabilities=[Capability.SUPPLY_ORCHESTRATE],
    risk_level=AgentRiskLevel.LOW,
    description="Routes replenishment cases to inventory and procurement specialists.",
)
