"""Agent Gateway ingress validation."""

from __future__ import annotations

from dataclasses import dataclass

from eir_shared.events import DomainEvent

from app.integrations.enterprise.model_armor import ArmorDecision, ModelArmor


@dataclass(frozen=True)
class GatewayDecision:
    allowed: bool
    reason: str = ""


class AgentGateway:
    def __init__(self, armor: ModelArmor | None = None) -> None:
        self.armor = armor or ModelArmor()

    def authorize_event(self, event: DomainEvent) -> GatewayDecision:
        payload_text = " ".join(str(value) for value in event.payload.values())
        decision: ArmorDecision = self.armor.inspect_ingress(
            f"{event.event_type} {payload_text}"
        )
        if not decision.allowed:
            return GatewayDecision(allowed=False, reason=decision.reason)
        return GatewayDecision(allowed=True, reason="gateway: event allowed")
