from google.adk import Agent

from eir_agents.common.model import gemini_model

root_agent = Agent(
    model=gemini_model(),
    name="recovery_video_agent",
    description="Generates a personalized recovery-instruction video from approved care tasks.",
    instruction=(
        "You generate a short patient recovery video from already-approved care instructions. "
        "Never invent new instructions or clinical advice; only visualize what was given."
    ),
)
