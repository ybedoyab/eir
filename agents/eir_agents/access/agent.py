from google.adk import Agent
from google.adk.tools.preload_memory_tool import PreloadMemoryTool

from eir_agents.access.constants import SYNTHETIC_USER_ID
from eir_agents.access.runtime_tools import (
    cancel_appointment,
    get_upcoming_appointments,
    reschedule_appointment,
    search_appointment_availability,
)
from eir_agents.common.model import gemini_model

PATIENT_ACCESS_INSTRUCTION = (
    "You are EIR's patient access coordinator for synthetic demo patients only. "
    "Help with appointments, reminders, and routing to recovery or staff. "
    "Never diagnose, prescribe, or invent clinical urgency. "
    "Never invent appointments or slots. Always call tools for live data. "
    f"The bound user is {SYNTHETIC_USER_ID}. Tools cannot query other patients. "
    "If memory contains preferred_clinic or preferred_time_of_day, use those values "
    "when ranking or explaining available slots. "
    "Only remember those two preference keys. Never store symptoms, medications, "
    "phone numbers, transcripts, or FHIR bodies."
)


def build_patient_access_agent() -> Agent:
    return Agent(
        model=gemini_model(),
        name="patient_access_agent",
        description="Administrative patient intent coordinator for hospital access.",
        instruction=PATIENT_ACCESS_INSTRUCTION,
        tools=[
            get_upcoming_appointments,
            search_appointment_availability,
            reschedule_appointment,
            cancel_appointment,
            PreloadMemoryTool(),
        ],
    )


root_agent = build_patient_access_agent()
patient_access_agent = root_agent
