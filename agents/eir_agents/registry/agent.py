from google.adk import Agent

from eir_agents.common.model import gemini_model

root_agent = Agent(
    model=gemini_model(),
    name="agent_registry",
    description="Lists registered recovery-fleet capabilities.",
    instruction=(
        "You expose the local EIR agent registry. You do not execute clinical work. "
        "Answer questions about which capabilities are available."
    ),
)
