from eir_shared.capabilities import Capability
from eir_shared.registry import AgentDescriptor, AgentRiskLevel

DESCRIPTOR = AgentDescriptor(
    name="recovery_video",
    version="0.1.0",
    capabilities=[Capability.RECOVERY_VIDEO_GENERATE],
    risk_level=AgentRiskLevel.LOW,
    description=(
        "Generates a short personalized recovery-instruction video from already-approved "
        "care tasks."
    ),
)
