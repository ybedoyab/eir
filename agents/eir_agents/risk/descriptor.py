from eir_shared.capabilities import Capability
from eir_shared.registry import AgentDescriptor, AgentRiskLevel

DESCRIPTOR = AgentDescriptor(
    name="risk",
    version="0.1.0",
    capabilities=[Capability.RISK_ASSESS],
    granted_capabilities=[Capability.RISK_ASSESS, Capability.PATIENT_READ],
    risk_level=AgentRiskLevel.HIGH,
    description="Structured risk signals, missing information, and human-review requests.",
)
