# Hackathon compliance matrix (Fortified Enterprise Fleet)

EIR implements a recovery workflow platform with **synthetic FHIR data only**. This document maps requirements to code paths and clearly labels managed Google services vs local fallbacks.

## Gemini / ADK runtime

| Area | Value | Notes |
|------|-------|-------|
| Default model | `gemini-3.5-flash` | `shared/eir_shared/gemini_config.py` |
| Production ADK | `ADK_RUNNER_MODE=adk` | Specialists invoke **domain tools** via ADK (`agents/eir_agents/runtime/domain_tools.py`) |
| Production fallback | `ADK_ALLOW_DIRECT_FALLBACK=false` | ADK failures surface as errors; no silent direct handler bypass |
| Health proof | `/health` → `runtime_verification` | `vertex_model_probe` = Gemini/Vertex model call only; `last_adk_run` = last ADK invocation audit |

## Enterprise Fleet adapters

| Capability | Managed target | Current adapter |
|------------|----------------|-----------------|
| Agent Registry | Gemini Enterprise Agent Registry | `EnterpriseAgentRegistry` (local descriptors + health/fallback) |
| Agent Runtime | Agent Engine / ADK | `AdkAgentRunner` with real domain tools |
| Memory Bank | Agent Engine Memory Bank | `FirestoreAgentMemoryFallback` unless Agent Engine client is wired |
| Model Armor | Vertex Model Armor | **Fallback**: `RegexContentGuardFallback` — SDK import alone does not count as screening |
| Agent Gateway | Enterprise Gateway | `AgentGateway` ingress checks |
| Observability | Cloud Trace / Agent Observability | Firestore/file structured traces |

## REAL vs fallback (explicit)

| Feature | Status |
|---------|--------|
| FHIR Healthcare API | **REAL** when `FHIR_MODE=gcp` |
| Firestore episode store | **REAL** in production |
| Pub/Sub event bus | **REAL** in split deploy |
| Vertex Gemini (`gemini-3.5-flash`) | **REAL** when `GOOGLE_GENAI_USE_VERTEXAI=TRUE` and IAM permits `aiplatform.endpoints.predict` |
| Cloud Scheduler | **REAL** after `infra/gcp/provision.py` (API must be enabled; job targets `/api/v1/recovery/process-due-follow-ups`) |
| Agent memory | **Fallback**: Firestore (`FirestoreAgentMemoryFallback`) — not Agent Engine Memory Bank yet |
| Content guard | **Fallback**: regex (`RegexContentGuardFallback`) |
| Voice outreach | **Synthetic**: `SyntheticVoiceProvider` — not Gemini Live |
| Clinical diagnosis | **Never** performed |

## Workflow guarantees

- **Pre-approval**: only `observation.write` requires clinician approval before domain tools run.
- **Post-action review**: escalation and appointment capabilities still pause the episode via handler results (`HumanReviewRequested`).
- **Proactive outreach**: `patient.contact` runs automatically within an authorized recovery protocol (no clinician gate before every call).
- **Longitudinal follow-ups**: episodes enter `WAITING_FOR_NEXT_FOLLOWUP`; Cloud Scheduler calls `POST /api/v1/recovery/process-due-follow-ups` with `X-Scheduler-Token` (from Secret Manager `eir-scheduler-secret`) plus OIDC.
- **Scheduling**: creates a FHIR R4 `Appointment` via `FhirClient.create_appointment` (server-assigned id on GCP POST).

## Demo / ops endpoints

- Manual follow-up: `POST /api/v1/recovery/{id}/follow-up`
- Scheduler (authenticated): `POST /api/v1/recovery/process-due-follow-ups`
- Health: `GET /health`

## Regression scenarios covered in tests

1. ADK direct fallback disabled in production config (`test_adk_runner_disallows_silent_fallback`)
2. `/health` runtime verification fields (`test_health_reports_runtime_verification`)
3. Scheduler auth + idempotency header (`test_scheduler_endpoint_requires_token`, `test_scheduler_idempotency_rejects_duplicate_run`)
4. Outreach runs without pre-approval (`test_outreach_runs_without_pre_approval`)
5. Day 0 → Day 7 second follow-up (`test_longitudinal_follow_up_day_0_and_day_7`)

## Not claimed

- HIPAA compliance
- Real patient data
- Gemini Live voice (production uses synthetic voice)
- Managed Agent Runtime / Memory Bank / Registry unless explicitly wired and verified
