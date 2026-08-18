# EIR — Healthcare Agent Fleet

EIR (Enterprise Intelligence Runtime) is a secure multi-agent hospital operations fleet. Patients can interact through web (and future voice) to manage routine hospital access workflows—appointments, reminders, recovery follow-up, and safe staff handoff—while clinicians and operations staff use dedicated workspaces. Recovery remains a first-class longitudinal module inside the broader fleet.

## Architecture overview

```text
Patient channels (Web / Voice)
        ↓
Patient Access Agent
        ↓
Capability Router / Registry
 ┌──────────────┬───────────┬──────────┬─────────────┐
 Scheduling   Recovery     Records    Care Navigation
     ↓            ↓           ↓
 FHIR Slots   Outreach      FHIR
 Appointment  Risk
              Adherence
        ↓
 Safety / Identity / Human Handoff
        ↓
 Clinician + Operations Workspaces
```

Recovery is a longitudinal workflow module. Patient Access is the hospital front door. The scheduling agent owns appointment lifecycle. FHIR remains the system-of-record abstraction. Voice and web call the same domain services.

See [docs/architecture/overview.md](docs/architecture/overview.md) and [docs/research/hospital-fleet-evidence.md](docs/research/hospital-fleet-evidence.md).

## Repository structure

```text
eir/
├── frontend/     Role-based patient, clinician, and admin workspaces
├── backend/      FastAPI API, domain services, adapters
├── agents/       ADK agents and capability registry
├── shared/       Events, capabilities, contracts
├── mocks/        Synthetic FHIR, hospital scheduling fixtures
├── docs/         Architecture, research, ADRs
└── infra/        GCP and Voximplant provisioning
```

## Local setup

```bash
cp .env.example .env
uv sync --all-packages --all-groups
cd frontend && pnpm install && cd ..
```

Add `SESSION_SECRET` to `.env` for demo auth tokens.

## Run

Backend:

```bash
uv run --package eir-backend uvicorn app.main:app --reload --app-dir backend --port 8000
```

Frontend:

```bash
cd frontend && pnpm dev
```

Demo sign-in users (`password` = `demo-<username>`):

- `alex` — patient (Alex Rivera)
- `clinician` — clinician workspace
- `admin` — operations command center

## Tests

```bash
uv run --package eir-backend --group dev pytest backend/tests
uv run --package eir-agents --group dev pytest agents/tests
uv run ruff check shared backend agents
cd frontend && pnpm typecheck && pnpm lint && pnpm build
```

## Terraform (GCP source of truth)

```bash
cd infra/terraform/bootstrap && ./bootstrap.sh
cd .. && terraform init
terraform fmt -check
terraform validate
# Import existing resources using imports.tf, then terraform plan
```

See [infra/terraform/README.md](infra/terraform/README.md).

## Production deploy

GitHub Actions on `main` uses Workload Identity Federation (`eir-deploy-ci`) — no long-lived JSON key required after migration.

```bash
GITHUB_SHA=$(git rev-parse HEAD) uv run python infra/gcp/deploy.py --services-only
uv run --package eir-backend python -m app.seed_fhir
uv run python infra/gcp/smoke_production.py
uv run python infra/gcp/provision.py   # verify + refresh scheduler target
```

Architecture diagram source: [docs/architecture/eir-gcp.mmd](docs/architecture/eir-gcp.mmd).

## Current status

**Hospital access**

- PatientAccessSession domain separate from RecoveryEpisode
- Appointment read / availability / book / reschedule / cancel / waitlist
- Text concierge via `/api/v1/access/sessions`
- Demo RBAC with server-enforced signed sessions
- Role-based portal routes

**Recovery (unchanged pipeline)**

- RecoveryEpisode workflow, orchestrator, voice callback path, risk, escalation, human review

**Privacy**

- Full voice transcripts are not persisted in domain events
- Voice preview keeps ephemeral browser transcript only

**Deferred (Voximplant balance)**

- Live paid PSTN/WebRTC verification

## License

Apache License 2.0
