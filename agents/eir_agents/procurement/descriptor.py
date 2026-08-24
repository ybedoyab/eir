from eir_shared.capabilities import Capability
from eir_shared.registry import AgentDescriptor, AgentRiskLevel

DESCRIPTOR = AgentDescriptor(
    name="procurement",
    version="0.1.0",
    capabilities=[
        Capability.SUPPLIER_CONTACT,
        Capability.PURCHASE_ORDER_DRAFT,
        Capability.PURCHASE_ORDER_APPROVE,
    ],
    granted_capabilities=[
        Capability.SUPPLIER_CONTACT,
        Capability.PURCHASE_ORDER_DRAFT,
        Capability.PURCHASE_ORDER_APPROVE,
        Capability.INVENTORY_READ,
    ],
    risk_level=AgentRiskLevel.HIGH,
    description="Contacts suppliers by voice, records quotes, and drafts purchase orders.",
    fallback_agent="inventory",
)
