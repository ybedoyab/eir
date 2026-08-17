# Hackathon compliance matrix (Fortified Enterprise Fleet)

EIR implements a recovery workflow platform with synthetic FHIR data only. This document maps hackathon requirements to code paths and notes what is fully managed vs local stand-in.

## Gemini model

| Area | Value | Notes |
|------|-------|-------|
| Default model | `gemini-3.5-flash` | `shared/eir_shared/gemini_config.py` |
| Production deploy | Vertex + Enterprise flags | `infra/gcp/deploy.py` |

## Enterprise Fleet adapters

| Capability | Production adapter | Local / fallback |
|------------|-------------------|------------------|
| Agent Registry | `EnterpriseAgentRegistry` | In-memory descriptors with health/lifecycle/fallback |
| Agent Runtime | `AdkAgentRunner` (`adk` mode) | Direct handler invocation in tests |
| Memory Bank | `FirestoreAgentMemory` | `InMemoryAgentMemory` |
| Agent Identity | `granted_capabilities` on descriptors | `AuthorizationPolicy` |
| Agent Gateway | `AgentGateway` + Model Armor ingress | Always on in runtime |
| Model Armor | `ModelArmor` deterministic patterns | Safety gate integration |
| Observability | Firestore / file structured traces | `EnterpriseObservability` span helper |

## REAL vs synthetic

| Feature | Status |
|---------|--------|
| FHIR on GCP Healthcare API | REAL when `FHIR_MODE=gcp` |
| Firestore episode store | REAL in production |
| Pub/Sub event bus | REAL in split deploy |
| Patient outreach telephony | SYNTHETIC (`MockVoiceProvider` / `GeminiVoiceProvider` conversation stub) |
| Clinical diagnosis | NOT performed; escalation uses structured signals only |

## Demo endpoints

- Manual follow-up: `POST /api/v1/recovery/{id}/follow-up`
- Proactive scheduler (Cloud Scheduler target): `POST /api/v1/recovery/process-due-follow-ups`

## Eval scenarios (manual)

1. Prompt injection in event payload → blocked by Model Armor / gateway
2. Jordan Lee (`patient-synthetic-002`) → pain 8 + issue → escalation
3. Alex (`patient-synthetic-001`) → low risk, WAITING
4. Clinician resolve → episode resumes ACTIVE
5. Adherence miss → `AdherenceConcernDetected`
6. Appointment request → human review path
7. Split worker mode → API publishes, worker handles
8. ADK runner mode → handler tool + agent session in production
9. Recovery uncertainty → risk payload includes `uncertain` flags
10. Registry fallback → outreach degrades to records agent
