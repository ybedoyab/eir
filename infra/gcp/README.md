# Google Cloud — project `eir-ata`

Team-shared config lives in the **repo-root** `.env` (copied from `.env.example`). Do not duplicate env files per package.

## Provision (idempotent)

Requires `gcloud` logged in as a project owner/editor:

```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project eir-ata
uv run python infra/gcp/provision.py
uv run --package eir-backend --directory backend python -m app.seed_fhir
```

This enables Pub/Sub, Healthcare, and Firestore APIs, then creates:

- Topic `eir-recovery-events` and subscription `eir-recovery-events-worker`
- Firestore native database `(default)` in `us-central1`
- Healthcare dataset `eir` / FHIR R4 store `fhir-r4`

Seed synthetic FHIR fixtures (transaction bundle; server assigns resource ids, app resolves patients by identifier):

```bash
uv run --package eir-backend --directory backend python -m app.seed_fhir
```

Never upload real PHI.

## Gemini locally

Local Gemini/ADK calls use `GOOGLE_API_KEY` in `.env` against the Generative Language API. That does not require `gcloud login`. Keep the key only in `.env` (gitignored).

Set `OUTREACH_LLM=true` to let Gemini phrase the outreach summary. Pain score and `reported_issue` stay deterministic in the handler.

## Adapter flags

| Flag | Safe default | Notes |
| --- | --- | --- |
| `EVENT_BUS` | `memory` | `pubsub` mirrors events to `PUBSUB_TOPIC`; handlers still run in-process unless `WORKFLOW_SUBSCRIBER=pubsub` |
| `EPISODE_STORE` | `file` | `firestore` uses native Firestore; pytest always uses memory |
| `FHIR_MODE` | `local` | `gcp` uses Healthcare API |
| `FHIR_FALLBACK` | `true` | If true, empty/missing FHIR resources fall back to `/mocks/fhir` |
| `OUTREACH_LLM` | `false` in `.env.example` | Requires `GOOGLE_API_KEY` |
| `WORKFLOW_SUBSCRIBER` | `local` | Set `pubsub` on the API only when the worker owns `--handle` |

## Worker

Audit consumer (does not re-run the recovery loop):

```bash
uv run --package eir-backend --directory backend python -m app.worker
```

Do not pass `--handle` while the API still has `WORKFLOW_SUBSCRIBER=local`. That would process the same event twice.

## Later

- Cloud Run for the FastAPI API and the Pub/Sub worker
- Gemini Enterprise: Agent Registry, Agent Runtime, Memory Bank, Agent Identity, Agent Gateway, Model Armor, Agent Observability
- Secret Manager for any secrets that are not ADC
