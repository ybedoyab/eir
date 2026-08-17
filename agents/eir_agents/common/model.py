from eir_shared.gemini_config import resolve_gemini_model


def gemini_model() -> str:
    return resolve_gemini_model()
