from functools import lru_cache

from eir_shared.gemini_config import genai_client_kwargs, resolve_gemini_model
from google.adk.models import Gemini


@lru_cache(maxsize=1)
def gemini_model() -> Gemini:
    """ADK Gemini model with explicit global Vertex endpoint (no env mutation)."""
    return Gemini(
        model=resolve_gemini_model(),
        client_kwargs=genai_client_kwargs(),
    )
