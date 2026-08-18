"""Routes patient-access intents to capabilities without touching recovery episodes."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from eir_shared.appointments import SlotSearchParams
from eir_shared.capabilities import Capability


@dataclass
class AccessPlan:
    capability: str
    reason: str
    requires_handoff: bool = False
    metadata: dict[str, Any] | None = None


_CLINICAL_PATTERNS = (
    re.compile(r"\bchest pain\b", re.I),
    re.compile(r"\bshort(ness)? of breath\b", re.I),
    re.compile(r"\bcan'?t breathe\b", re.I),
    re.compile(r"\bsevere\b.*\bpain\b", re.I),
)

_INJECTION_PATTERNS = (
    re.compile(r"ignore (all )?(previous )?instructions", re.I),
    re.compile(r"cancel all appointments", re.I),
    re.compile(r"bypass authorization", re.I),
)


def _mentions_specialty(text: str) -> str:
    lowered = text.lower()
    if "cardio" in lowered:
        return "Cardiology"
    if "ortho" in lowered:
        return "Orthopedics"
    if "primary" in lowered:
        return "Primary Care"
    return ""


def _time_of_day(text: str) -> str:
    lowered = text.lower()
    if "afternoon" in lowered:
        return "afternoon"
    if "morning" in lowered:
        return "morning"
    return "any"


class AccessOrchestrator:
    def plan(self, message: str, *, session: dict[str, Any] | None = None) -> AccessPlan:
        session = session or {}
        text = message.strip()
        lowered = text.lower()

        for pattern in _INJECTION_PATTERNS:
            if pattern.search(text):
                return AccessPlan(
                    capability=Capability.HUMAN_HANDOFF_REQUEST,
                    reason="blocked unauthorized administrative request",
                    requires_handoff=True,
                )

        for pattern in _CLINICAL_PATTERNS:
            if pattern.search(text):
                return AccessPlan(
                    capability=Capability.HUMAN_HANDOFF_REQUEST,
                    reason="clinical symptoms require governed handoff",
                    requires_handoff=True,
                )

        if any(token in lowered for token in ("recover", "recovery", "after surgery", "follow-up")):
            return AccessPlan(
                capability=Capability.RECOVERY_ORCHESTRATE,
                reason="route to recovery module",
            )

        if "human" in lowered or "staff" in lowered or "representative" in lowered:
            return AccessPlan(
                capability=Capability.HUMAN_HANDOFF_REQUEST,
                reason="patient requested staff assistance",
                requires_handoff=True,
            )

        if session.get("status") == "awaiting_confirmation" and any(
            token in lowered for token in ("yes", "confirm", "please do", "go ahead")
        ):
            pending = str(session.get("current_intent", ""))
            if pending == "cancel":
                return AccessPlan(
                    capability=Capability.APPOINTMENT_CANCEL,
                    reason="confirmed cancellation",
                )
            if pending == "reschedule":
                return AccessPlan(
                    capability=Capability.APPOINTMENT_RESCHEDULE,
                    reason="confirmed reschedule",
                )
            if pending == "book":
                return AccessPlan(
                    capability=Capability.APPOINTMENT_BOOK,
                    reason="confirmed booking",
                )

        if session.get("status") == "awaiting_selection" and session.get("selected_slot_id"):
            pending = str(session.get("current_intent", ""))
            if pending in {"book", "reschedule"}:
                capability = (
                    Capability.APPOINTMENT_BOOK
                    if pending == "book"
                    else Capability.APPOINTMENT_RESCHEDULE
                )
                return AccessPlan(capability=capability, reason="slot selected")

        if any(token in lowered for token in ("what appointments", "my appointments", "upcoming")):
            return AccessPlan(
                capability=Capability.APPOINTMENT_READ,
                reason="list patient appointments",
            )

        if "cancel" in lowered and "appointment" in lowered:
            return AccessPlan(
                capability=Capability.APPOINTMENT_CANCEL,
                reason="cancel appointment",
            )

        reschedule_tokens = ("move", "reschedule", "change")
        if any(token in lowered for token in reschedule_tokens) and "appointment" in lowered:
            return AccessPlan(
                capability=Capability.APPOINTMENT_RESCHEDULE,
                reason="reschedule appointment",
            )

        if any(token in lowered for token in ("earlier", "sooner", "waitlist")):
            return AccessPlan(
                capability=Capability.APPOINTMENT_WAITLIST,
                reason="earlier slot or waitlist",
            )

        book_tokens = ("book", "schedule", "need an appointment", "make an appointment", "need a")
        if any(token in lowered for token in book_tokens) and "appointment" in lowered:
            return AccessPlan(
                capability=Capability.APPOINTMENT_AVAILABILITY_READ,
                reason="search availability before booking",
            )

        if session.get("current_intent"):
            return AccessPlan(
                capability=Capability.PATIENT_ACCESS_ORCHESTRATE,
                reason="continue active access session",
            )

        return AccessPlan(
            capability=Capability.PATIENT_ACCESS_ORCHESTRATE,
            reason="clarify patient request",
        )

    def slot_search_params(self, message: str, patient_id: str) -> SlotSearchParams:
        specialty = _mentions_specialty(message)
        now = datetime.now(UTC)
        return SlotSearchParams(
            patient_id=patient_id,
            specialty=specialty,
            start_date=now,
            end_date=now + timedelta(days=14),
            time_of_day=_time_of_day(message),
            limit=6,
        )
