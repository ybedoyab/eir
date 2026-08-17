.PHONY: install backend frontend test lint provision worker seed-fhir

install:
	uv sync --all-packages --all-groups
	cd frontend && pnpm install

backend:
	uv run --package eir-backend uvicorn app.main:app --reload --app-dir backend --port 8000

frontend:
	cd frontend && pnpm dev

worker:
	uv run --package eir-backend --directory backend python -m app.worker

provision:
	uv run python infra/gcp/provision.py

seed-fhir:
	uv run --package eir-backend --directory backend python -m app.seed_fhir

test:
	uv run --package eir-backend --group dev pytest backend/tests
	uv run --package eir-agents --group dev pytest agents/tests

lint:
	uv run ruff check shared backend agents
	cd frontend && pnpm lint
	cd frontend && pnpm typecheck
