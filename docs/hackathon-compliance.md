# EIR Healthcare Agent Fleet — compliance matrix

Synthetic data only. No real PHI. Voice is not verified until a paid PSTN/WebRTC call succeeds.

| Requirement | Implementation | Managed Google service | Evidence | Status |
|-------------|------------------|------------------------|----------|--------|
| Gemini 3.5+ | Vertex `gemini-3.5-flash` orchestration + outreach | Vertex AI Gemini | `/health` → `runtime_verification.vertex_model_probe` | VERIFIED MANAGED |
| Google ADK | `AdkAgentRunner` + domain tools | ADK on Cloud Run worker | `ADK_RUNNER_MODE=adk`, worker telemetry | VERIFIED GCP |
| Cloud Run | `eir-api`, `eir-worker`, `eir-ui` | Cloud Run | Deploy pipeline + `/health` | VERIFIED MANAGED |
| Pub/Sub | Recovery event bus | Pub/Sub `eir-recovery-events` | Worker `--handle`, `/health` adapters | VERIFIED MANAGED |
| Firestore | Episodes, reviews, access sessions, waitlist | Firestore `(default)` | `episode_store=firestore`, access repo | VERIFIED MANAGED |
| Cloud Healthcare FHIR | Appointment lifecycle + patient fixtures | FHIR R4 store `fhir-r4` | `FHIR_MODE=gcp`, `gcp_scheduling.py`, seed | VERIFIED GCP |
| Agent Registry | `EnterpriseAgentRegistry` descriptors | Agent Registry (target) | Admin fleet page | CONFIGURED UNVERIFIED |
| Agent Runtime | Custom ADK Cloud Run runtime | Agent Runtime (target) | `/health` enterprise flags | CONFIGURED UNVERIFIED |
| Memory Bank | Firestore preference fallback | Memory Bank (target) | `agent_memory_adapter` | CONFIGURED UNVERIFIED |
| Agent Identity | Demo signed tokens | Agent Identity (target) | `/api/v1/auth/login` | VERIFIED LOCAL |
| Agent Gateway | `AgentGateway` + Model Armor ingress | Agent Gateway (target) | Security demo routes | CONFIGURED UNVERIFIED |
| Model Armor | `VertexModelArmorAdapter` | Model Armor `eir-agent-guard` | `/health` → `managed_model_armor_available` | VERIFIED MANAGED |
| Agent Observability / OTel | ADK OTel → Cloud Trace | Agent Observability | `adk_otel.py`, deploy env | VERIFIED GCP |
| Cloud Trace | ADK GCP exporters | Cloud Trace | Worker/API startup hook | VERIFIED GCP |
| Cloud Logging | ADK + Cloud Run logs | Cloud Logging | Cloud Run log viewer | VERIFIED MANAGED |
| Cloud Monitoring | Terraform dashboard + alerts | Cloud Monitoring | `infra/terraform/observability.tf` | VERIFIED GCP |
| Voximplant / Gemini Live voice | Voximplant scenario + synthetic preview | Voximplant + Gemini Live | No paid call verification | CONFIGURED UNVERIFIED |

## Fleet modules

- **Patient Access** — web concierge, Firestore sessions, appointment tools
- **Scheduling** — FHIR Schedule/Slot/Appointment lifecycle
- **Recovery** — Pub/Sub worker, scheduler follow-ups (verified)
- **Records / Risk / Human Review** — existing recovery + escalation paths
- **Operations** — admin fleet + observability UI

## Explicit non-claims

- No HIPAA compliance claim
- No real patient data
- No autonomous diagnosis
- No verified paid voice call in this sprint
