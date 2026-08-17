from eir_shared.capabilities import Capability
from eir_shared.registry import AgentDescriptor, AgentRiskLevel

DESCRIPTOR = AgentDescriptor(
    name="outreach",
    version="0.1.0",
    capabilities=[Capability.PATIENT_CONTACT],
    granted_capabilities=[Capability.PATIENT_CONTACT, Capability.CARE_PLAN_READ],
    risk_level=AgentRiskLevel.MEDIUM,
    description="Outbound voice, messaging, and conversational follow-up.",
    fallback_agent="records",
)
