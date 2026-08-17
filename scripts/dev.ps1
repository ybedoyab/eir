param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("install", "backend", "frontend", "test", "lint")]
    [string]$Command
)

Set-Location (Split-Path -Parent $PSScriptRoot)

switch ($Command) {
    "install" {
        uv sync --all-packages --group dev
        Set-Location frontend
        pnpm install
    }
    "backend" {
        uv run --package eir-backend uvicorn app.main:app --reload --app-dir backend --port 8000
    }
    "frontend" {
        Set-Location frontend
        pnpm dev
    }
    "test" {
        uv run --package eir-backend --group dev pytest backend/tests
        uv run --package eir-agents --group dev pytest agents/tests
    }
    "lint" {
        uv run ruff check shared backend agents
        Set-Location frontend
        pnpm lint
        pnpm typecheck
    }
}
