from google.adk import Agent

from eir_agents.common.model import gemini_model

root_agent = Agent(
    model=gemini_model(),
    name="adherence_agent",
    description="Checks whether prescribed medications were taken.",
    instruction=(
        "You check whether the patient has been taking prescribed medications. "
        "Escalate only when a critical medication was skipped. "
        "Do not provide medical advice or diagnose."
    ),
)
