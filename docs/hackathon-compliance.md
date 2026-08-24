# EIR Healthcare Agent Fleet — compliance matrix

Synthetic data only. No real PHI. Voice is not verified until a paid PSTN/WebRTC call succeeds.

| Requirement | Implementation | Managed Google service | Evidence | Status |
|-------------|------------------|------------------------|----------|--------|
| Gemini 3.5+ | Vertex `gemini-3.5-flash` orchestration + outreach | Vertex AI Gemini | `/health` → `runtime_verification.vertex_model_probe`; worker logs `GoogleLLMVariant.VERTEX_AI` | VERIFIED MANAGED |
| Google ADK | `AdkAgentRunner` + domain tools on Cloud Run | ADK 2.7.1 on Cloud Run worker | `ADK_RUNNER_MODE=adk`, worker telemetry | VERIFIED GCP |
| Cloud Run | `eir-api`, `eir-worker`, `eir-ui` SHA-tagged images | Cloud Run | Deploy pipeline + `/health` | VERIFIED MANAGED |
| Pub/Sub | Recovery + supply event bus | Pub/Sub `eir-recovery-events` | Worker consumed `RecoveryEpisodeStarted` | VERIFIED MANAGED |
| Firestore | Episodes, reviews, access sessions, waitlist, inventory + replenishment cases | Firestore `(default)` | `episode_store=firestore`, access session reload | VERIFIED MANAGED |
| Cloud Healthcare FHIR | Appointment lifecycle + patient fixtures | FHIR R4 `fhir-r4` (`enableUpdateCreate=true`) | List/search/book/reschedule/cancel on synthetic Alex | VERIFIED GCP |
| Agent Registry | `google_agent_registry_service.patient_access` → live Agent resource | Agent Registry | URN `urn:agent:projects-658898892127:projects:658898892127:locations:us-central1:agentregistry:services:eir-patient-access` | VERIFIED MANAGED |
| Agent Runtime | ADK `AdkApp` on ReasoningEngine `3041998479602745344` | Agent Runtime | Remote `async_stream_query` → `get_upcoming_appointments` → GCP FHIR Alex cardiology 2026-08-27 | VERIFIED MANAGED |
| Memory Bank | ReasoningEngine `contextSpec.memoryBankConfig` | Memory Bank | Session A preference generated; retrieve + Session B used Main Clinic / afternoon | VERIFIED MANAGED |
| Agent Identity | `identity_type=AGENT_IDENTITY` STS token | Agent Identity | `last_authenticated_principal` matches engine SPIFFE / principal | VERIFIED MANAGED |
| Agent Gateway | Google-managed `eir-agent-egress` (`AGENT_TO_ANYWHERE`) + in-process SafetyGate secondary | Agent Gateway | Live query Runtime → Gateway → eir-api → FHIR; IAP ENFORCED | VERIFIED MANAGED |
| Model Armor | `VertexModelArmorAdapter` | Model Armor `eir-agent-guard` | `/health` → `managed_model_armor_available` | VERIFIED MANAGED |
| Agent Observability / OTel | ADK OTel exporters + Cloud Run logs | Cloud Logging + Cloud Trace | Request logs + Cloud Run `/health` spans in Trace | VERIFIED GCP |
| Cloud Trace | Cloud Run request traces ingested | Cloud Trace | Trace `c192b5f897a3cd08a8c0a8acff3331c0` GET returned spans | VERIFIED GCP |
| Cloud Logging | Cloud Run request + worker JSON events | Cloud Logging | `eir-api` HTTP lines; worker `consumed RecoveryEpisodeStarted` | VERIFIED MANAGED |
| Cloud Monitoring | Terraform dashboard + enabled alerts | Cloud Monitoring | Dashboard `EIR Healthcare Agent Fleet`; 5xx + Pub/Sub alerts enabled | VERIFIED GCP |
| Voximplant / Gemini Live voice | Voximplant scenario + synthetic preview | Voximplant + Gemini Live | No paid call verification | CONFIGURED UNVERIFIED |
| Terraform remote state | GCS `eir-ata-terraform-state-658898892127` | Terraform + GCS | `terraform plan -detailed-exitcode` = 0 after apply | VERIFIED GCP |
| CI auth | GitHub OIDC → WIF → `eir-deploy-ci` | Workload Identity Federation | Workflow has no `GCP_SA_KEY` | VERIFIED GCP |

## Fleet modules

- **Patient Access** — web concierge, Firestore sessions, appointment tools (GCP FHIR)
- **Scheduling** — FHIR Schedule/Slot/Appointment lifecycle (GCP)
- **Recovery** — Pub/Sub worker, scheduler follow-ups (verified)
- **Records / Risk / Human Review** — existing recovery + escalation paths
- **Supply & Replenishment** — stock monitor, inventory + procurement agents, supplier voice,
  purchase authorization gated on a human (synthetic catalog, no real vendors)
- **Operations** — admin fleet + Cloud Monitoring dashboard

## Explicit non-claims

- No HIPAA compliance claim
- No real patient data
- No autonomous diagnosis
- No autonomous purchasing: the procurement agent drafts orders, an operations admin
  authorizes every one, and no order reaches a real supplier
- Supplier calls run on a scripted synthetic provider; no vendor is dialled and the
  catalog uses reserved fictional phone numbers
- No verified paid voice call in this sprint
- In-process `AgentGateway` / SafetyGate remains a secondary application defense; it is not the Google managed Agent Gateway
- ReasoningEngine packaging is pickle-based; source-based deploy is not the live path and was not required to attach Agent Gateway
