# EIR backend

FastAPI service for patients, recovery episodes, and domain events.

```bash
uv run --package eir-backend uvicorn app.main:app --reload --app-dir backend --port 8000
```

Agents are a separate package and are not imported here. See the root README.
