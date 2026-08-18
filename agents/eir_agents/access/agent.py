from google.adk import Agent

from eir_agents.common.model import gemini_model

root_agent = Agent(
    model=gemini_model(),
    name="patient_access_agent",
    description="Administrative patient intent coordinator for hospital access.",
    instruction=(
        "You are EIR's patient access coordinator. Help with appointments, reminders, "
        "and routing to recovery or staff. Never diagnose, prescribe, or invent clinical urgency."
    ),
)
