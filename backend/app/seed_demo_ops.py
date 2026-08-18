"""Idempotent operational demo seed for Firestore. Synthetic IDs only.

Intended for a runtime with Firestore access (Cloud Run startup or an
operator identity). The GitHub deploy SA seeds FHIR only.
"""

from __future__ import annotations

from eir_shared.env import load_root_env

from app.core.deps import get_container
from app.demo_ops import apply_demo_operations


def main() -> int:
    load_root_env()
    get_container.cache_clear()
    container = get_container()
    container.seed()
    counts = apply_demo_operations(
        episodes=container.episodes,
        reviews=container.reviews,
        operational=getattr(container, "operational", None),
    )
    print(
        "seeded demo operations "
        f"episodes={counts['episodes']} reviews={counts['reviews']} "
        f"waitlist={counts['waitlist']} reminders={counts['reminders']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
