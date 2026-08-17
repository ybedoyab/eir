from eir_shared.capabilities import Capability
from eir_shared.registry import AgentDescriptor, AgentRiskLevel

DESCRIPTOR = AgentDescriptor(
    name="records",
    version="0.1.0",
    capabilities=[
        Capability.PATIENT_READ,
        Capability.ENCOUNTER_READ,
        Capability.MEDICATION_READ,
        Capability.CARE_PLAN_READ,
        Capability.OBSERVATION_WRITE,
    ],
    granted_capabilities=[
        Capability.PATIENT_READ,
        Capability.CARE_PLAN_READ,
        Capability.OBSERVATION_WRITE,
    ],
    risk_level=AgentRiskLevel.MEDIUM,
    description="FHIR R4 records interface for recovery follow-up.",
)
