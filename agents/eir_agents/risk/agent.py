from google.adk import Agent

from eir_agents.common.model import gemini_model

root_agent = Agent(
    model=gemini_model(),
    name="risk_agent",
    description="Surfaces structured recovery risk signals and requests human review.",
    instruction=(
        "You detect missing information and uncertainty. You do not diagnose. "
        "Inspect structured observations or care plan data with read-only tools when useful, "
        "then call the risk assessment tool. When unsure or when risk may be HIGH or CRITICAL, "
        "request human review."
    ),
)
