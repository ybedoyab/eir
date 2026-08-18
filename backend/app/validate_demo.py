"""Validate synthetic hospital catalog relationships."""

from __future__ import annotations

from eir_shared.demo_hospital import build_appointments, build_slots, validate_hospital
from eir_shared.env import load_root_env

from app.demo_ops import DEMO_EPISODES, DEMO_REVIEWS, DEMO_WAITLIST


def main() -> int:
    load_root_env()
    slots = build_slots()
    appointments = build_appointments(slots)
    errors = validate_hospital(slots, appointments)
    active = [
        item for item in DEMO_EPISODES if item["status"].value not in {"COMPLETED", "CANCELLED"}
    ]
    pending = [item for item in DEMO_REVIEWS if item["status"].value == "pending"]
    if len(active) < 3:
        errors.append("need at least 3 active recoveries")
    if len(pending) < 2:
        errors.append("need at least 2 pending human reviews")
    if len(DEMO_WAITLIST) < 1:
        errors.append("need at least 1 waitlist request")
    if errors:
        for item in errors:
            print(f"FAIL {item}")
        return 1
    print(
        "demo catalog ok "
        f"slots={len(slots)} appointments={len(appointments)} "
        f"recoveries={len(DEMO_EPISODES)} reviews={len(DEMO_REVIEWS)} "
        f"waitlist={len(DEMO_WAITLIST)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
