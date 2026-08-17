from eir_shared.events import ClinicianResolved
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.deps import get_container
from app.repositories.review_repository import HumanReview, ReviewStatus

router = APIRouter()


class ResolveReviewRequest(BaseModel):
    note: str = ""


@router.get("", response_model=list[HumanReview])
def list_reviews(pending: bool = True) -> list[HumanReview]:
    return get_container().reviews.list(pending_only=pending)


@router.post("/{review_id}/resolve", response_model=HumanReview)
async def resolve_review(review_id: str, body: ResolveReviewRequest) -> HumanReview:
    container = get_container()
    review = container.reviews.get(review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found")
    if review.status == ReviewStatus.RESOLVED:
        return review

    event = ClinicianResolved(
        episode_id=review.episode_id,
        review_id=review.id,
        note=body.note,
        payload={"review_id": review.id, "note": body.note},
    )
    container.episodes.append_event(review.episode_id, event)
    await container.event_bus.publish(event)
    updated = container.reviews.get(review_id)
    if updated is None:
        raise HTTPException(status_code=404, detail="Review not found")
    return updated
