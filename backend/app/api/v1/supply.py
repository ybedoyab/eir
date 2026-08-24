"""Replenishment cases and purchase authorization.

The HTTP layer persists and publishes. Agents run in SupplyWorkflowRuntime, so
nothing here calls a procurement handler directly.
"""

from typing import Annotated, Any

from eir_shared.auth import DemoRole
from eir_shared.events import SupplyApprovalGranted
from eir_shared.supply import ReplenishmentCase, ReplenishmentStatus
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from app.api.deps.auth import require_role
from app.core.config import settings
from app.core.deps import get_container
from app.integrations.agents.supply_runtime import WORKFLOW
from app.repositories.review_repository import HumanReview, ReviewStatus
from app.services.stock_monitor import StockMonitor
from app.services.supply_service import SupplyService

router = APIRouter()

AdminOrClinician = Annotated[
    dict[str, Any],
    Depends(require_role(DemoRole.OPERATIONS_ADMIN, DemoRole.CLINICIAN)),
]
OperationsAdmin = Annotated[
    dict[str, Any],
    Depends(require_role(DemoRole.OPERATIONS_ADMIN)),
]


class ApprovePurchaseRequest(BaseModel):
    note: str = ""


class CancelCaseRequest(BaseModel):
    reason: str = ""


def _service() -> SupplyService:
    return SupplyService(get_container().supply)


def _monitor() -> StockMonitor:
    container = get_container()
    return StockMonitor(container.supply, idempotency=container.scheduler_idempotency)


def _pending_approval(case_id: str) -> HumanReview | None:
    container = get_container()
    for review in container.reviews.list(pending_only=True, workflow=WORKFLOW):
        if review.episode_id == case_id and review.pending_capability:
            return review
    return None


@router.get("/cases", response_model=list[ReplenishmentCase])
def list_cases(_claims: AdminOrClinician, open_only: bool = False) -> list[ReplenishmentCase]:
    service = _service()
    return service.open_cases() if open_only else service.list_cases()


@router.get("/approvals", response_model=list[HumanReview])
def list_approvals(_claims: AdminOrClinician, pending: bool = True) -> list[HumanReview]:
    return get_container().reviews.list(pending_only=pending, workflow=WORKFLOW)


@router.get("/cases/{case_id}", response_model=ReplenishmentCase)
def get_case(case_id: str, _claims: AdminOrClinician) -> ReplenishmentCase:
    case = _service().get_case(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Replenishment case not found")
    return case


@router.get("/cases/{case_id}/events")
def list_case_events(case_id: str, _claims: AdminOrClinician) -> list[dict]:
    if _service().get_case(case_id) is None:
        raise HTTPException(status_code=404, detail="Replenishment case not found")
    return [event.model_dump(mode="json") for event in _service().list_events(case_id)]


@router.post("/cases/{case_id}/approve", response_model=ReplenishmentCase)
async def approve_purchase_order(
    case_id: str,
    body: ApprovePurchaseRequest,
    claims: OperationsAdmin,
) -> ReplenishmentCase:
    """Authorize the drafted order.

    Publishes through the event bus rather than placing the order here: the
    deferred capability replays inside the runtime so the placed order carries the
    same audit trail as every other agent action.
    """
    container = get_container()
    case = _service().get_case(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Replenishment case not found")

    review = _pending_approval(case_id)
    if review is None:
        raise HTTPException(
            status_code=409,
            detail="No purchase order on this case is awaiting authorization",
        )

    approved_by = str(claims.get("sub") or claims.get("display_name") or "operations")
    event = SupplyApprovalGranted(
        episode_id=case_id,
        review_id=review.id,
        note=body.note,
        payload={
            "review_id": review.id,
            "note": body.note,
            "approved_by": approved_by,
        },
    )
    container.supply.append_event(case_id, event)
    await container.event_bus.publish(event)

    updated = _service().get_case(case_id)
    if updated is None:
        raise HTTPException(status_code=404, detail="Replenishment case not found")
    return updated


@router.post("/cases/{case_id}/receive", response_model=ReplenishmentCase)
def receive_delivery(case_id: str, _claims: OperationsAdmin) -> ReplenishmentCase:
    case = _service().get_case(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Replenishment case not found")
    received = _service().receive_delivery(case_id)
    if received is None:
        raise HTTPException(
            status_code=409,
            detail="Only a placed purchase order can be received",
        )
    return received


@router.post("/cases/{case_id}/cancel", response_model=ReplenishmentCase)
def cancel_case(
    case_id: str,
    body: CancelCaseRequest,
    _claims: OperationsAdmin,
) -> ReplenishmentCase:
    """Hand a case back to a human buyer and stop the fleet working it."""
    container = get_container()
    case = _service().get_case(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Replenishment case not found")
    if case.status in {ReplenishmentStatus.COMPLETED, ReplenishmentStatus.CANCELLED}:
        return case
    case.status = ReplenishmentStatus.CANCELLED
    case.rationale = body.reason or case.rationale
    container.supply.save_case(case)
    for review in container.reviews.list(pending_only=True, workflow=WORKFLOW):
        if review.episode_id != case_id:
            continue
        review.status = ReviewStatus.RESOLVED
        review.note = body.reason or "case cancelled by operations"
        container.reviews.save(review)
    return case


@router.post("/process-due-stock")
async def process_due_stock(
    scheduler_token: str | None = Header(default=None, alias="X-Scheduler-Token"),
    idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
) -> dict:
    """Cloud Scheduler entry point. Same claim path as every other trigger."""
    if settings.scheduler_secret and scheduler_token != settings.scheduler_secret:
        raise HTTPException(status_code=401, detail="Invalid scheduler token")
    container = get_container()
    events = _monitor().process_due(idempotency_key=idempotency_key)
    for event in events:
        await container.event_bus.publish(event)
    return {
        "processed": len(events),
        "cases": [event.episode_id for event in events],
        "skus": [event.sku for event in events],
        "idempotency_key": idempotency_key or "generated",
    }
