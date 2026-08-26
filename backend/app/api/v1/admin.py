from typing import Annotated, Any

from eir_shared.auth import DemoRole
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps.auth import require_role
from app.core.deps import get_container
from app.integrations.agents.supply_runtime import WORKFLOW as SUPPLY_WORKFLOW
from app.services.supply_service import SupplyService

router = APIRouter()


class AdminSnapshotResponse(BaseModel):
    appointments: dict[str, int]
    active_recoveries: int
    pending_reviews: int
    waitlist_requests: int = 0
    low_stock_skus: int = 0
    open_replenishments: int = 0
    pending_purchase_approvals: int = 0


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
    # Clinical reviews only; purchase approvals are counted separately below.
    reviews = container.reviews.list(pending_only=True, workflow="recovery")
    waitlist = 0
    operational = getattr(container, "operational", None)
    if operational is not None:
        waitlist = len(operational.list_waitlist())
    supply = SupplyService(container.supply)
    purchase_approvals = container.reviews.list(pending_only=True, workflow=SUPPLY_WORKFLOW)
    snapshot = container.appointments.operations_snapshot()
    waitlist = max(waitlist, int(snapshot.get("waitlist_requests") or 0))
    return AdminSnapshotResponse(
        appointments=snapshot,
        active_recoveries=len(recoveries),
        pending_reviews=len(reviews),
        waitlist_requests=waitlist,
        low_stock_skus=len(supply.low_stock_items()),
        open_replenishments=len(supply.open_cases()),
        pending_purchase_approvals=len(purchase_approvals),
    )
