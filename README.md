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

```bash
cp .env.example .env
uv sync --all-packages --all-groups
cd frontend && pnpm install && cd ..
```

Or: `make install`

Never put credentials in git. `.env` is ignored; `.env.example` is not.

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

- FastAPI health and patient/recovery CRUD over in-memory repositories
- Recovery Episode creation publishes `RecoveryEpisodeStarted` and returns without running the full workflow
- Domain events + `InMemoryEventBus`
- Local `AgentRegistry` capability lookup
- Orchestrator delegates by capability (not hardcoded agent classes)
- Safety gate interface for high-risk actions
- Local FHIR client reading synthetic fixtures
- Mock voice provider
- Placeholder Next.js routes
- Structured workflow trace logger

**Explicit stubs (adapters only)**

- Google Cloud Healthcare API / FHIR R4 (local JSON fixtures)
- Pub/Sub (`GooglePubSubEventBus` not implemented)
- Agent Runtime + Memory Bank (in-memory `EpisodeStore` / `AgentMemory`)
- Gemini Live / telephony (`MockVoiceProvider` only)
- Model Armor, Agent Identity, Agent Gateway, Agent Observability (interfaces only)
- No medical diagnosis, no real EHR, no production credentials

## Roadmap for Google Cloud integrations

1. Replace `InMemoryEventBus` with `GooglePubSubEventBus` without changing domain event types.
2. Persist Recovery Episodes in Firestore or Cloud SQL behind the existing repository / `EpisodeStore` protocols.
3. Point the records agent `FhirClient` at Google Cloud Healthcare API (FHIR R4).
4. Map `AgentRegistry` to Gemini Enterprise Agent Registry; run agents on Agent Runtime with Memory Bank.
5. Wire Agent Identity + Agent Gateway for capability authorization, Model Armor + the safety agent for high-risk actions, and Cloud Trace / Cloud Logging for the existing `WorkflowTrace` fields.

## License

Apache License 2.0. See [LICENSE](LICENSE).
