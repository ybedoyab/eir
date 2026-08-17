# EIR agents

Google ADK agent skeletons. Independently testable; they do not import FastAPI.

```bash
uv run --package eir-agents pytest agents/tests
uv run adk web agents/eir_agents
```

The orchestrator delegates by **capability** via `AgentRegistry`, not by hardcoded agent classes.
