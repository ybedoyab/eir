from eir_shared.capabilities import Capability
from eir_shared.registry import AgentDescriptor, AgentRiskLevel

DESCRIPTOR = AgentDescriptor(
    name="patient_access",
    version="0.1.0",
    capabilities=[
        Capability.PATIENT_ACCESS_ORCHESTRATE,
        Capability.APPOINTMENT_READ,
        Capability.APPOINTMENT_AVAILABILITY_READ,
        Capability.CARE_NAVIGATION_READ,
        Capability.HUMAN_HANDOFF_REQUEST,
        Capability.RECOVERY_ORCHESTRATE,
    ],
    risk_level=AgentRiskLevel.LOW,
    description="Front-door hospital access coordinator for administrative patient requests.",
)
