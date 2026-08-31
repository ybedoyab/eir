<img src="frontend/public/brand/logo-mark.png" alt="EIR logo" width="32" align="left" />

# EIR — Healthcare Agent Fleet

<br clear="left"/>

EIR (Enterprise Intelligence Runtime) is a secure multi-agent hospital operations fleet. Patients can interact through web and future voice to manage routine hospital access workflows such as appointments, reminders, recovery follow-up, and safe staff handoff, while clinicians and operations staff use dedicated workspaces.

Recovery remains a first-class longitudinal module inside the broader fleet. Supply & Replenishment is a second long-running workflow for hospital inventory and procurement operations.

## Try EIR live

Production demo:

https://eir-ui-658898892127.us-central1.run.app/

Demo personas:

| Role | User | Password |
|---|---|---|
| Patient | `alex` | `demo-alex` |
| Clinician | `clinician` | `demo-clinician` |
| Operations Admin | `admin` | `demo-admin` |

Recommended walkthrough:

1. Sign in as Alex Rivera and open **Appointments**.
2. Open **Ask EIR** and try `What appointments do I have?`
3. Switch to Dr. Maya Chen to inspect the clinician schedule and human reviews.
4. Switch to Operations Admin to inspect Fleet and Observability.
5. Open `/demo` for the guided Recovery workflow.

All patients, appointments, clinical events, inventory, and supplier data are synthetic.

## Architecture overview

```text
Patient channels (Web / Voice)          Cloud Scheduler
        |                                      |
        v                                      v
Patient Access Agent                     Stock Monitor
        |                                      |
        v                                      v
Capability Router / Registry  <---------  Supply Orchestrator
 |         |         |         |            |            |
 v         v         v         v            v            v
Sched.  Recovery  Records  Care Nav.    Inventory   Procurement
 |         |         |                      |            |
 v         v         v                      v            v
FHIR    Outreach    FHIR                 Forecast   Supplier voice
Slots   Risk                                             |
        Adherence                                        v
                                                  Purchase order
        |                                                |
        +------------------+-----------------------------+
                           v
             Safety / Identity / Human Handoff
                           v
             Clinician + Operations Workspaces
```

Recovery is a longitudinal workflow module. Patient Access is the hospital front door. The scheduling agent owns appointment lifecycle. FHIR remains the system-of-record abstraction. Voice and web call the same domain services.

Supply & Replenishment is a sibling workflow on the same platform. It reuses the capability registry, safety controls, observability, and human-review patterns, but owns its own runtime and operational state. Stock is operational data and does not touch FHIR. Procurement agents may draft purchase orders, but an operations admin must authorize every critical purchase action.

See:

- [`docs/architecture/overview.md`](docs/architecture/overview.md)
- [`docs/architecture/eir-gcp.mmd`](docs/architecture/eir-gcp.mmd)
- [`docs/hackathon-compliance.md`](docs/hackathon-compliance.md)
- [`docs/research/hospital-fleet-evidence.md`](docs/research/hospital-fleet-evidence.md)

## Managed Google Agent Platform

The hosted Patient Access path uses Google's managed agent stack:

- **Gemini 3.5 Flash** for agent reasoning and orchestration
- **Google ADK** for agent implementation
- **Agent Runtime** for the managed Patient Access agent
- **Memory Bank** for cross-session context
- **Agent Registry** for managed agent and service registration
- **Agent Identity** for least-privilege agent authentication
- **Agent Gateway** in `AGENT_TO_ANYWHERE` mode with IAP enforcement
- **Model Armor** for managed content protection
- **Cloud Logging, Cloud Trace, and Cloud Monitoring** for observability

The live managed path is:

```text
Patient
  |
  v
Patient Access Agent
  |
  v
Managed Agent Runtime
  |
  v
Agent Gateway + Agent Identity + Model Armor
  |
  v
eir-api on Cloud Run
  |
  v
AppointmentService / domain services
  |
  v
Cloud Healthcare API (FHIR R4)
```

