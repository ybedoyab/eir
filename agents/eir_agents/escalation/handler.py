"""Human-review dispatch stubs."""


def request_human_review(episode_id: str, reason: str) -> dict:
    return {
        "episode_id": episode_id,
        "reason": reason,
        "status": "queued",
        "channel": "clinician_inbox",
    }
