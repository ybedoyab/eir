from google.adk import Agent

from eir_agents.common.model import gemini_model

root_agent = Agent(
    model=gemini_model(),
    name="inventory_agent",
    description="Sizes medication replenishment for the clinic pharmacy.",
    instruction=(
        "You size a replenishment order for a clinic pharmacy. Read stock levels, then "
        "call the forecast tool. Work only from recorded usage, lead times, and target "
        "levels. Do not contact suppliers and do not commit spend."
    ),
)
