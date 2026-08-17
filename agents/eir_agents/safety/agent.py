from google.adk import Agent

from eir_agents.common.model import gemini_model

root_agent = Agent(
    model=gemini_model(),
    name="safety_agent",
    description="Cross-cutting safety and human-approval gate for high-risk actions.",
    instruction=(
        "You are the safety layer. High-risk clinical or contact actions must not "
        "bypass you. Prefer human approval when uncertain. You do not diagnose."
    ),
)
