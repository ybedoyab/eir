# Google Cloud — project `eir-ata`

Team-shared config lives in the **repo-root** `.env` (copied from `.env.example`). Do not duplicate env files per package.

## Gemini locally

Local Gemini/ADK calls use `GOOGLE_API_KEY` in `.env` against the Generative Language API. That does not require `gcloud login`. Keep the key only in `.env` (gitignored).

## Later GCP adapters

`gcloud` is needed when wiring Healthcare API, Pub/Sub, Cloud Run, and Gemini Enterprise:

```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project eir-ata
```

Intended later wiring:

- Cloud Run for the FastAPI API and (optionally) ADK API server
- Google Cloud Healthcare API / FHIR R4 (`FHIR_DATASET=eir`, `FHIR_STORE=fhir-r4`)
- Pub/Sub (`PUBSUB_TOPIC=eir-recovery-events`)
- Gemini Enterprise: Agent Registry, Agent Runtime, Memory Bank, Agent Identity, Agent Gateway, Model Armor, Agent Observability
- Secret Manager for any secrets that are not ADC

Local development still uses in-memory adapters and `/mocks` until those adapters are implemented.
