# ADR 0005: Supply workflow as a sibling runtime

## Status

Accepted

## Context

Pharmacy replenishment is a second long-running workflow: stock falls below a
reorder point, suppliers are called, a purchase order is drafted, someone
authorizes it. It needs the same machinery Recovery already has — a capability
registry, a safety gate, an event bus, a human-review queue, an audit trail — but
its state machine has nothing in common with a patient's recovery.

Two options were available: generalize `WorkflowRuntime` over an abstract
aggregate, or stand up a sibling runtime that shares the collaborators.

The forcing constraint is `WorkflowRuntime._handle`: it looks up
`episodes.get(event.episode_id)` and returns silently when nothing matches. Since
`bind()` subscribed to every key in `EVENT_TYPE_MAP`, adding supply events to that
map would have made the recovery runtime swallow them with no trace and no error.

## Decision

Add `SupplyWorkflowRuntime` alongside `WorkflowRuntime` rather than generalizing
it, and split the event bus subscriptions explicitly into `RECOVERY_EVENT_TYPES`
and `SUPPLY_EVENT_TYPES`.

Both runtimes share the agent registry, `SafetyGate`, `AgentGateway`,
`AdkAgentRunner`, the human-review repository, and the checkpoint store. Each owns
its own aggregate (`RecoveryEpisode` vs `ReplenishmentCase`) and its own
orchestrator.

Spend is gated by putting `purchase_order.approve` in
`PRE_APPROVAL_CAPABILITIES`, reusing the deferred-execution path that
`observation.write` already uses on the clinical side: the safety gate parks the
capability, stores the triggering event verbatim on the review, and replays it
only after a person authorizes.

## Consequences

- A change to purchasing cannot regress the recovery demo path, which is the
  verified one.
- The duplication between the two runtimes is real and accepted. If a third
  workflow appears, that is the point to extract a shared base — not before,
  while there are only two and their guard conditions still differ.
- `EVENT_TYPE_MAP` is no longer the subscription list. Any new event must be
  added to exactly one of the two type sets; a test asserts they stay disjoint
  and that each runtime is bound only to its own.
- `HumanReview` gained a `workflow` tag so purchase orders never surface in the
  clinician queue, and `/api/v1/reviews` refuses to resolve them.
- Supply domain models live in `shared/eir_shared/supply.py`, following the
  `appointments.py` precedent, because both the agents package and the backend
  need them typed.
- Supplier voice is a separate protocol from patient outreach voice. Reusing the
  patient provider would have meant widening its synthetic-patient guard to reach
  a vendor, which is exactly the guard worth keeping narrow.
