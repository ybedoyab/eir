# EIR — Enterprise Intelligence for Recovery

EIR is a longitudinal recovery agent fleet: after a consultation, procedure, or discharge it creates a persistent Recovery Episode that can stay active for days or weeks, proactively contacting the patient, tracking recovery tasks, collecting structured follow-up, escalating when needed, and keeping clinicians informed. It does not autonomously diagnose patients or replace clinicians; high-risk clinical actions require human escalation or approval.

## Architecture overview

The platform is a modular monorepo. A Next.js clinician/operator UI and Voximplant PSTN voice outreach talk to a FastAPI API. The API persists Recovery Episodes and publishes domain events. A Recovery Orchestrator inspects episode state, asks a local Agent Registry for the next **capability**, and delegates to specialist agents (outreach, adherence, risk, scheduling, records, escalation). A safety gate sits in front of high-risk actions. External systems (FHIR, Pub/Sub, voice, identity, observability) are accessed only through adapters so local in-memory implementations can be replaced with Google Cloud services.

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

Python packages are a uv workspace: `eir-shared`, `eir-backend`, `eir-agents`. Agents do not import FastAPI. The backend imports agents only at the composition root (`backend/app/core/deps.py` and `integrations/agents`).

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

- FastAPI health (includes ADK/runtime verification), patients, recovery episodes, events, follow-up trigger, reviews, agents, traces
- ADK runtime executes specialists via **domain tools** (`conduct_outreach`, FHIR reads/writes, scheduling, adherence, escalation)
- Pre-approval gate: only `observation.write` requires clinician approval **before** tools run; outreach/escalation run automatically and pause via post-action reviews when needed
- Episode state `WAITING_FOR_NEXT_FOLLOWUP` supports recurring scheduler-driven follow-ups
- Cloud Scheduler target: authenticated `POST /api/v1/recovery/process-due-follow-ups` (Secret Manager `eir-scheduler-secret` + OIDC)
- Production voice: Voximplant PSTN + Vertex Gemini Live (`gemini-live-2.5-flash-native-audio`). Orchestration remains `gemini-3.5-flash`. `SyntheticVoiceProvider` is local/test fallback. A Web Softphone preview transport (`VOXIMPLANT_VOICE_TRANSPORT` / `callUser`) can validate Gemini Live without PSTN; production Cloud Run stays on PSTN.
- Authenticated async callback `POST /api/v1/voice/voximplant/callback` publishes `PatientResponded` on the existing EventBus
- Synthetic FHIR including Appointment creation on schedule requests
- Optional Vertex Gemini (`gemini-3.5-flash`, `ADK_RUNNER_MODE=adk`, `ADK_ALLOW_DIRECT_FALLBACK=false` in production)

**Explicit fallbacks (labeled in code/docs)**

- Firestore agent memory (`FirestoreAgentMemoryFallback`) — not Agent Engine Memory Bank
- Regex content guard (`RegexContentGuardFallback`) — local/test fallback; production uses managed Model Armor template `eir-agent-guard` in `us-central1` when screening succeeds
- `SyntheticVoiceProvider` — local tests and fallback if `VOICE_PROVIDER` is not `voximplant`

Production stack also exposes shared worker telemetry at `GET /api/v1/runtime/status` and a security demo at `POST /api/v1/security/screen`.

See [docs/hackathon-compliance.md](docs/hackathon-compliance.md) for the REAL vs fallback matrix.

## License

Apache License 2.0. See [LICENSE](LICENSE).
