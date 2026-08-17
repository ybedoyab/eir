"""Cross-cutting safety gate.

Later this can combine deterministic policies, model confidence, Model Armor,
and human approval. High-risk actions cannot skip this module.
"""

from __future__ import annotations

from typing import Any

from eir_shared.capabilities import HIGH_RISK_CAPABILITIES
from eir_shared.identity import AgentIdentity, AuthorizationPolicy, PolicyDecision


class SafetyGate:
    def __init__(
        self,
        policy: AuthorizationPolicy | None = None,
        armor: Any | None = None,
    ) -> None:
        self.policy = policy or AuthorizationPolicy()
        self._armor = armor

    def authorize(
        self,
        identity: AgentIdentity,
        capability: str,
        context: dict | None = None,
        agent_risk_level: str | None = None,
    ) -> PolicyDecision:
        del agent_risk_level
        context = context or {}
        if self._armor is not None:
            payload = context.get("payload") or {}
            text = " ".join(str(value) for value in payload.values())
            ingress = self._armor.inspect_ingress(f"{context.get('event_type', '')} {text}")
            if not ingress.allowed:
                return PolicyDecision(allowed=False, reason=ingress.reason)

        decision = self.policy.decide(identity, capability)
        if not decision.allowed:
            return decision

        if capability in HIGH_RISK_CAPABILITIES:
            return PolicyDecision(
                allowed=True,
                requires_human_approval=True,
                reason="safety gate: capability requires clinician approval before execution",
            )
        return PolicyDecision(allowed=True, reason="safety gate: allowed")
