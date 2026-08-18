"""Canonical capability strings.

Agents request capabilities rather than assuming unrestricted access.
These names map to Agent Identity + Agent Gateway policies.
"""

from enum import StrEnum


class Capability(StrEnum):
    PATIENT_READ = "patient.read"
    PATIENT_CONTACT = "patient.contact"
    ENCOUNTER_READ = "encounter.read"
    MEDICATION_READ = "medication.read"
    CARE_PLAN_READ = "care_plan.read"
    OBSERVATION_WRITE = "observation.write"
    APPOINTMENT_READ = "appointment.read"
    APPOINTMENT_AVAILABILITY_READ = "appointment.availability.read"
    APPOINTMENT_BOOK = "appointment.book"
    APPOINTMENT_RESCHEDULE = "appointment.reschedule"
    APPOINTMENT_CANCEL = "appointment.cancel"
    APPOINTMENT_WAITLIST = "appointment.waitlist"
    APPOINTMENT_SCHEDULE = "appointment.schedule"
    ADHERENCE_CHECK = "adherence.check"
    RISK_ASSESS = "risk.assess"
    ESCALATION_REQUEST = "escalation.request"
    RECOVERY_ORCHESTRATE = "recovery.orchestrate"
    PATIENT_ACCESS_ORCHESTRATE = "patient_access.orchestrate"
    CARE_NAVIGATION_READ = "care_navigation.read"
    HUMAN_HANDOFF_REQUEST = "human_handoff.request"


PRE_APPROVAL_CAPABILITIES: frozenset[str] = frozenset(
    {
        Capability.OBSERVATION_WRITE,
    }
)

HIGH_RISK_CAPABILITIES = PRE_APPROVAL_CAPABILITIES

BLOCKING_CAPABILITIES: frozenset[str] = frozenset(
    {
        Capability.ESCALATION_REQUEST,
        Capability.OBSERVATION_WRITE,
        Capability.HUMAN_HANDOFF_REQUEST,
    }
)

ROUTINE_APPOINTMENT_CAPABILITIES: frozenset[str] = frozenset(
    {
        Capability.APPOINTMENT_READ,
        Capability.APPOINTMENT_AVAILABILITY_READ,
        Capability.APPOINTMENT_BOOK,
        Capability.APPOINTMENT_RESCHEDULE,
        Capability.APPOINTMENT_CANCEL,
        Capability.APPOINTMENT_WAITLIST,
    }
)
