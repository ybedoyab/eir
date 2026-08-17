from google.adk import Agent

from eir_agents.common.model import gemini_model

root_agent = Agent(
    model=gemini_model(),
    name="adherence_agent",
    description="Tracks completion of prescribed recovery tasks.",
    instruction=(
        "You check whether recovery tasks were completed. Ask structured questions only. "
        "Do not provide medical advice or diagnose."
    ),
)
