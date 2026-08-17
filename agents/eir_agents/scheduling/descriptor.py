from eir_shared.capabilities import Capability
from eir_shared.registry import AgentDescriptor, AgentRiskLevel

DESCRIPTOR = AgentDescriptor(
    name="scheduling",
    version="0.1.0",
    capabilities=[Capability.APPOINTMENT_READ, Capability.APPOINTMENT_SCHEDULE],
    risk_level=AgentRiskLevel.LOW,
    description="Appointment-related recovery actions.",
)