Memory Bank has been verified across separate sessions using synthetic patient preferences such as preferred clinic and time of day.

## Product modules

### Patient Access

Patients can:

- View upcoming appointments
- Search availability
- Book appointments
- Reschedule appointments
- Cancel appointments
- Join waitlists
- Use Ask EIR for conversational hospital access
- Enter or continue Recovery workflows

### Clinician Workspace

Clinicians can:

- View today's and upcoming schedule
- Review patients
- Inspect Recovery escalations
- Resolve human review items
- See structured, synthetic patient context

### Operations Command Center

Operations users can:

- Monitor hospital appointment activity
- Inspect patients and operational queues
- Inspect the logical agent fleet
- Inspect the managed Google Agent Platform
- View observability and system status
- Review supply and replenishment workflows

### Recovery

Recovery is a durable workflow that may last days or weeks.

It supports:

- Scheduled follow-ups
- Outreach
- Structured adherence checks
- Risk signal evaluation
- Human escalation
- Clinician review
- Long-running resumption through Pub/Sub and Cloud Scheduler
- Optional personalized recovery videos generated with Vertex AI Veo from already-approved care tasks

EIR does not autonomously diagnose patients.

### Supply & Replenishment

Supply & Replenishment applies the same fleet architecture to hospital operations.

It supports:

- Inventory monitoring
- Low-stock events
- Forecasting
- Procurement agent workflows
- Synthetic supplier outreach
- Purchase-order drafting
- Human approval before critical purchasing actions

No real vendors are contacted in the demo.

## Repository structure

```text
eir/
├── frontend/     Role-based patient, clinician, and admin workspaces
├── backend/      FastAPI API, domain services, adapters
├── agents/       Google ADK agents and capability registry
├── shared/       Events, capabilities, contracts
├── mocks/        Synthetic FHIR, hospital scheduling, and inventory fixtures
├── docs/         Architecture, research, compliance, and ADRs
└── infra/        GCP, Terraform, CI/CD, and Voximplant provisioning
```

## Prerequisites

For local development:

- Python 3.12+
- `uv`
- Node.js
- `pnpm`
- Git

Google Cloud credentials are not required for the default local fallback configuration.

Managed Google Cloud integrations require access to a configured Google Cloud project and Application Default Credentials.

## Quick start

Clone the repository:

```bash
git clone https://github.com/ybedoyab/eir.git
cd eir
```

Create the local environment file:

```bash
cp .env.example .env
```

For a basic local demo, the defaults in `.env.example` use local, file, or in-memory adapters. Set a non-default development session secret:

```text
SESSION_SECRET=replace-with-a-local-development-secret
```

Install dependencies:

```bash
uv sync --all-packages --all-groups

cd frontend
pnpm install --frozen-lockfile
cd ..
```

Start the API in terminal 1:

```bash
uv run --package eir-backend uvicorn app.main:app \
  --reload \
  --app-dir backend \
  --port 8000
```

Start the frontend in terminal 2:

```bash
cd frontend
pnpm dev
```

Then open:

http://localhost:3000

The frontend reads `NEXT_PUBLIC_API_URL=http://localhost:8000` from the root `.env`.

## Demo sign-in users

Local and hosted demo authentication uses synthetic identities.

Password format:

```text
demo-<username>
```

Main personas:

- `alex` → Patient, Alex Rivera
- `clinician` → Clinician, Dr. Maya Chen
- `admin` → Operations Admin

## Google Cloud production architecture

The hosted submission uses:

- Gemini 3.5 Flash
- Google ADK
- Agent Runtime
- Memory Bank
- Agent Registry
- Agent Identity
- Agent Gateway
- Model Armor
- Cloud Run
- Cloud Healthcare API with FHIR R4
- Firestore
- Pub/Sub
- Cloud Scheduler
- Secret Manager
- Artifact Registry
- Cloud Logging
- Cloud Trace
- Cloud Monitoring
- Vertex AI Veo
- Terraform
- Workload Identity Federation

