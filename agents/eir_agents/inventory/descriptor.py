from eir_shared.capabilities import Capability
from eir_shared.registry import AgentDescriptor, AgentRiskLevel

DESCRIPTOR = AgentDescriptor(
    name="inventory",
    version="0.1.0",
    capabilities=[Capability.SUPPLY_FORECAST],
    granted_capabilities=[Capability.SUPPLY_FORECAST, Capability.INVENTORY_READ],
    risk_level=AgentRiskLevel.LOW,
    description="Sizes replenishment against usage, lead time, and target stock levels.",
)
