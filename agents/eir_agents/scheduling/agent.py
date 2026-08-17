from google.adk import Agent

from eir_agents.common.model import gemini_model

root_agent = Agent(
    model=gemini_model(),
    name="scheduling_agent",
    description="Reads and requests appointments related to a Recovery Episode.",
    instruction=(
        "You handle appointment read and schedule capabilities. You do not contact "
        "patients directly and you do not diagnose."
    ),
)
