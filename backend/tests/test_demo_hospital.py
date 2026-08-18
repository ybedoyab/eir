from app.demo_ops import DEMO_EPISODES, DEMO_REVIEWS, DEMO_WAITLIST
from app.seed_fhir import _ordered_resources
from eir_shared.demo_hospital import (
    LOCATIONS,
    PATIENTS,
    PRACTITIONERS,
    SERVICES,
    build_appointments,
    build_slots,
    validate_hospital,
)


def test_hospital_catalog_relationships() -> None:
    slots = build_slots()
    appointments = build_appointments(slots)
    errors = validate_hospital(slots, appointments)
    assert errors == []
    assert len(PATIENTS) >= 10
    assert len(SERVICES) >= 5
    assert len(PRACTITIONERS) >= 6
    assert len(LOCATIONS) >= 3
    assert len(slots) >= 30
    assert len(appointments) >= 15
    assert any(item["id"] == "appt-alex-cardio-2026-08-27" for item in appointments)
    assert any(item["id"] == "appt-jordan-primary-2026-08-21" for item in appointments)


def test_demo_operations_counts() -> None:
    assert len(DEMO_EPISODES) >= 3
    assert len([item for item in DEMO_REVIEWS if item["status"].value == "pending"]) >= 2
    assert len(DEMO_WAITLIST) >= 1
    assert {item["patient_id"] for item in DEMO_EPISODES} <= {item["id"] for item in PATIENTS}


def test_fhir_seed_orders_services_before_roles() -> None:
    ordered = _ordered_resources(
        [
            {"resourceType": "PractitionerRole", "id": "role-amir-rahman"},
            {"resourceType": "HealthcareService", "id": "service-neurology"},
        ]
    )
    types = [item["resourceType"] for item in ordered]
    assert types.index("HealthcareService") < types.index("PractitionerRole")
