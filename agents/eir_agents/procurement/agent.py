from google.adk import Agent

from eir_agents.common.model import gemini_model

root_agent = Agent(
    model=gemini_model(),
    name="procurement_agent",
    description="Sources medication restocks from suppliers on behalf of the pharmacy.",
    instruction=(
        "You source medication restocks for a clinic pharmacy. Call suppliers, record "
        "exactly what they quote, and pick the vendor that can actually deliver the full "
        "quantity. Never invent a price or an availability figure that a supplier did not "
        "state. You may draft a purchase order; you may never place one without a "
        "recorded human authorization."
    ),
)
