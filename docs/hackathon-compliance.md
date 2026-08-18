# EIR Healthcare Agent Fleet — compliance matrix

Synthetic data only. No real PHI. Voice is not verified until a paid PSTN/WebRTC call succeeds.

| Requirement | Implementation | Managed Google service | Evidence | Status |
|-------------|------------------|------------------------|----------|--------|
| Gemini 3.5+ | Vertex `gemini-3.5-flash` orchestration + outreach | Vertex AI Gemini | `/health` → `runtime_verification.vertex_model_probe`; worker logs `GoogleLLMVariant.VERTEX_AI` | VERIFIED MANAGED |
| Google ADK | `AdkAgentRunner` + domain tools on Cloud Run | ADK 2.7.1 on Cloud Run worker | `ADK_RUNNER_MODE=adk`, worker telemetry | VERIFIED GCP |
| Cloud Run | `eir-api`, `eir-worker`, `eir-ui` SHA-tagged images | Cloud Run | Deploy pipeline + `/health` | VERIFIED MANAGED |
| Pub/Sub | Recovery event bus | Pub/Sub `eir-recovery-events` | Worker consumed `RecoveryEpisodeStarted` | VERIFIED MANAGED |
| Firestore | Episodes, reviews, access sessions, waitlist | Firestore `(default)` | `episode_store=firestore`, access session reload | VERIFIED MANAGED |
| Cloud Healthcare FHIR | Appointment lifecycle + patient fixtures | FHIR R4 `fhir-r4` (`enableUpdateCreate=true`) | List/search/book/reschedule/cancel on synthetic Alex | VERIFIED GCP |
| Agent Registry | Local `EnterpriseAgentRegistry`; API enabled | Agent Registry | List works; custom Service create returned internal error 13 | BLOCKED |
| Agent Runtime | Custom ADK on Cloud Run | Agent Runtime `reasoningEngines` | API lists; ADK package deploy not completed | BLOCKED |
| Memory Bank | Firestore preference fallback | Memory Bank (Runtime-attached) | `.../memoryBanks` HTTP 404; Firestore fallback | BLOCKED |
| Agent Identity | Demo signed tokens | Agent Identity (target) | `/api/v1/auth/login` | VERIFIED LOCAL |
| Agent Gateway | In-process `AgentGateway` + Model Armor | Agent Gateway (target) | Security demo routes; backend RBAC is final | VERIFIED LOCAL |
| Model Armor | `VertexModelArmorAdapter` | Model Armor `eir-agent-guard` | `/health` → `managed_model_armor_available` | VERIFIED MANAGED |
| Agent Observability / OTel | ADK OTel exporters + Cloud Run logs | Cloud Logging + Cloud Trace | Logging verified; Trace API list empty this sprint | VERIFIED GCP |
| Cloud Trace | ADK GCP exporters + Cloud Run trace fields | Cloud Trace | Log `trace=` present; `traces.list` empty | CONFIGURED UNVERIFIED |
| Cloud Logging | Cloud Run request + worker JSON events | Cloud Logging | `eir-api` HTTP lines; worker `trace_id` JSON | VERIFIED MANAGED |
| Cloud Monitoring | Terraform dashboard + enabled alerts | Cloud Monitoring | Dashboard `EIR Healthcare Agent Fleet`; 5xx + Pub/Sub alerts enabled | VERIFIED GCP |
| Voximplant / Gemini Live voice | Voximplant scenario + synthetic preview | Voximplant + Gemini Live | No paid call verification | CONFIGURED UNVERIFIED |
| Terraform remote state | GCS `eir-ata-terraform-state-658898892127` | Terraform + GCS | `terraform plan -detailed-exitcode` = 0 after apply | VERIFIED GCP |
| CI auth | GitHub OIDC → WIF → `eir-deploy-ci` | Workload Identity Federation | Workflow has no `GCP_SA_KEY` | VERIFIED GCP |

## Fleet modules

- **Patient Access** — web concierge, Firestore sessions, appointment tools (GCP FHIR)
- **Scheduling** — FHIR Schedule/Slot/Appointment lifecycle (GCP)
- **Recovery** — Pub/Sub worker, scheduler follow-ups (verified)
- **Records / Risk / Human Review** — existing recovery + escalation paths
- **Operations** — admin fleet + Cloud Monitoring dashboard

## Explicit non-claims

- No HIPAA compliance claim
- No real patient data
- No autonomous diagnosis
- No verified paid voice call in this sprint
- No verified managed Agent Runtime invocation of Patient Access
- No verified Memory Bank cross-session preference
- Custom Agent Registry registration is not complete
