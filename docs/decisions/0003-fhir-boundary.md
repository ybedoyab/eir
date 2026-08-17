# ADR 0003: FHIR boundary

## Status

Accepted

## Context

EIR will read and append healthcare data via Google Cloud Healthcare API (FHIR R4). Agents must not couple to a vendor SDK or a live EHR during the scaffold.

## Decision

The records agent owns a `FhirClient` protocol (`get_patient`, `get_encounters`, `get_medications`, `get_care_plan`, `append_follow_up_observation`). `LocalFhirClient` reads synthetic fixtures from `/mocks/fhir`. The backend `integrations/fhir` package is a placeholder only. All fixtures are labeled synthetic.

## Consequences

- FHIR stays behind one interface.
- No real PHI in the repository.
- Swapping in Healthcare API is an adapter change, not an orchestrator change.
- Frontend never talks to FHIR directly.
