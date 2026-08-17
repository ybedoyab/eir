# Google Cloud — project `eir-ata`

Team-shared config lives in the **repo-root** `.env` (copied from `.env.example`). Do not duplicate env files per package.

## Gemini locally

Local Gemini/ADK calls use `GOOGLE_API_KEY` in `.env` against the Generative Language API. That does not require `gcloud login`. Keep the key only in `.env` (gitignored).

Set `OUTREACH_LLM=true` to let Gemini phrase the outreach summary. Pain score and `reported_issue` stay deterministic in the handler.

## Adapter flags

| Flag | Local default | Notes |
| --- | --- | --- |
| `EVENT_BUS` | `memory` | `pubsub` mirrors events to `PUBSUB_TOPIC`; handlers still run in-process |
| `EPISODE_STORE` | `file` | Writes gitignored `data/`; pytest always uses memory |
| `FHIR_MODE` | `local` | `gcp` uses Healthcare API with fixture fallback |
| `OUTREACH_LLM` | `false` in `.env.example` | Requires `GOOGLE_API_KEY` |

## gcloud for Healthcare API, Pub/Sub, and Cloud Run

```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project eir-ata
```

Intended later wiring:

- Cloud Run for the FastAPI API and a Pub/Sub subscriber worker
- Google Cloud Healthcare API / FHIR R4 (`FHIR_DATASET=eir`, `FHIR_STORE=fhir-r4`)
- Pub/Sub (`PUBSUB_TOPIC=eir-recovery-events`)
- Gemini Enterprise: Agent Registry, Agent Runtime, Memory Bank, Agent Identity, Agent Gateway, Model Armor, Agent Observability
- Secret Manager for any secrets that are not ADC
