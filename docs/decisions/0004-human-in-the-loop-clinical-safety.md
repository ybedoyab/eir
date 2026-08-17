# ADR 0004: Human-in-the-loop clinical safety

## Status

Accepted

## Context

EIR must not autonomously diagnose or replace clinicians. High-risk contact, records writes, scheduling writes, and escalation need an explicit policy boundary.

## Decision

All high-risk capabilities pass through a `SafetyGate` that returns a `PolicyDecision` (`allowed`, `requires_human_approval`, `reason`). Agents request capabilities via identity/policy placeholders rather than unrestricted access. The risk and escalation agents may request human review; they must not issue diagnoses. Later this gate can include Model Armor, confidence/uncertainty, and Agent Gateway.

## Consequences

- Orchestrator cannot skip the safety gate for high-risk work.
- Human review is a first-class event (`HumanReviewRequested`).
- A full RBAC product is out of scope for the scaffold.
- Clinical actions remain escalate-and-approve, not silent automation.
