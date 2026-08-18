"""Patient access session orchestration."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from eir_agents.access.orchestrator import AccessOrchestrator
from eir_shared.appointments import AppointmentView, SlotView
from eir_shared.capabilities import Capability

from app.domain.access.models import AccessSessionStatus, PatientAccessSession
from app.repositories.access_repository import PatientAccessSessionRepository
from app.services.appointment_service import AppointmentService


def _format_slot(slot: SlotView) -> str:
    local = slot.start.astimezone()
    return (
        f"{slot.service_name} with {slot.practitioner_name} · "
        f"{local.strftime('%a %b %d')} · {local.strftime('%I:%M %p')} · "
        f"{slot.location_name}"
    )


def _format_appointment(appt: AppointmentView) -> str:
    local = appt.start.astimezone()
    return (
        f"{appt.service_name} with {appt.practitioner_name} · "
        f"{local.strftime('%a %b %d')} · {local.strftime('%I:%M %p')} · "
        f"{appt.location_name} · {appt.status.value}"
    )


class PatientAccessService:
    def __init__(
        self,
        *,
        sessions: PatientAccessSessionRepository,
        appointments: AppointmentService,
        orchestrator: AccessOrchestrator | None = None,
    ) -> None:
        self._sessions = sessions
        self._appointments = appointments
        self._orchestrator = orchestrator or AccessOrchestrator()

    def create_session(
        self,
        *,
        patient_id: str | None,
        channel: str = "web",
    ) -> PatientAccessSession:
        session = PatientAccessSession(
            id=str(uuid4()),
            patient_id=patient_id,
            channel=channel,  # type: ignore[arg-type]
        )
        return self._sessions.save(session)

    def get_session(self, session_id: str) -> PatientAccessSession | None:
        return self._sessions.get(session_id)

    def handle_message(
        self,
        session_id: str,
        message: str,
        *,
        patient_id: str | None,
        role: str,
    ) -> dict[str, Any]:
        session = self._sessions.get(session_id)
        if session is None:
            raise ValueError("session not found")
        if (
            role == "PATIENT"
            and patient_id
            and session.patient_id
            and session.patient_id != patient_id
        ):
            raise PermissionError("session ownership mismatch")
        if patient_id and not session.patient_id:
            session.patient_id = patient_id

        plan = self._orchestrator.plan(message, session=session.model_dump(mode="json"))
        session.updated_at = datetime.now(UTC)

        if plan.requires_handoff or plan.capability == Capability.HUMAN_HANDOFF_REQUEST:
            session.handoff_required = True
            session.status = AccessSessionStatus.HANDOFF
            session.current_intent = "human_handoff"
            self._sessions.save(session)
            return {
                "reply": (
                    "I cannot safely handle that request on my own. "
                    "A clinician or staff member will review your case."
                ),
                "session": session.model_dump(mode="json"),
                "handoff_required": True,
                "capability": plan.capability,
            }

        if plan.capability == Capability.RECOVERY_ORCHESTRATE:
            session.current_intent = "recovery"
            session.status = AccessSessionStatus.COMPLETED
            self._sessions.save(session)
            return {
                "reply": (
                    "Recovery follow-up is handled in the Recovery module. "
                    "Open Recovery to start or continue your episode."
                ),
                "session": session.model_dump(mode="json"),
                "route": "/patient/recovery",
                "capability": plan.capability,
            }

        if plan.capability == Capability.APPOINTMENT_READ:
            if not patient_id:
                raise PermissionError("patient identity required")
            appointments = self._appointments.list_for_actor(
                role=role,
                patient_id=patient_id,
            )
            upcoming = [
                item
                for item in appointments
                if item.status.value not in {"cancelled", "fulfilled", "noshow"}
            ]
            if not upcoming:
                reply = "You do not have any upcoming appointments."
            else:
                lines = ["Here are your upcoming appointments:"]
                lines.extend(f"• {_format_appointment(item)}" for item in upcoming[:5])
                reply = "\n".join(lines)
            session.current_intent = "appointment.read"
            session.status = AccessSessionStatus.ACTIVE
            self._sessions.save(session)
            return {
                "reply": reply,
                "appointments": [item.model_dump(mode="json") for item in upcoming],
                "session": session.model_dump(mode="json"),
                "capability": plan.capability,
            }

        if plan.capability == Capability.APPOINTMENT_AVAILABILITY_READ:
            if not patient_id:
                raise PermissionError("patient identity required")
            params = self._orchestrator.slot_search_params(message, patient_id)
            slots = self._appointments.search_slots(params)
            session.current_intent = "book"
            if not slots:
                reply = "I could not find open slots that match. Would you like to join a waitlist?"
                session.status = AccessSessionStatus.ACTIVE
            else:
                lines = ["Here are available times:"]
                for index, slot in enumerate(slots, start=1):
                    lines.append(f"{index}. {_format_slot(slot)}")
                lines.append("Reply with the option number to continue.")
                reply = "\n".join(lines)
                session.status = AccessSessionStatus.AWAITING_SELECTION
                session.metadata["offered_slots"] = [slot.model_dump(mode="json") for slot in slots]
            self._sessions.save(session)
            return {
                "reply": reply,
                "slots": [slot.model_dump(mode="json") for slot in slots],
                "session": session.model_dump(mode="json"),
                "capability": plan.capability,
            }

        if plan.capability in {Capability.APPOINTMENT_BOOK, Capability.APPOINTMENT_RESCHEDULE}:
            return self._handle_slot_selection(session, message, patient_id, plan.capability)

        if plan.capability == Capability.APPOINTMENT_CANCEL:
            return self._handle_cancel(session, message, patient_id)

        if plan.capability == Capability.APPOINTMENT_WAITLIST:
            return self._handle_waitlist(session, patient_id)

        session.status = AccessSessionStatus.ACTIVE
        self._sessions.save(session)
        return {
            "reply": (
                "I can help with appointments, recovery follow-up, or connecting you with staff. "
                "What would you like to do?"
            ),
            "session": session.model_dump(mode="json"),
            "capability": plan.capability,
        }

    def _handle_slot_selection(
        self,
        session: PatientAccessSession,
        message: str,
        patient_id: str | None,
        capability: str,
    ) -> dict[str, Any]:
        if not patient_id:
            raise PermissionError("patient identity required")
        offered = session.metadata.get("offered_slots") or []
        selected_slot_id = session.selected_slot_id
        if not selected_slot_id:
            choice = message.strip()
            if choice.isdigit():
                index = int(choice) - 1
                if 0 <= index < len(offered):
                    selected_slot_id = str(offered[index]["id"])
                    session.selected_slot_id = selected_slot_id
            if not selected_slot_id and capability == Capability.APPOINTMENT_RESCHEDULE:
                appointment = self._find_target_appointment(patient_id, message)
                if appointment:
                    session.selected_appointment_id = appointment.id
                    params = self._orchestrator.slot_search_params(message, patient_id)
                    slots = self._appointments.search_slots(params)
                    session.metadata["offered_slots"] = [
                        slot.model_dump(mode="json") for slot in slots
                    ]
                    session.status = AccessSessionStatus.AWAITING_SELECTION
                    session.current_intent = "reschedule"
                    self._sessions.save(session)
                    if not slots:
                        return {
                            "reply": (
                                "I couldn't find alternative times. Would you like staff help?"
                            ),
                            "session": session.model_dump(mode="json"),
                            "capability": capability,
                        }
                    lines = ["I found these alternative times:"]
                    for index, slot in enumerate(slots, start=1):
                        lines.append(f"{index}. {_format_slot(slot)}")
                    lines.append("Reply with the option number to confirm the reschedule.")
                    return {
                        "reply": "\n".join(lines),
                        "slots": [slot.model_dump(mode="json") for slot in slots],
                        "session": session.model_dump(mode="json"),
                        "capability": capability,
                    }

        if not selected_slot_id:
            session.status = AccessSessionStatus.AWAITING_SELECTION
            self._sessions.save(session)
            return {
                "reply": "Please choose one of the listed options by number.",
                "session": session.model_dump(mode="json"),
                "capability": capability,
            }

        if capability == Capability.APPOINTMENT_BOOK:
            appointment = self._appointments.book(
                patient_id=patient_id,
                slot_id=selected_slot_id,
            )
            session.status = AccessSessionStatus.COMPLETED
            session.current_intent = "book"
            self._sessions.save(session)
            return {
                "reply": f"Your appointment is booked.\n{_format_appointment(appointment)}",
                "appointment": appointment.model_dump(mode="json"),
                "session": session.model_dump(mode="json"),
                "capability": capability,
            }

        appointment_id = session.selected_appointment_id or self._find_target_appointment(
            patient_id,
            message,
        ).id
        current = self._appointments.get_for_actor(
            role="PATIENT",
            actor_patient_id=patient_id,
            appointment_id=appointment_id,
        )
        updated = self._appointments.reschedule(
            appointment_id=appointment_id,
            patient_id=patient_id,
            new_slot_id=selected_slot_id,
        )
        session.status = AccessSessionStatus.COMPLETED
        session.current_intent = "reschedule"
        self._sessions.save(session)
        return {
            "reply": (
                "Your appointment has been rescheduled.\n"
                f"Previous: {_format_appointment(current)}\n"
                f"New: {_format_appointment(updated)}"
            ),
            "appointment": updated.model_dump(mode="json"),
            "session": session.model_dump(mode="json"),
            "capability": capability,
        }

    def _handle_cancel(
        self,
        session: PatientAccessSession,
        message: str,
        patient_id: str | None,
    ) -> dict[str, Any]:
        if not patient_id:
            raise PermissionError("patient identity required")
        if session.status != AccessSessionStatus.AWAITING_CONFIRMATION:
            appointment = self._find_target_appointment(patient_id, message)
            session.selected_appointment_id = appointment.id
            session.current_intent = "cancel"
            session.status = AccessSessionStatus.AWAITING_CONFIRMATION
            self._sessions.save(session)
            return {
                "reply": (
                    "Please confirm cancellation.\n"
                    f"Appointment: {_format_appointment(appointment)}\n"
                    'Reply "yes" to confirm.'
                ),
                "session": session.model_dump(mode="json"),
                "capability": Capability.APPOINTMENT_CANCEL,
            }
        appointment_id = session.selected_appointment_id
        if not appointment_id:
            raise ValueError("appointment not selected")
        cancelled = self._appointments.cancel(
            appointment_id=appointment_id,
            patient_id=patient_id,
            reason="patient requested cancellation",
            confirmed=True,
        )
        session.status = AccessSessionStatus.COMPLETED
        self._sessions.save(session)
        return {
            "reply": f"Your appointment has been cancelled.\n{_format_appointment(cancelled)}",
            "appointment": cancelled.model_dump(mode="json"),
            "session": session.model_dump(mode="json"),
            "capability": Capability.APPOINTMENT_CANCEL,
        }

    def _handle_waitlist(
        self,
        session: PatientAccessSession,
        patient_id: str | None,
    ) -> dict[str, Any]:
        if not patient_id:
            raise PermissionError("patient identity required")
        appointments = self._appointments.list_for_actor(role="PATIENT", patient_id=patient_id)
        upcoming = [
            item
            for item in appointments
            if item.status.value not in {"cancelled", "fulfilled", "noshow"}
        ]
        if not upcoming:
            return {
                "reply": "You need an upcoming appointment before joining a waitlist.",
                "session": session.model_dump(mode="json"),
                "capability": Capability.APPOINTMENT_WAITLIST,
            }
        target = upcoming[0]
        request = self._appointments.waitlist(
            patient_id=patient_id,
            appointment_id=target.id,
        )
        session.current_intent = "waitlist"
        session.status = AccessSessionStatus.COMPLETED
        self._sessions.save(session)
        return {
            "reply": (
                f"You are on the waitlist for an earlier {target.specialty} slot. "
                "We will notify you in the portal if something opens."
            ),
            "waitlist": request.model_dump(mode="json"),
            "session": session.model_dump(mode="json"),
            "capability": Capability.APPOINTMENT_WAITLIST,
        }

    def _find_target_appointment(self, patient_id: str, message: str) -> AppointmentView:
        appointments = self._appointments.list_for_actor(role="PATIENT", patient_id=patient_id)
        upcoming = [
            item
            for item in appointments
            if item.status.value not in {"cancelled", "fulfilled", "noshow"}
        ]
        if not upcoming:
            raise ValueError("no upcoming appointments")
        lowered = message.lower()
        for item in upcoming:
            if item.specialty.lower() in lowered:
                return item
            if "thursday" in lowered and item.start.weekday() == 3:
                return item
            if "tomorrow" in lowered:
                tomorrow = datetime.now(UTC).date() + timedelta(days=1)
                if item.start.date() == tomorrow:
                    return item
        return upcoming[0]
