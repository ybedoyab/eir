"""Canonical capability strings.

Agents request capabilities rather than assuming unrestricted access.
These names will later map to Agent Identity + Agent Gateway policies.
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
    APPOINTMENT_SCHEDULE = "appointment.schedule"
    ADHERENCE_CHECK = "adherence.check"
    RISK_ASSESS = "risk.assess"
    ESCALATION_REQUEST = "escalation.request"
    RECOVERY_ORCHESTRATE = "recovery.orchestrate"


# Capabilities that require clinician PRE-approval before domain tools run.
PRE_APPROVAL_CAPABILITIES: frozenset[str] = frozenset(
    {
        Capability.OBSERVATION_WRITE,
    }
)

# Backward-compatible alias for docs and policy references.
HIGH_RISK_CAPABILITIES = PRE_APPROVAL_CAPABILITIES

# These pause the episode until a clinician resolves a review.
BLOCKING_CAPABILITIES: frozenset[str] = frozenset(
    {
        Capability.ESCALATION_REQUEST,
        Capability.APPOINTMENT_SCHEDULE,
        Capability.OBSERVATION_WRITE,
    }
)
