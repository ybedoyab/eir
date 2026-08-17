"""Risk stubs. Does not autonomously diagnose."""


def flag_for_human_review(reason: str) -> dict:
    return {"action": "human_review", "reason": reason, "autonomous_diagnosis": False}
