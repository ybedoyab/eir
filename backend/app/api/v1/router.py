from fastapi import APIRouter

from app.api.v1 import (
    access,
    admin,
    agent_runtime,
    agents,
    appointments,
    auth,
    demo,
    inventory,
    patients,
    recovery,
    reviews,
    runtime,
    security,
    supply,
    traces,
    voice,
)

router = APIRouter()
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(access.router, prefix="/access", tags=["access"])
router.include_router(
    agent_runtime.router, prefix="/agent-runtime", tags=["agent-runtime"]
)
router.include_router(appointments.router, prefix="/appointments", tags=["appointments"])
router.include_router(admin.router, prefix="/admin", tags=["admin"])
router.include_router(inventory.router, prefix="/inventory", tags=["inventory"])
router.include_router(supply.router, prefix="/supply", tags=["supply"])
router.include_router(patients.router, prefix="/patients", tags=["patients"])
router.include_router(recovery.router, prefix="/recovery", tags=["recovery"])
router.include_router(reviews.router, prefix="/reviews", tags=["reviews"])
router.include_router(agents.router, prefix="/agents", tags=["agents"])
router.include_router(traces.router, prefix="/traces", tags=["traces"])
router.include_router(runtime.router, prefix="/runtime", tags=["runtime"])
router.include_router(security.router, prefix="/security", tags=["security"])
router.include_router(demo.router, prefix="/demo", tags=["demo"])
router.include_router(voice.router, prefix="/voice", tags=["voice"])
