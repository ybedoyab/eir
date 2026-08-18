"""Demo identity roles for synthetic hospital access."""

from enum import StrEnum


class DemoRole(StrEnum):
    PATIENT = "PATIENT"
    CLINICIAN = "CLINICIAN"
    OPERATIONS_ADMIN = "OPERATIONS_ADMIN"


ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    DemoRole.PATIENT: frozenset(
        {
            "patient.self.read",
            "appointment.own.read",
            "appointment.own.write",
            "recovery.own.read",
            "access.assistant",
        }
    ),
    DemoRole.CLINICIAN: frozenset(
        {
            "patient.assigned.read",
            "appointment.clinical.read",
            "recovery.clinical.read",
            "review.read",
            "review.resolve",
        }
    ),
    DemoRole.OPERATIONS_ADMIN: frozenset(
        {
            "patient.directory.read",
            "appointment.operations.read",
            "appointment.operations.write",
            "fleet.read",
            "observability.read",
            "demo.tools",
        }
    ),
}
