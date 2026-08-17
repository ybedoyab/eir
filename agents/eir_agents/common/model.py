import os


def gemini_model() -> str:
    return os.getenv("GEMINI_MODEL") or "gemini-flash-latest"
