from google.adk import Agent

from eir_agents.common.model import gemini_model

root_agent = Agent(
    model=gemini_model(),
    name="records_agent",
    description="Reads and appends FHIR R4 resources for recovery follow-up.",
    instruction=(
        "You are the FHIR interface for EIR. Use tools to read Patient, Encounter, "
        "MedicationRequest, CarePlan, and to append follow-up Observations. "
        "Never invent real patient data. Fixtures are synthetic."
    ),
)
