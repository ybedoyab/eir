from google.adk import Agent

from eir_agents.common.model import gemini_model

root_agent = Agent(
    model=gemini_model(),
    name="outreach_agent",
    description="Contacts patients by voice or messaging for recovery follow-up.",
    instruction=(
        "You own outbound patient contact for a Recovery Episode. You do not diagnose. "
        "Collect structured follow-up answers and return them as data. High-risk "
        "contact actions must go through the safety gate."
    ),
)
