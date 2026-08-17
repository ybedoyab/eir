"""Cross-cutting safety gate.

Later this can combine deterministic policies, model confidence, Model Armor,
and human approval. High-risk actions cannot skip this module.
"""

from eir_shared.capabilities import HIGH_RISK_CAPABILITIES
from eir_shared.identity import AgentIdentity, AuthorizationPolicy, PolicyDecision
from eir_shared.registry import AgentRiskLevel


class SafetyGate:
    def __init__(self, policy: AuthorizationPolicy | None = None) -> None:
        self.policy = policy or AuthorizationPolicy()

    def authorize(
        self,
        identity: AgentIdentity,
        capability: str,
        context: dict | None = None,
        agent_risk_level: str | None = None,
    ) -> PolicyDecision:
        del context  # reserved for Model Armor / uncertainty features
        decision = self.policy.decide(identity, capability)
        if not decision.allowed:
            return decision

        high_risk = capability in HIGH_RISK_CAPABILITIES or agent_risk_level in {
            AgentRiskLevel.HIGH,
            AgentRiskLevel.CRITICAL,
        }
        if high_risk:
            return PolicyDecision(
                allowed=True,
                requires_human_approval=True,
                reason="safety gate: high-risk action requires human approval path",
            )
        return PolicyDecision(allowed=True, reason="safety gate: allowed")
