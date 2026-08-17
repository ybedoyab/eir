FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY shared ./shared
COPY backend ./backend
COPY agents ./agents
COPY mocks ./mocks

RUN uv sync --all-packages --no-dev

ENV PORT=8080

EXPOSE 8080

CMD ["uv", "run", "--package", "eir-backend", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--app-dir", "backend"]
