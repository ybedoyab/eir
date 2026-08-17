from fastapi import APIRouter

from app.api.v1 import patients, recovery

router = APIRouter()
router.include_router(patients.router, prefix="/patients", tags=["patients"])
router.include_router(recovery.router, prefix="/recovery", tags=["recovery"])
