"""EIR FastAPI application.

HTTP handlers persist state and publish events. They do not run the full
recovery workflow in a single request.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as v1_router
from app.core.config import settings
from app.core.deps import get_container
from app.integrations.enterprise.adk_otel import otel_configured, setup_adk_otel


@asynccontextmanager
async def lifespan(_app: FastAPI):
    setup_adk_otel(
        service_name="eir-api",
        project_id=settings.google_cloud_project,
        enabled=settings.adk_otel_enabled,
    )
    get_container().seed()
    yield


app = FastAPI(
    title="EIR API",
    description="EIR — Healthcare Agent Fleet API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router, prefix="/api/v1")


@app.get("/health")
def health() -> dict:
    container = get_container()
    adapters = container.adapter_status()
    adapters["otel"] = {
        "configured": otel_configured(),
        "capture_message_content_in_spans": settings.adk_capture_message_content_in_spans,
    }
    return {
        "status": "ok",
        "project": settings.google_cloud_project,
        "adapters": adapters,
    }
