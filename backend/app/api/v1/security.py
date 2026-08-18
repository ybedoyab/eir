"""Deterministic security demo scenarios for hackathon judges."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.deps import get_container
from app.integrations.enterprise.security_demo import (
    DEMO_MALICIOUS_PROMPT,
    DEMO_SAFE_PROMPT,
    screen_demo_prompt,
)
from app.services.demo_controls import (
    claim_demo_action,
    has_prompt_injection_attempt,
    require_synthetic_episode,
)

router = APIRouter()


class SecurityScreenRequest(BaseModel):
    prompt: str = Field(default=DEMO_SAFE_PROMPT)
    scenario: str = Field(default="custom")


@router.post("/screen")
def screen_prompt(body: SecurityScreenRequest) -> dict:
    container = get_container()
    result = screen_demo_prompt(container.content_guard, body.prompt)
    return {
        "scenario": body.scenario,
        "allowed": result.allowed,
        "adapter": result.adapter,
        "filter_category": result.filter_category,
        "reason": result.reason,
    }


@router.post("/demo/prompt-injection/{episode_id}")
async def demo_prompt_injection(episode_id: str) -> dict:
    """Publish a synthetic malicious patient message through the normal event bus."""
    container = get_container()
    require_synthetic_episode(container.episodes, episode_id)
    events = container.episodes.list_events(episode_id)
    if has_prompt_injection_attempt(events) or not claim_demo_action(
        episode_id, "prompt_injection"
    ):
        raise HTTPException(
            status_code=409,
            detail="Prompt-injection demo already submitted for this episode",
        )

    from eir_shared.events import PatientResponded

    event = PatientResponded(
        episode_id=episode_id,
        channel="synthetic",
        payload={"message": DEMO_MALICIOUS_PROMPT},
    )
    container.episodes.append_event(episode_id, event)
    await container.event_bus.publish(event)
    return {
        "published": event.event_type,
        "episode_id": episode_id,
        "expected": "ContentSecurityBlocked without FHIR/tool execution",
        "demo_prompt_category": "prompt_injection",
    }


@router.get("/demo/prompts")
def demo_prompts() -> dict:
    return {
        "safe": DEMO_SAFE_PROMPT,
        "malicious": DEMO_MALICIOUS_PROMPT,
    }
