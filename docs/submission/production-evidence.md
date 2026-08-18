# Production evidence (synthetic only)

No secrets, phones, credentials, or PHI.

## Current commit

- Repo: `ybedoyab/eir`
- Branch: `main`
- Verified deploy SHA: `79f82f37e9dd1d4d07b09e653de77e50df0f48d4`
- ADK `2.7.1` (not upgraded)
- CI Terraform `1.15.8` (matches the version that wrote remote state)
- `terraform plan -detailed-exitcode`: **exit 0** (CI `terraform-plan` job as `eir-infra-ci`; also verified locally)

A later docs-only commit may retag Cloud Run. Re-check `gcloud run services describe` if `GITHUB_SHA` differs.

## CI

- Run: https://github.com/ybedoyab/eir/actions/runs/32150395022
- `head_sha`: `79f82f37e9dd1d4d07b09e653de77e50df0f48d4`
- Jobs: `terraform`, `terraform-plan`, `backend`, `frontend`, `deploy` — all success
- Do not cite `32145308170` (that run was SHA `6213192`, before `fa1a622`)
- Auth: GitHub OIDC → WIF pool `github-actions` / provider `github`
  - plan: `eir-infra-ci@eir-ata.iam.gserviceaccount.com`
  - deploy: `eir-deploy-ci@eir-ata.iam.gserviceaccount.com`
- Obsolete secret `GCP_SA_KEY` is deleted. Remaining Actions secret: `VOXIMPLANT_CREDENTIALS` (scenario sync only).
- EIR / pytest / Terraform log warnings: **0**
- Third-party Node `DeprecationWarning` lines from `pnpm/action-setup@v5` and `actions/setup-node@v5` (`url.parse`, `punycode`): **4**. Not suppressed. Therefore this run is **not** claimed as `CI warnings: 0`.

## GCP

- Project: `eir-ata` (`658898892127`)
- Region: `us-central1`

## Cloud Run (SHA `79f82f37e9dd1d4d07b09e653de77e50df0f48d4`)

| Service | Ready revision | Image tag |
| --- | --- | --- |
| eir-api | eir-api-00040-rtr | `us-central1-docker.pkg.dev/eir-ata/eir/backend:79f82f37e9dd1d4d07b09e653de77e50df0f48d4` |
| eir-worker | eir-worker-00036-pmx | same backend SHA |
| eir-ui | eir-ui-00035-4jc | `us-central1-docker.pkg.dev/eir-ata/eir/frontend:79f82f37e9dd1d4d07b09e653de77e50df0f48d4` |

No live revision is `:latest`-only.

Worker ingress is `INGRESS_TRAFFIC_INTERNAL_ONLY` (Pub/Sub pull). API/UI remain public.

## Data plane

- FHIR store: `projects/eir-ata/locations/us-central1/datasets/eir/fhirStores/fhir-r4`
- `enableUpdateCreate: true`
- Synthetic Alex cardiology appointment listed via `GET /api/v1/appointments`
- Mutation fixture on SHA `79f82f3` deploy smoke: book → reschedule → cancel
- Firestore `(default)` native, delete protection enabled
- Pub/Sub topic `eir-recovery-events` / subscription `eir-recovery-events-worker`
- Worker log on revision `eir-worker-00036-pmx`: `consumed RecoveryEpisodeStarted episode=875e8953-7a86-4b10-8f90-445842ddf2f1`

## Model Armor

- Template `eir-agent-guard` in `us-central1`
- `/health` `managed_model_armor_available: true`, mode `managed`
- `/health` `platform_verification.managed_model_armor_verified: true`

## WIF

- Pool: `projects/658898892127/locations/global/workloadIdentityPools/github-actions`
- Provider: `.../providers/github`
- Condition: `assertion.repository=='ybedoyab/eir'`

## Observability

- OTel config: `ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS=false` (`/health` `adapters.otel`)
- Cloud Logging `eir-api` request: `GET /health` 200 on `eir-api-00040-rtr`, `trace=projects/eir-ata/traces/c192b5f897a3cd08a8c0a8acff3331c0`, `traceSampled=true`
- Cloud Trace GET of that ID returned HTTP load-balancer + Cloud Run AppServer `/health` spans (status 200). No raw prompt/transcript/FHIR body.
- `/health` `otel_cloud_trace_verified` remains **false** (runtime does not probe the Trace API)
- Cloud Logging `eir-worker`: `consumed RecoveryEpisodeStarted episode=875e8953-7a86-4b10-8f90-445842ddf2f1`
- Dashboard: `projects/658898892127/dashboards/913eb265-2d87-42f6-8cda-cc9684537743` displayName `EIR Healthcare Agent Fleet`
- Alerts enabled: `EIR Cloud Run high 5xx rate`, `EIR Pub/Sub backlog age`

## Terraform

- Backend bucket `eir-ata-terraform-state-658898892127`: versioning on, uniform access, public access prevention enforced
- Apply: **55 imported, 26 added, 7 changed, 0 destroyed** (initial adoption)
- Follow-up applies: telemetry writer IAM (2 add), Agent Registry API (1 add)
- Post-apply / CI plan: **exit 0**, **0 destroys**
- Ownership: Terraform = static infra; `deploy.py --services-only` = image build + Cloud Run revision
- CI drift check uses `eir-infra-ci` (`eir-deploy-ci` cannot read IAM/secrets/WIF)

## Managed Agent Platform

Live 2026-08-18 (synthetic Alex only). No secrets.

| Capability | Status | Evidence |
| --- | --- | --- |
| Agent Runtime | VERIFIED MANAGED | ReasoningEngine `3041998479602745344`; remote query `What appointments do I have?` → tool `get_upcoming_appointments` → Alex cardiology with Dr. Maya Chen, Main Clinic, 2026-08-27T15:00:00Z |
| Managed Sessions | VERIFIED MANAGED | Distinct session IDs `7917773378407104512` and `7561989007844835328` for `patient-synthetic-001` |
| Memory Bank | VERIFIED MANAGED | Attached `contextSpec.memoryBankConfig`; generated fact prefers Main Clinic + afternoon; retrieve API + Session B ranking used those preferences |
| Agent Registry | VERIFIED MANAGED | URN `urn:agent:projects-658898892127:projects:658898892127:locations:us-central1:agentregistry:services:eir-patient-access`; method: standard REST service (not the old eir-api POST). Terraform-imported |
| Agent Identity | VERIFIED MANAGED | `principal://agents.global.proj-658898892127.system.id.goog/resources/aiplatform/projects/658898892127/locations/us-central1/reasoningEngines/3041998479602745344`; Cloud Run invoker only; live tool call recorded that principal |
| Agent Gateway | VERIFIED MANAGED | `projects/eir-ata/locations/us-central1/agentGateways/eir-agent-egress`; mode `AGENT_TO_ANYWHERE`; IAP ENFORCED; native Model Armor `CONTENT_AUTHZ` on `eir-agent-guard`. Same ReasoningEngine `3041998479602745344`. Live query `What appointments do I have?` → tool `get_upcoming_appointments` → Alex cardiology. Cross-patient denied by backend RBAC. Prompt injection did not invoke `cancel_appointment`. |
| Model Armor | VERIFIED MANAGED | Unchanged |
| Agent Observability | VERIFIED GCP | Cloud Logging hit on `/api/v1/agent-runtime/` during the acceptance query |

Obsolete claims removed: Memory Bank is not `/memoryBanks`; Agent Runtime is not blocked on `vertexai` import; empty reasoningEngine shells do not count.


## Voice

No Voximplant call placed. Status remains CONFIGURED UNVERIFIED.
