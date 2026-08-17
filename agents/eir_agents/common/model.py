import os

from eir_shared.env import load_root_env


def gemini_model() -> str:
    load_root_env()
    return os.getenv("GEMINI_MODEL") or "gemini-2.5-flash"
