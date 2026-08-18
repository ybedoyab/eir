# Production evidence (synthetic only)

No secrets, phones, credentials, or PHI.

## Current commit

Recorded at evidence-file authoring time. After merge, Cloud Run images must match `GITHUB_SHA` of the green `main` workflow.

- Repo: `ybedoyab/eir`
- Branch: `main`
- Evidence authored against the Terraform adoption + CI warning-fix tree
- ADK `2.7.1` (not upgraded; Agent Registry packaging needs a later Agent Platform SDK, not a blind ADK bump)
- CI Terraform `1.15.8` (matches the version that wrote remote state)
- `terraform plan -detailed-exitcode` locally: **exit 0** (no drift, 0 destroys)

## CI

- HEAD run to verify after this push (do not cite `32145308170`)
- Required jobs: `terraform`, `backend`, `frontend`, `deploy`
- Auth: GitHub OIDC → WIF pool `github-actions` / provider `github` → `eir-deploy-ci@eir-ata.iam.gserviceaccount.com`
- Obsolete secret `GCP_SA_KEY` deleted from GitHub Actions secrets. `VOXIMPLANT_CREDENTIALS` retained (scenario sync only).

## GCP

- Project: `eir-ata` (`658898892127`)
- Region: `us-central1`

## Cloud Run (pre-this-push revisions used SHA `fa1a622ea842dc61926885951972a96f04c1e961`)

| Service | Ready revision (at verification) | Image tag |
| --- | --- | --- |
| eir-api | eir-api-00039-sl8 | `us-central1-docker.pkg.dev/eir-ata/eir/backend:fa1a622ea842dc61926885951972a96f04c1e961` |
| eir-worker | eir-worker-00035-wtn | same backend SHA |
| eir-ui | eir-ui-00034-b89 | `us-central1-docker.pkg.dev/eir-ata/eir/frontend:fa1a622ea842dc61926885951972a96f04c1e961` |

No service relies solely on `:latest` in the live revision.

Worker ingress is `INGRESS_TRAFFIC_INTERNAL_ONLY` (Pub/Sub pull). API/UI remain public.

## Data plane

- FHIR store: `projects/eir-ata/locations/us-central1/datasets/eir/fhirStores/fhir-r4`
- `enableUpdateCreate: true`
- Synthetic Alex cardiology appointment `appt-alex-cardio-2026-08-27` listed via `GET /api/v1/appointments`
- Cardiology availability returned GCP slots (`slot-cardio-2026-08-25-1430`, Main Clinic)
- Mutation fixture: book → reschedule → cancel on a non-demo slot (`appt-ff4642ffbb` cancelled)
- Firestore `(default)` native, delete protection enabled
- Access session create + reload: `c8909d25-643b-4063-846c-7057781043bb`
- Pub/Sub topic `eir-recovery-events` / subscription `eir-recovery-events-worker`
- Worker log: `consumed RecoveryEpisodeStarted episode=619bb6d1-c49d-46d7-8ab9-7bb5b86fef26`

## Model Armor

- Template `eir-agent-guard` in `us-central1`
- `/health` `managed_model_armor_available: true`, mode `managed`

## WIF

- Pool: `projects/658898892127/locations/global/workloadIdentityPools/github-actions`
- Provider: `.../providers/github`
- Condition: `assertion.repository=='ybedoyab/eir'`

## Observability

- OTel config: `ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS=false`
- Cloud Logging `eir-api`: HTTP 200 for appointments/access; Cloud Run `trace` field example `projects/eir-ata/traces/0e6010404f7e3807efbb8bff794d00cb`
- Cloud Logging `eir-worker` structured event: `trace_id=a9e2b964-94e7-40c9-9a82-d5125c8772f7`, `agent_name=escalation`, `event_type=RiskEscalated`, outcome `delegated`
- Cloud Trace API `traces.list` returned **no stored traces** during this sprint → do not claim Trace ingestion
- Dashboard: `projects/658898892127/dashboards/913eb265-2d87-42f6-8cda-cc9684537743` displayName `EIR Healthcare Agent Fleet` (Cloud Run request/5xx/latency + Pub/Sub unacked age)
- Alerts enabled: `EIR Cloud Run high 5xx rate`, `EIR Pub/Sub backlog age`

## Terraform

- Backend bucket `eir-ata-terraform-state-658898892127`: versioning on, uniform access, public access prevention enforced; `eir-infra-ci` `roles/storage.objectAdmin`
- Apply: **55 imported, 26 added, 7 changed, 0 destroyed** (initial adoption)
- Follow-up applies: telemetry writer IAM (2 add), Agent Registry API (1 add)
- Post-apply: `terraform plan -detailed-exitcode` **exit 0**
- Ownership: Terraform = static infra; `deploy.py` (default / `--services-only`) = image build + Cloud Run revision

## Managed Agent Platform

See `infra/gcp/agent_platform/README.md`.

| Capability | Status |
| --- | --- |
| Agent Registry | BLOCKED (API on; custom Service create internal error 13) |
| Agent Runtime | BLOCKED (API on; ADK package not deployed) |
| Memory Bank | BLOCKED (no Memory Bank API; Firestore fallback) |
| Agent Identity | VERIFIED LOCAL |
| Agent Gateway | VERIFIED LOCAL |
| Model Armor | VERIFIED MANAGED |
| Agent Observability | VERIFIED GCP (logs); Cloud Trace CONFIGURED UNVERIFIED |

## Voice

No Voximplant call placed. Status remains CONFIGURED UNVERIFIED.
