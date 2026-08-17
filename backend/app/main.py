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


@asynccontextmanager
async def lifespan(_app: FastAPI):
    get_container().seed()
    yield


app = FastAPI(
    title="EIR API",
    description="Enterprise Intelligence for Recovery — healthcare recovery fleet API",
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
    return {
        "status": "ok",
        "project": settings.google_cloud_project,
        "adapters": container.adapter_status(),
    }
