# EIR GCP infrastructure (Terraform)

Declarative source of truth for project `eir-ata` / region `us-central1`.

## Bootstrap (once)

```bash
cd infra/terraform/bootstrap
./bootstrap.sh
```

Creates GCS bucket `eir-ata-terraform-state-658898892127` with versioning and uniform access.

## Init and adopt existing resources

Existing production resources must be **imported**, not recreated:

```bash
cd infra/terraform
terraform init
terraform fmt -check
terraform validate
terraform plan   # after imports resolve
```

Import blocks lived in `imports.tf` and were removed after the 2026-08-18 apply
that adopted existing production resources into GCS remote state.
Do not recreate working resources. New environments start from this module.

## What Terraform owns

- APIs, IAM (runtime / deploy-ci / infra-ci)
- Artifact Registry, Pub/Sub (recovery + ops), Firestore, Healthcare FHIR
- Secret Manager containers + runtime accessor bindings
- Cloud Run service shells (image/env ignored — deploy pipeline updates those)
- Workload Identity Federation for GitHub Actions
- Monitoring dashboard + alert policies

## What deploy.py owns

- Immutable image build/push tagged with `GITHUB_SHA`
- Cloud Run revision rollout with env + secrets
- Production smoke (see `infra/gcp/smoke_production.py`)

## What provision.py owns

- Prerequisites verification
- Gemini runtime probe
- Scheduler target refresh when API URL changes
- Documented exceptions (Agent Platform preview resources under `infra/gcp/agent_platform/`)

## Secret values

Terraform creates secret **containers** only. Add versions outside Terraform:

```bash
gcloud secrets versions add eir-session-secret --data-file=...
```

Never commit secret values to Git or tfvars.
