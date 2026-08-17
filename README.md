# EIR — Enterprise Intelligence for Recovery

EIR is a longitudinal recovery agent fleet: after a consultation, procedure, or discharge it creates a persistent Recovery Episode that can stay active for days or weeks, proactively contacting the patient, tracking recovery tasks, collecting structured follow-up, escalating when needed, and keeping clinicians informed. It does not autonomously diagnose patients or replace clinicians; high-risk clinical actions require human escalation or approval.

## Architecture overview

The platform is a modular monorepo. A Next.js clinician/operator UI and (later) voice channels talk to a FastAPI API. The API persists Recovery Episodes and publishes domain events. A Recovery Orchestrator inspects episode state, asks a local Agent Registry for the next **capability**, and delegates to specialist agents (outreach, adherence, risk, scheduling, records, escalation). A safety gate sits in front of high-risk actions. External systems (FHIR, Pub/Sub, voice, identity, observability) are accessed only through adapters so local in-memory implementations can be replaced with Google Cloud services later.

```text
Patient / Clinician
        |
        v
Frontend / Voice
        |
        v
Recovery Orchestrator
        |
        v
Agent Registry
        |
  +-----+-----+------+-------+
  |     |     |      |       |
Voice Adherence Risk Records Scheduling
  |                    |
  +---------+----------+
            |
        Safety Layer
            |
       Human Escalation
```

See [docs/architecture/overview.md](docs/architecture/overview.md) for the full diagram and design notes.

## Repository structure

```text
eir/
├── frontend/     Next.js App Router UI (placeholder routes)
├── backend/      FastAPI API, domain models, in-memory repositories
├── agents/       Google ADK agent skeletons + capability registry
├── shared/       Cross-cutting contracts (events, capabilities, protocols)
├── infra/        Dockerfiles and GCP placeholders
├── mocks/        Synthetic FHIR, patients, and events (never real PHI)
├── docs/         Architecture overview and ADRs
└── scripts/      Helper scripts
```

Python packages are a uv workspace: `eir-shared`, `eir-backend`, `eir-agents`. Backend and agents never import each other.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- Node.js 20+
- [pnpm](https://pnpm.io/)
- GNU Make (optional; commands below work without it)
- Docker (optional, for `docker compose`)

## Local setup

There is **one** env file: `.env` at the repo root. Backend, agents, and frontend all read it. Do not add `.env` files inside `frontend/`, `backend/`, or `agents/`.

```bash
cp .env.example .env
uv sync --all-packages --all-groups
cd frontend && pnpm install && cd ..
```

Or: `make install`

Gemini uses `GOOGLE_API_KEY` from local `.env` (no `gcloud login`). Never commit `.env` or the API key.

## How to run the frontend

```bash
cd frontend
pnpm dev
```

Or: `make frontend`

UI: http://localhost:3000

## How to run the backend

```bash
uv run --package eir-backend uvicorn app.main:app --reload --app-dir backend --port 8000
```

Or: `make backend`

API: http://localhost:8000  
Health: http://localhost:8000/health  
Docs: http://localhost:8000/docs

Docker (API + UI): `docker compose up --build`

## How to run agents / tests

Agents are independently testable Python modules. They do not import FastAPI.

```bash
uv run --package eir-backend --group dev pytest backend/tests
uv run --package eir-agents --group dev pytest agents/tests
```

Or: `make test`

ADK CLI (requires `GOOGLE_API_KEY` or Vertex credentials; not needed for unit tests):

```bash
uv run adk web agents/eir_agents
```

Lint:

```bash
uv run ruff check shared backend agents
cd frontend && pnpm lint && pnpm typecheck
```

Or: `make lint`

## Current implementation status

**Functional now**

- FastAPI health, patients, recovery episodes, events, follow-up trigger, reviews, agents, traces
- Creating an episode publishes `RecoveryEpisodeStarted` and returns; follow-up is a later event
- Event bus subscriber (`WorkflowRuntime`) delegates by capability: outreach → risk → escalation
- Synthetic FHIR care plan/observations inform outreach; mock voice records the contact
- Human-review queue for escalation; resolving resumes the episode (`ClinicianResolved`)
- Operator UI lists patients, episodes, agents, traces, and pending reviews
- Optional file persistence (`EPISODE_STORE=file` → gitignored `data/`)
- Optional Pub/Sub mirror (`EVENT_BUS=pubsub`) while handlers still run in-process
- Optional Healthcare API FHIR reads (`FHIR_MODE=gcp`) with local fixture fallback
- Optional Gemini phrasing for outreach (`OUTREACH_LLM=true`); risk fields stay deterministic

**Explicit stubs (adapters only)**

- Pub/Sub subscribe worker (publish-only mirror today)
- Agent Runtime + Memory Bank (file/`EpisodeStore` and in-memory `AgentMemory`)
- Gemini Live / telephony (`MockVoiceProvider` only)
- Model Armor, Agent Identity, Agent Gateway, Agent Observability (interfaces only)
- No medical diagnosis, no real EHR, no production credentials

## Roadmap for Google Cloud integrations

1. Subscribe to Pub/Sub from a Cloud Run / Agent Runtime worker (publish mirror already exists).
2. Persist Recovery Episodes in Firestore or Cloud SQL behind the existing repository / `EpisodeStore` protocols.
3. Provision the Healthcare API FHIR store so `FHIR_MODE=gcp` stops falling back to fixtures.
4. Map `AgentRegistry` to Gemini Enterprise Agent Registry; run agents on Agent Runtime with Memory Bank.
5. Wire Agent Identity + Agent Gateway for capability authorization, Model Armor + the safety agent for high-risk actions, and Cloud Trace / Cloud Logging for the existing `WorkflowTrace` fields.

## License

Apache License 2.0. See [LICENSE](LICENSE).
