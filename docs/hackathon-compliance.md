# Hackathon compliance matrix (Fortified Enterprise Fleet)

EIR implements a recovery workflow platform with **synthetic FHIR data only**. This document maps requirements to code paths and clearly labels managed Google services vs local fallbacks.

## Gemini / ADK runtime

| Area | Value | Notes |
|------|-------|-------|
| Default model | `gemini-3.5-flash` | `shared/eir_shared/gemini_config.py` |
| Production ADK | `ADK_RUNNER_MODE=adk` | Specialists invoke **domain tools** via ADK (`agents/eir_agents/runtime/domain_tools.py`) |
| Production fallback | `ADK_ALLOW_DIRECT_FALLBACK=false` | ADK failures surface as errors; no silent direct handler bypass |
| Health proof | `/health` → `runtime_verification` | Reports model, ADK probe, enterprise endpoint flag |

## Enterprise Fleet adapters

| Capability | Managed target | Current adapter |
|------------|----------------|-----------------|
| Agent Registry | Gemini Enterprise Agent Registry | `EnterpriseAgentRegistry` (local descriptors + health/fallback) |
| Agent Runtime | Agent Engine / ADK | `AdkAgentRunner` with real domain tools |
| Memory Bank | Agent Engine Memory Bank | `FirestoreAgentMemoryFallback` unless Agent Engine client is wired |
| Model Armor | Vertex Model Armor | `VertexModelArmorAdapter` → `RegexContentGuardFallback` |
| Agent Gateway | Enterprise Gateway | `AgentGateway` ingress checks |
| Observability | Cloud Trace / Agent Observability | Firestore/file structured traces |

## REAL vs fallback (explicit)

| Feature | Status |
|---------|--------|
| FHIR Healthcare API | **REAL** when `FHIR_MODE=gcp` |
| Firestore episode store | **REAL** in production |
| Pub/Sub event bus | **REAL** in split deploy |
| Vertex Gemini (`gemini-3.5-flash`) | **REAL** in production (`GOOGLE_GENAI_USE_VERTEXAI=TRUE`) |
| Agent memory | **Fallback**: Firestore (`FirestoreAgentMemoryFallback`) — not Agent Engine Memory Bank yet |
| Content guard | **Fallback**: regex (`RegexContentGuardFallback`); Vertex adapter attempts managed client |
| Voice outreach | **Synthetic**: `SyntheticVoiceProvider` — not Gemini Live |
| Clinical diagnosis | **Never** performed |

## Workflow guarantees

- **Pre-approval**: when `PolicyDecision.requires_human_approval=true`, the runtime creates a pending review and does **not** invoke domain tools until clinician approval.
- **Longitudinal follow-ups**: episodes enter `WAITING_FOR_NEXT_FOLLOWUP`; Cloud Scheduler calls `POST /api/v1/recovery/process-due-follow-ups` with `X-Scheduler-Token`.
- **Scheduling**: creates a synthetic FHIR R4 `Appointment` via `FhirClient.create_appointment`.

## Demo / ops endpoints

- Manual follow-up: `POST /api/v1/recovery/{id}/follow-up` (creates approval gate for patient contact)
- Scheduler (authenticated): `POST /api/v1/recovery/process-due-follow-ups`
- Health: `GET /health`

## Regression scenarios covered in tests

1. ADK direct fallback disabled in production config (`test_adk_runner_disallows_silent_fallback`)
2. `/health` runtime verification fields (`test_health_reports_runtime_verification`)
3. Scheduler auth + idempotency header (`test_scheduler_endpoint_requires_token`)
4. Outreach tool not invoked before approval (`test_outreach_tool_not_called_before_approval`)
5. Day 0 → Day 7 second follow-up (`test_longitudinal_follow_up_day_0_and_day_7`)
