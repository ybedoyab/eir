from eir_shared.capabilities import Capability
from eir_shared.registry import AgentDescriptor, AgentRiskLevel

DESCRIPTOR = AgentDescriptor(
    name="escalation",
    version="0.1.0",
    capabilities=[Capability.ESCALATION_REQUEST],
    risk_level=AgentRiskLevel.HIGH,
    description="Generates and dispatches human-review requests.",
)
