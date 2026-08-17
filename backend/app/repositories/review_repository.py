"""Human-review queue.

TODO: persist in Firestore / Cloud SQL.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field


class ReviewStatus(StrEnum):
    PENDING = "pending"
    RESOLVED = "resolved"


class HumanReview(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    episode_id: str
    reason: str
    capability: str
    agent_name: str
    status: ReviewStatus = ReviewStatus.PENDING
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    resolved_at: datetime | None = None
    note: str = ""
    pending_event_type: str = ""
    pending_event_payload: dict = Field(default_factory=dict)
    pending_capability: str = ""


class InMemoryReviewRepository:
    def __init__(self) -> None:
        self._items: dict[str, HumanReview] = {}

    def save(self, review: HumanReview) -> HumanReview:
        self._items[review.id] = review
        return review

    def get(self, review_id: str) -> HumanReview | None:
        return self._items.get(review_id)

    def list(self, *, pending_only: bool = False) -> list[HumanReview]:
        items = list(self._items.values())
        if pending_only:
            return [item for item in items if item.status == ReviewStatus.PENDING]
        return items

    def for_episode(self, episode_id: str) -> list[HumanReview]:
        return [item for item in self._items.values() if item.episode_id == episode_id]
