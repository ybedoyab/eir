from google.adk import Agent

from eir_agents.common.model import gemini_model

root_agent = Agent(
    model=gemini_model(),
    name="recovery_orchestrator",
    description="Coordinates Recovery Episode workflows by capability.",
    instruction=(
        "You coordinate longitudinal recovery. Inspect episode state, choose the next "
        "capability, and delegate. Do not implement outreach, diagnosis, FHIR, or "
        "scheduling yourself. Never autonomously diagnose a patient."
    ),
)
