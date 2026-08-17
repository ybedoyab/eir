"""Thin ADK Agent factory. Prompts stay out of API routes."""

from google.adk import Agent

from eir_agents.common.model import gemini_model


def build_agent(
    *,
    name: str,
    description: str,
    instruction: str,
    tools: list | None = None,
):
    return Agent(
        model=gemini_model(),
        name=name,
        description=description,
        instruction=instruction,
        tools=tools or [],
    )
