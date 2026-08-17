# ADR 0001: Use Google ADK

## Status

Accepted

## Context

EIR is a multi-agent recovery fleet targeting the Fortified Enterprise Fleet track. Agents must be independently testable, deployable to Gemini Enterprise / Agent Runtime later, and free of FastAPI or UI coupling.

## Decision

Implement specialist agents with Google Agent Development Kit (ADK) for Python. Each agent directory exposes `root_agent` for `adk web` / `adk run`. Deterministic coordination and tests live in plain Python handlers, not in HTTP routes or LLM prompts.

## Consequences

- ADK CLI can load agents during development.
- Unit tests do not need to call Gemini.
- Later mapping to Gemini Enterprise Agent Platform is straightforward.
- Prompts stay inside agent modules, never inside API routes.
