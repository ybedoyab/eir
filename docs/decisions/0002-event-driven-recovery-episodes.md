# ADR 0002: Event-driven recovery episodes

## Status

Accepted

## Context

Recovery lasts days or weeks. A single HTTP request must not run the whole workflow. Patient replies, follow-up timers, and clinician resolutions arrive asynchronously.

## Decision

Model Recovery Episodes as persistent workflows driven by domain events (`RecoveryEpisodeStarted`, `FollowUpDue`, `PatientResponded`, and related types). Domain code depends on an `EventBus` protocol. The first implementation is `InMemoryEventBus`; `GooglePubSubEventBus` can be added without changing publishers.

## Consequences

- API handlers persist state, publish an event, and return.
- Agents and the orchestrator resume from stored episode state plus the next event.
- Local development needs no Pub/Sub.
- Event contracts live in `eir-shared` so backend and agents stay aligned.
