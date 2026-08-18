from eir_shared.capabilities import Capability
from eir_shared.registry import AgentDescriptor, AgentRiskLevel

DESCRIPTOR = AgentDescriptor(
    name="scheduling",
    version="0.1.0",
    capabilities=[
        Capability.APPOINTMENT_READ,
        Capability.APPOINTMENT_AVAILABILITY_READ,
        Capability.APPOINTMENT_BOOK,
        Capability.APPOINTMENT_RESCHEDULE,
        Capability.APPOINTMENT_CANCEL,
        Capability.APPOINTMENT_WAITLIST,
        Capability.APPOINTMENT_SCHEDULE,
    ],
    risk_level=AgentRiskLevel.LOW,
    description="Appointment lifecycle for hospital access and recovery follow-up.",
)
