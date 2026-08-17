"""Scheduling stubs."""


def request_appointment(episode_id: str, reason: str) -> dict:
    return {"episode_id": episode_id, "reason": reason, "status": "requested"}
