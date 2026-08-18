from typing import Annotated, Any

from eir_shared.auth import DemoRole
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps.auth import require_role
from app.core.deps import get_container

router = APIRouter()


class AdminSnapshotResponse(BaseModel):
    appointments: dict[str, int]
    active_recoveries: int
    pending_reviews: int
    waitlist_requests: int = 0


AdminOrClinician = Annotated[
    dict[str, Any],
    Depends(require_role(DemoRole.OPERATIONS_ADMIN, DemoRole.CLINICIAN)),
]


@router.get("/snapshot")
def operations_snapshot(_claims: AdminOrClinician) -> AdminSnapshotResponse:
    container = get_container()
    recoveries = [
        item
        for item in container.episodes.list()
        if item.status.value not in {"COMPLETED", "CANCELLED"}
    ]
    reviews = container.reviews.list(pending_only=True)
    waitlist = 0
    operational = getattr(container, "operational", None)
    if operational is not None:
        waitlist = len(operational.list_waitlist())
    snapshot = container.appointments.operations_snapshot()
    waitlist = max(waitlist, int(snapshot.get("waitlist_requests") or 0))
    return AdminSnapshotResponse(
        appointments=snapshot,
        active_recoveries=len(recoveries),
        pending_reviews=len(reviews),
        waitlist_requests=waitlist,
    )
