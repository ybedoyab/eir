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
    episode = container.episodes.get(episode_id)
    if episode is None:
        raise HTTPException(status_code=404, detail="Recovery episode not found")

    from eir_shared.events import PatientResponded

    event = PatientResponded(
        episode_id=episode_id,
        channel="synthetic",
        payload={"message": DEMO_MALICIOUS_PROMPT},
    )
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
