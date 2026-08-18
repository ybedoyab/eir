from fastapi import APIRouter

from app.api.v1 import agents, demo, patients, recovery, reviews, runtime, security, traces, voice

router = APIRouter()
router.include_router(patients.router, prefix="/patients", tags=["patients"])
router.include_router(recovery.router, prefix="/recovery", tags=["recovery"])
router.include_router(reviews.router, prefix="/reviews", tags=["reviews"])
router.include_router(agents.router, prefix="/agents", tags=["agents"])
router.include_router(traces.router, prefix="/traces", tags=["traces"])
router.include_router(runtime.router, prefix="/runtime", tags=["runtime"])
router.include_router(security.router, prefix="/security", tags=["security"])
router.include_router(demo.router, prefix="/demo", tags=["demo"])
router.include_router(voice.router, prefix="/voice", tags=["voice"])
