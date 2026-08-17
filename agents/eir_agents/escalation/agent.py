from google.adk import Agent

from eir_agents.common.model import gemini_model

root_agent = Agent(
    model=gemini_model(),
    name="escalation_agent",
    description="Creates human-review requests for clinicians.",
    instruction=(
        "You dispatch human-review requests. You do not resolve clinical questions "
        "yourself. Include episode_id, reason, and urgency."
    ),
)
