from eir_shared.capabilities import Capability
from eir_shared.registry import AgentDescriptor, AgentRiskLevel

DESCRIPTOR = AgentDescriptor(
    name="outreach",
    version="0.1.0",
    capabilities=[Capability.PATIENT_CONTACT],
    risk_level=AgentRiskLevel.MEDIUM,
    description="Outbound voice, messaging, and conversational follow-up.",
)
