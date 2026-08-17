from eir_shared.capabilities import Capability
from eir_shared.registry import AgentDescriptor, AgentRiskLevel

DESCRIPTOR = AgentDescriptor(
    name="recovery_orchestrator",
    version="0.1.0",
    capabilities=[Capability.RECOVERY_ORCHESTRATE],
    risk_level=AgentRiskLevel.LOW,
    description="Owns Recovery Episode workflow coordination.",
)
