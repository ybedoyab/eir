"""Deterministic hackathon demo bootstrap — synthetic data only."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from eir_shared.events import PatientResponded
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.deps import get_container
from app.integrations.enterprise.security_demo import DEMO_MALICIOUS_PROMPT
from app.services.demo_controls import (
    CONCERNING_MESSAGE,
    claim_demo_action,
    has_concerning_signal,
    has_recovery_checkin,
    mock_checkin_payload,
    require_demo_sku,
    require_synthetic_episode,
)
from app.services.follow_up_scheduler import FollowUpScheduler
from app.services.medications import medications_for_patient
from app.services.recovery_service import RecoveryService
from app.services.stock_monitor import StockMonitor

router = APIRouter()

DEMO_PATIENT_ID = "patient-synthetic-001"
DEMO_CONCERNING_MESSAGE = CONCERNING_MESSAGE


class DemoBootstrapRequest(BaseModel):
    patient_id: str = Field(default=DEMO_PATIENT_ID)
    fast_forward: bool = False


def _scheduler() -> FollowUpScheduler:
    container = get_container()
    return FollowUpScheduler(
        container.episodes,
        idempotency=container.scheduler_idempotency,
    )


@router.post("/bootstrap")
async def bootstrap_demo(body: DemoBootstrapRequest) -> dict:
    """Create a fresh synthetic recovery episode for the hackathon story."""
    container = get_container()
    patient = container.patients.get(body.patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    due_at = datetime.now(UTC) + timedelta(days=7)
    service = RecoveryService(container.episodes)
    episode, started = service.create_episode(
        patient_id=body.patient_id,
        next_follow_up_at=due_at,
        assigned_agents=["outreach", "risk"],
    )
    scheduler = _scheduler()
    scheduler.ensure_schedule(episode)
    await container.event_bus.publish(started)
    follow_up = None
    if body.fast_forward:
        follow_up = scheduler.advance_episode(episode.id)
        if follow_up is not None:
            await container.event_bus.publish(follow_up)
    episode = container.episodes.get(episode.id) or episode
    medications = medications_for_patient(
        container.fhir.get_medications(episode.patient_id),
        container.supply.list_items(),
    )
    return {
        "episode_id": episode.id,
        "patient_id": episode.patient_id,
        "patient_name": patient.name,
        "status": episode.status.value,
        "risk_level": episode.risk_level.value,
        "next_follow_up_at": episode.next_follow_up_at,
        "fast_forwarded": follow_up is not None,
        "monitoring": True,
        "medications": [item.model_dump(mode="json") for item in medications],
        "story": [
            "Consultation finished → RecoveryEpisodeStarted",
            "Next autonomous follow-up scheduled",
            "POST /api/v1/demo/advance-follow-up/{episode_id} uses FollowUpScheduler",
            "FollowUpDue published through EventBus → worker outreach_agent",
            "Voximplant PSTN + Gemini Live, or in-page WebRTC check-in → PatientResponded",
            "risk_agent evaluates structured recovery check-in",
            f"POST /api/v1/security/demo/prompt-injection/{episode.id}",
            f"POST /api/v1/demo/concerning-signal/{episode.id} (backup if PSTN unavailable)",
            f"POST /api/v1/demo/mock-checkin/{episode.id} (typed answers if the call ends early)",
        ],
        "malicious_prompt": DEMO_MALICIOUS_PROMPT,
    }


@router.post("/advance-follow-up/{episode_id}")
async def advance_follow_up(episode_id: str) -> dict:
    """Demo time acceleration: make the follow-up due via FollowUpScheduler.

    Production uses Cloud Scheduler to call the same claim path. This endpoint
    never invokes outreach_agent and never bypasses EventBus/worker logic.
    """
    container = get_container()
    require_synthetic_episode(container.episodes, episode_id)
    events = container.episodes.list_events(episode_id)
    already_due = any(event.event_type == "FollowUpDue" for event in events)
    if already_due or not claim_demo_action(episode_id, "advance"):
        return {
            "advanced": False,
            "episode_id": episode_id,
            "event": None,
            "reason": "follow-up already claimed or episode is not schedulable",
        }
    event = _scheduler().advance_episode(episode_id)
    if event is None:
        return {
            "advanced": False,
            "episode_id": episode_id,
            "event": None,
            "reason": "follow-up already claimed or episode is not schedulable",
        }
    await container.event_bus.publish(event)
    return {
        "advanced": True,
        "episode_id": episode_id,
        "event": event.event_type,
    }


@router.post("/concerning-signal/{episode_id}")
async def concerning_signal(episode_id: str) -> dict:
    """Publish a synthetic high-pain patient response through the real event bus."""
    container = get_container()
    require_synthetic_episode(container.episodes, episode_id)
    events = container.episodes.list_events(episode_id)
    if has_concerning_signal(events) or not claim_demo_action(episode_id, "concerning"):
        raise HTTPException(
            status_code=409,
            detail="Concerning signal already submitted for this demo episode",
        )
    event = PatientResponded(
        episode_id=episode_id,
        channel="synthetic",
        payload={
            "message": DEMO_CONCERNING_MESSAGE,
            "pain_score": 8,
            "reported_issue": True,
        },
    )
    container.episodes.append_event(episode_id, event)
    await container.event_bus.publish(event)
    return {
        "published": event.event_type,
        "episode_id": episode_id,
        "expected": "risk_agent escalates; clinician review may open",
        "signal": {"pain_score": 8, "reported_issue": "swelling"},
        "backup": True,
    }


class MockMedication(BaseModel):
    sku: str = ""
    taken: bool = True


class MockCheckinRequest(BaseModel):
    """Typed stand-in for the answers a patient would speak on the call."""

    pain_score: int | None = 8
    reported_issue: bool = True
    issue_summary: str = "swelling near the incision"
    symptoms_worsening: bool = False
    medication_adherence: str = "unknown"
    patient_requests_clinician: bool = False
    medications: list[MockMedication] = Field(default_factory=list)


@router.post("/mock-checkin/{episode_id}")
async def mock_checkin(episode_id: str, body: MockCheckinRequest) -> dict:
    """Publish a typed recovery check-in when the live call did not produce one.

    A demo call that is hung up early leaves the episode with no structured
    answers and nothing for the risk agent to assess. This puts the same event
    on the same bus -- flagged synthetic, never dressed up as a spoken reply.
    """
    container = get_container()
    require_synthetic_episode(container.episodes, episode_id)
    events = container.episodes.list_events(episode_id)
    if has_recovery_checkin(events):
        raise HTTPException(
            status_code=409,
            detail="This episode already has a recovery check-in",
        )
    if not claim_demo_action(episode_id, "mock-checkin"):
        raise HTTPException(
            status_code=409,
            detail="Mock check-in already submitted for this demo episode",
        )
    payload = mock_checkin_payload(
        pain_score=body.pain_score,
        reported_issue=body.reported_issue,
        issue_summary=body.issue_summary,
        symptoms_worsening=body.symptoms_worsening,
        medication_adherence=body.medication_adherence,
        medications=[item.model_dump() for item in body.medications],
        patient_requests_clinician=body.patient_requests_clinician,
    )
    event = PatientResponded(
        episode_id=episode_id,
        channel="voice",
        payload=payload,
    )
    container.episodes.append_event(episode_id, event)
    await container.event_bus.publish(event)
    return {
        "published": event.event_type,
        "episode_id": episode_id,
        "simulated": True,
        "signal": {
            "pain_score": payload["pain_score"],
            "reported_issue": payload["reported_issue"],
            "medication_adherence": payload["medication_adherence"],
        },
        "expected": "risk_agent assesses the structured check-in",
    }


@router.post("/retry-voice/{episode_id}")
async def retry_voice(episode_id: str) -> dict:
    """One manual PSTN retry after a failed/unanswered call. Never loops automatically."""
    container = get_container()
    require_synthetic_episode(container.episodes, episode_id)
    events = container.episodes.list_events(episode_id)
    failed = any(event.event_type == "VoiceCallFailed" for event in events)
    completed = any(event.event_type == "VoiceCallCompleted" for event in events)
    if not failed or completed:
        raise HTTPException(
            status_code=409,
            detail="Voice retry is only available after a failed or unanswered call",
        )
    if not claim_demo_action(episode_id, "voice-retry"):
        raise HTTPException(
            status_code=409,
            detail="Voice retry already used for this demo episode",
        )
    service = RecoveryService(container.episodes)
    event = service.trigger_follow_up(episode_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Recovery episode not found")
    await container.event_bus.publish(event)
    return {
        "retried": True,
        "episode_id": episode_id,
        "event": event.event_type,
    }


@router.get("/context/{episode_id}")
def demo_context(episode_id: str) -> dict:
    """Medications and voice hints for the guided demo. Synthetic episodes only."""
    container = get_container()
    require_synthetic_episode(container.episodes, episode_id)
    episode = container.episodes.get(episode_id)
    if episode is None:
        raise HTTPException(status_code=404, detail="Recovery episode not found")
    medications = medications_for_patient(
        container.fhir.get_medications(episode.patient_id),
        container.supply.list_items(),
    )
    return {
        "episode_id": episode.id,
        "patient_id": episode.patient_id,
        "medications": [item.model_dump(mode="json") for item in medications],
    }


DEMO_SKU = "MED-ENOX-40"


class SupplyDemoRequest(BaseModel):
    sku: str = Field(default=DEMO_SKU)


def _stock_monitor() -> StockMonitor:
    container = get_container()
    return StockMonitor(container.supply, idempotency=container.scheduler_idempotency)


@router.post("/supply/bootstrap")
async def bootstrap_supply_demo(body: SupplyDemoRequest) -> dict:
    """Dispense a synthetic medication down to a stock-out and let the fleet react.

    Consumes stock through the same rule production uses instead of writing a
    low number directly, so the InventoryLevelLow event is genuinely earned.
    """
    container = get_container()
    require_demo_sku(body.sku)
    item = container.supply.get_item(body.sku)
    if item is None:
        raise HTTPException(status_code=404, detail="Inventory item not found")

    existing = container.supply.open_case_for_sku(body.sku)
    if existing is not None:
        return {
            "opened": False,
            "case_id": existing.id,
            "sku": existing.sku,
            "status": existing.status.value,
            "reason": "a replenishment case is already open for this SKU",
            "hint": f"POST /api/v1/supply/cases/{existing.id}/cancel to reset the demo",
        }

    event = _stock_monitor().drain_stock(body.sku)
    if event is None:
        raise HTTPException(status_code=409, detail="Could not open a replenishment case")
    await container.event_bus.publish(event)

    case = container.supply.get_case(event.episode_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Replenishment case not found")
    updated = container.supply.get_item(body.sku)
    return {
        "opened": True,
        "case_id": case.id,
        "sku": case.sku,
        "item_name": case.item_name,
        "status": case.status.value,
        "urgency": case.urgency.value,
        "on_hand": updated.on_hand if updated else None,
        "reorder_point": updated.reorder_point if updated else None,
        "requested_quantity": case.requested_quantity,
        "quotes": len(case.quotes),
        "purchase_order": case.purchase_order.model_dump(mode="json")
        if case.purchase_order
        else None,
        "assigned_agents": case.assigned_agents,
        "story": [
            "Stock dispensed below the reorder point → InventoryLevelLow",
            "inventory_agent sized the order against usage and supplier lead time",
            "procurement_agent called every supplier that carries the SKU",
            "Quotes recorded from the calls; availability beats price",
            "Purchase order drafted and parked at the safety gate",
            f"POST /api/v1/supply/cases/{case.id}/approve places the order",
        ],
    }