Infrastructure is managed declaratively with Terraform wherever supported.

## Synthetic demo data

The demo includes a populated synthetic hospital dataset with:

- 12 patients
- 6 practitioners
- 5 healthcare services
- 3 locations
- 80+ appointment slots
- 20+ appointments
- Recovery episodes
- Human review items
- Waitlist requests
- Synthetic inventory and procurement data

No real patient information is used.

## Tests

Backend:

```bash
uv run --package eir-backend --group dev pytest backend/tests
```

Agents:

```bash
uv run --package eir-agents --group dev pytest agents/tests
```

Lint:

```bash
uv run ruff check shared backend agents infra/gcp
```

Frontend:

```bash
cd frontend
pnpm typecheck
pnpm lint
pnpm build
```

Terraform:

```bash
cd infra/terraform
terraform fmt -check -recursive
terraform validate
terraform plan -detailed-exitcode
```

Production browser and API smoke tests are also run through CI.

## Terraform

Google Cloud infrastructure is managed from:

```text
infra/terraform/
```

Bootstrap the Terraform remote state bucket once:

```bash
cd infra/terraform/bootstrap
./bootstrap.sh
```

Then:

```bash
cd ..
terraform init
terraform fmt -check -recursive
terraform validate
terraform plan
```

See:

[`infra/terraform/README.md`](infra/terraform/README.md)

Terraform remote state is stored in GCS.

## Production deploy

GitHub Actions on `main` uses Workload Identity Federation. No long-lived Google Cloud service-account JSON key is required by CI.

The deployment pipeline:

1. Runs backend, agent, frontend, Terraform, and lint checks.
2. Builds immutable SHA-tagged container images.
3. Deploys Cloud Run services.
4. Seeds synthetic FHIR and operational demo data.
5. Runs production API smoke tests.
6. Runs production browser QA.
7. Checks Terraform drift.

Manual equivalent:

```bash
GITHUB_SHA=$(git rev-parse HEAD) \
  uv run python infra/gcp/deploy.py --services-only

uv run --package eir-backend python -m app.seed_fhir
uv run python infra/gcp/smoke_production.py
```

## Safety and privacy

EIR is a hackathon prototype using synthetic data only.

The project intentionally does not claim:

- HIPAA compliance
- Production hospital deployment
- Use of real patient data
- Autonomous medical diagnosis
- Autonomous approval of critical purchases

Safety boundaries include:

- Backend RBAC
- Agent Identity
- Agent Gateway with IAP enforcement
- Model Armor
- Capability-based routing
- Deterministic appointment and authorization rules
- Human review for clinical and operational critical actions

Full voice transcripts are not persisted in domain events.

## Voice

The project includes a Voximplant + Gemini Live voice architecture that uses the same backend tools as the web experience.

## Recovery video generation

Recovery can optionally generate short patient-education clips using Vertex AI Veo.

The generated narration is assembled deterministically from already-approved care tasks. The generative video model does not author medication names, doses, diagnoses, or new clinical instructions.

The verified text instructions remain the source of truth.

## Observability

EIR uses:

- Cloud Logging
- Cloud Trace
- Cloud Monitoring
- ADK OpenTelemetry integration

Message content capture is disabled for agent spans.

The system records safe operational metadata such as capability, tool, duration, outcome, and trace identifiers without storing raw patient prompts in observability spans.

## CI/CD

GitHub Actions uses:

```text
GitHub OIDC
    ↓
Workload Identity Federation
    ↓
eir-deploy-ci / eir-infra-ci
    ↓
Google Cloud
```

The repository does not require a long-lived `GCP_SA_KEY` for deployment.

## Hackathon compliance

For a detailed mapping between EIR and the All Things Agentic Hackathon requirements, see:

[`docs/hackathon-compliance.md`](docs/hackathon-compliance.md)

This document distinguishes verified managed integrations from local fallbacks and configured but unverified components.

## License

Apache License 2.0
