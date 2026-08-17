FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml ./
COPY shared ./shared
COPY backend ./backend
COPY agents ./agents
COPY mocks ./mocks

RUN uv sync --package eir-backend --no-dev --all-packages

EXPOSE 8000

CMD ["uv", "run", "--package", "eir-backend", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "backend"]
