"""Deterministic synthetic operational demo state. Prefix demo- / synthetic- only."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from eir_shared.appointments import AppointmentReminder, WaitlistRequest
from eir_shared.demo_hospital import PATIENTS, demo_now
from eir_shared.events import (
    ClinicianResolved,
    DomainEvent,
    HumanReviewRequested,
    PatientResponded,
    RecoveryEpisodeCompleted,
    RecoveryEpisodeStarted,
    RiskEscalated,
)

from app.domain.recovery.models import EpisodeStatus, RecoveryEpisode, RiskLevel
from app.repositories.review_repository import HumanReview, ReviewStatus

DEMO_EPISODES = (
    {
        "id": "demo-recovery-alex",
        "patient_id": "patient-synthetic-001",
        "status": EpisodeStatus.WAITING_FOR_NEXT_FOLLOWUP,
        "risk_level": RiskLevel.MEDIUM,
        "offset_days": 1,
        "started_offset_days": -12,
        "agents": ["recovery", "adherence"],
        "context": "Post-procedure cardiology follow-up",
        "tasks": ["Walk daily as tolerated", "Take prescribed medication", "Report new symptoms"],
    },
    {
        "id": "demo-recovery-sofia",
        "patient_id": "patient-synthetic-003",
        "status": EpisodeStatus.ACTIVE,
        "risk_level": RiskLevel.LOW,
        "offset_days": 1,
        "started_offset_days": -6,
        "agents": ["recovery"],
        "context": "Orthopedics recovery check-in",
        "tasks": ["Complete home exercises", "Ice after activity", "Keep the follow-up visit"],
    },
    {
        "id": "demo-recovery-elena",
        "patient_id": "patient-synthetic-006",
        "status": EpisodeStatus.ESCALATED,
        "risk_level": RiskLevel.HIGH,
        "offset_days": 0,
        "started_offset_days": -4,
        "agents": ["recovery", "risk", "escalation"],
        "context": "Escalated orthopedic recovery",
        "tasks": [
            "Rest the affected joint",
            "Take prescribed medication",
            "Await clinician review",
        ],
    },
    {
        "id": "demo-recovery-marcus",
        "patient_id": "patient-synthetic-004",
        "status": EpisodeStatus.ACTIVE,
        "risk_level": RiskLevel.MEDIUM,
        "offset_days": 2,
        "started_offset_days": -3,
        "agents": ["recovery"],
        "context": "Cardiology follow-up recovery",
    },
    {
        "id": "demo-recovery-daniel-complete",
        "patient_id": "patient-synthetic-010",
        "status": EpisodeStatus.COMPLETED,
        "risk_level": RiskLevel.LOW,
        "offset_days": None,
        "started_offset_days": -40,
        "agents": ["recovery"],
        "context": "Completed primary-care recovery",
    },
)

DEMO_REVIEWS = (
    {
        "id": "demo-review-elena-01",
        "episode_id": "demo-recovery-elena",
        "reason": "Escalated recovery needs clinician review",
        "capability": "escalation.human_review",
        "agent_name": "escalation",
        "status": ReviewStatus.PENDING,
        "created_offset_hours": -18,
    },
    {
        "id": "demo-review-marcus-01",
        "episode_id": "demo-recovery-marcus",
        "reason": "Concerning follow-up signal awaiting review",
        "capability": "risk.review",
        "agent_name": "risk",
        "status": ReviewStatus.PENDING,
        "created_offset_hours": -6,
    },
    {
        "id": "demo-review-daniel-resolved",
        "episode_id": "demo-recovery-daniel-complete",
        "reason": "Recovery completed after clinician confirmation",
        "capability": "escalation.human_review",
        "agent_name": "escalation",
        "status": ReviewStatus.RESOLVED,
        "created_offset_hours": -36,
        "note": "Reviewed and closed in the synthetic demo.",
    },
)

DEMO_WAITLIST = (
    {
        "id": "demo-waitlist-priya",
        "patient_id": "patient-synthetic-005",
        "appointment_id": "appt-demo-priya-primary-next",
        "specialty": "Primary Care",
    },
    {
        "id": "demo-waitlist-leah",
        "patient_id": "patient-synthetic-011",
        "appointment_id": "appt-demo-leah-derm-next",
        "specialty": "Dermatology",
    },
)

DEMO_REMINDERS = (
    {
        "id": "demo-reminder-alex",
        "appointment_id": "appt-alex-cardio-2026-08-27",
        "patient_id": "patient-synthetic-001",
        "offset_hours": 24,
    },
    {
        "id": "demo-reminder-jordan",
        "appointment_id": "appt-jordan-primary-2026-08-21",
        "patient_id": "patient-synthetic-002",
        "offset_hours": 12,
    },
    {
        "id": "demo-reminder-sofia",
        "appointment_id": "appt-demo-sofia-ortho-next",
        "patient_id": "patient-synthetic-003",
        "offset_hours": 36,
    },
)

PATIENT_NAME = {item["id"]: item["name"] for item in PATIENTS}


def build_demo_episodes(now: datetime | None = None) -> list[RecoveryEpisode]:
    now = now or demo_now().astimezone(UTC)
    episodes: list[RecoveryEpisode] = []
    for item in DEMO_EPISODES:
        follow_up = None
        if item["offset_days"] is not None:
            follow_up = now + timedelta(days=int(item["offset_days"]))
        episodes.append(
            RecoveryEpisode(
                id=str(item["id"]),
                patient_id=str(item["patient_id"]),
                status=item["status"],
                started_at=now + timedelta(days=int(item["started_offset_days"])),
                next_follow_up_at=follow_up,
                risk_level=item["risk_level"],
                assigned_agents=list(item["agents"]),
            )
        )
    return episodes


def build_demo_reviews(now: datetime | None = None) -> list[HumanReview]:
    now = now or demo_now().astimezone(UTC)
    reviews: list[HumanReview] = []
    for item in DEMO_REVIEWS:
        created = now + timedelta(hours=int(item["created_offset_hours"]))
        resolved = created + timedelta(hours=2) if item["status"] == ReviewStatus.RESOLVED else None
        reviews.append(
            HumanReview(
                id=str(item["id"]),
                episode_id=str(item["episode_id"]),
                reason=str(item["reason"]),
                capability=str(item["capability"]),
                agent_name=str(item["agent_name"]),
                status=item["status"],
                created_at=created,
                resolved_at=resolved,
                note=str(item.get("note", "")),
            )
        )
    return reviews


def build_demo_waitlist() -> list[WaitlistRequest]:
    return [WaitlistRequest.model_validate(item) for item in DEMO_WAITLIST]


def build_demo_reminders(now: datetime | None = None) -> list[AppointmentReminder]:
    now = now or demo_now().astimezone(UTC)
    return [
        AppointmentReminder(
            id=str(item["id"]),
            appointment_id=str(item["appointment_id"]),
            patient_id=str(item["patient_id"]),
            scheduled_for=now + timedelta(hours=int(item["offset_hours"])),
        )
        for item in DEMO_REMINDERS
    ]


def build_demo_events(now: datetime | None = None) -> list[DomainEvent]:
    now = now or demo_now().astimezone(UTC)
    events: list[DomainEvent] = []
    for item in DEMO_EPISODES:
        events.append(
            RecoveryEpisodeStarted(
                event_id=f"demo-event-{item['id']}-started",
                episode_id=str(item["id"]),
                patient_id=str(item["patient_id"]),
                occurred_at=now + timedelta(days=int(item["started_offset_days"])),
                payload={
                    "synthetic": True,
                    "context": item.get("context"),
                    "tasks": item.get("tasks", []),
                },
            )
        )
    events.extend(
        [
            PatientResponded(
                event_id="demo-event-alex-checkin",
                episode_id="demo-recovery-alex",
                channel="sms",
                occurred_at=now - timedelta(days=1),
                payload={
                    "pain_score": 2,
                    "issue_summary": "Feeling better",
                    "medication_adherence": "yes",
                    "channel": "sms",
                },
            ),
            PatientResponded(
                event_id="demo-event-sofia-checkin",
                episode_id="demo-recovery-sofia",
                channel="app",
                occurred_at=now - timedelta(hours=8),
                payload={
                    "pain_score": 1,
                    "issue_summary": "Walking more each day",
                    "medication_adherence": "yes",
                    "channel": "app",
                },
            ),
            PatientResponded(
                event_id="demo-event-elena-checkin",
                episode_id="demo-recovery-elena",
                channel="voice",
                occurred_at=now - timedelta(hours=18),
                payload={
                    "pain_score": 7,
                    "issue_summary": "Increased pain after activity",
                    "medication_adherence": "no",
                    "channel": "voice",
                },
            ),
            RiskEscalated(
                event_id="demo-event-elena-risk",
                episode_id="demo-recovery-elena",
                risk_level="HIGH",
                occurred_at=now - timedelta(hours=18),
                payload={"risk_level": "HIGH"},
            ),
            HumanReviewRequested(
                event_id="demo-event-elena-review",
                episode_id="demo-recovery-elena",
                reason="Escalated recovery needs clinician review",
                occurred_at=now - timedelta(hours=18),
                payload={"reason": "Escalated recovery needs clinician review"},
            ),
            RecoveryEpisodeCompleted(
                event_id="demo-event-daniel-complete",
                episode_id="demo-recovery-daniel-complete",
                occurred_at=now - timedelta(days=20),
            ),
            ClinicianResolved(
                event_id="demo-event-daniel-resolved",
                episode_id="demo-recovery-daniel-complete",
                review_id="demo-review-daniel-resolved",
                note="Reviewed and closed in the synthetic demo.",
                occurred_at=now - timedelta(days=20),
            ),
        ]
    )
    return events


def apply_demo_operations(
    *,
    episodes: Any,
    reviews: Any,
    operational: Any | None = None,
) -> dict[str, int]:
    episode_items = build_demo_episodes()
    review_items = build_demo_reviews()
    for episode in episode_items:
        episodes.save(episode)
    for event in build_demo_events():
        existing = episodes.list_events(event.episode_id)
        ids = {item.event_id for item in existing}
        types = {item.event_type for item in existing}
        if event.event_id in ids:
            continue
        if event.event_type == "RecoveryEpisodeStarted" and "RecoveryEpisodeStarted" in types:
            continue
        episodes.append_event(event.episode_id, event)
    for review in review_items:
        existing = reviews.get(review.id)
        if existing is not None and existing.status == ReviewStatus.RESOLVED:
            continue
        reviews.save(review)
    if operational is not None:
        for request in build_demo_waitlist():
            operational.upsert_waitlist(request)
        for reminder in build_demo_reminders():
            operational.upsert_reminder(reminder)
    return {
        "episodes": len(episode_items),
        "reviews": len(review_items),
        "waitlist": len(DEMO_WAITLIST),
        "reminders": len(DEMO_REMINDERS),
    }
