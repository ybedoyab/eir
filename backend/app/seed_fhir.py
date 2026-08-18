"""Upload synthetic FHIR fixtures into Healthcare API. Never use real PHI."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import httpx
from eir_shared.demo_hospital import (
    PATIENTS,
    build_appointments,
    build_slots,
    location_fhir,
    patient_fhir,
    practitioner_fhir,
    practitioner_role_fhir,
    schedule_fhir,
    service_fhir,
)
from eir_shared.env import load_root_env, repo_root

from app.core.config import settings
from app.integrations.fhir.client import GoogleHealthcareFhirClient

_SEED_ORDER = (
    "patient.json",
    "encounter.json",
    "medication-request.json",
    "observation.json",
    "care-plan.json",
)


def _load_patient_resources(mocks: Path) -> list[dict[str, Any]]:
    resources: list[dict[str, Any]] = []
    for patient_dir in sorted(mocks.iterdir()):
        if not patient_dir.is_dir():
            continue
        for name in _SEED_ORDER:
            path = patient_dir / name
            if not path.is_file():
                continue
            resource = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(resource, dict) and resource.get("resourceType"):
                resources.append(resource)
    return resources


def _load_json_list(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, list) else []


def _hospital_resources(_hospital_dir: Path) -> list[dict[str, Any]]:
    from app.integrations.fhir.gcp_scheduling import _with_extensions

    resources: list[dict[str, Any]] = []
    resources.extend(patient_fhir(item) for item in PATIENTS)
    resources.extend(practitioner_fhir())
    resources.extend(location_fhir())
    resources.extend(service_fhir())
    resources.extend(practitioner_role_fhir())
    resources.extend(schedule_fhir())
    slots = build_slots()
    appointments = build_appointments(slots)
    for raw in slots:
        slot = {
            "resourceType": "Slot",
            "id": raw["id"],
            "status": raw["status"],
            "schedule": {"reference": f"Schedule/{raw['schedule_id']}"},
            "start": raw["start"],
            "end": raw["end"],
        }
        _with_extensions(
            slot,
            specialty=str(raw["specialty"]),
            service_name=str(raw["service_name"]),
            practitioner_name=str(raw["practitioner_name"]),
            practitioner_id=str(raw["practitioner_id"]),
            location_name=str(raw["location_name"]),
            location_id=str(raw["location_id"]),
            appointment_type=str(raw.get("appointment_type", "routine")),
        )
        resources.append(slot)
    for raw in appointments:
        patient_ref = f"Patient/{raw['patient_id']}"
        appointment = {
            "resourceType": "Appointment",
            "id": raw["id"],
            "status": raw["status"],
            "start": raw["start"],
            "end": raw["end"],
            "slot": [{"reference": f"Slot/{raw['slot_id']}"}],
            "participant": [
                {"actor": {"reference": patient_ref}, "status": "accepted"},
                {
                    "actor": {"reference": f"Practitioner/{raw['practitioner_id']}"},
                    "status": "accepted",
                },
            ],
        }
        if raw.get("cancellation_reason"):
            appointment["cancelationReason"] = {"text": raw["cancellation_reason"]}
        _with_extensions(
            appointment,
            synthetic_patient_id=str(raw["patient_id"]),
            specialty=str(raw["specialty"]),
            service_name=str(raw["service_name"]),
            practitioner_name=str(raw["practitioner_name"]),
            practitioner_id=str(raw["practitioner_id"]),
            location_name=str(raw["location_name"]),
            location_id=str(raw["location_id"]),
            appointment_type=str(raw.get("appointment_type", "routine")),
        )
        resources.append(appointment)
    return resources


def _ordered_resources(resources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    priority = {
        "Patient": 0,
        "Practitioner": 1,
        "Location": 1,
        "HealthcareService": 2,
        "PractitionerRole": 3,
        "Schedule": 4,
        "Slot": 5,
        "Appointment": 6,
        "Encounter": 7,
        "MedicationRequest": 8,
        "Observation": 9,
        "CarePlan": 10,
    }
    return sorted(
        resources,
        key=lambda item: (priority.get(str(item.get("resourceType")), 99), str(item.get("id", ""))),
    )


def _upsert_resource(
    client: GoogleHealthcareFhirClient,
    resource: dict[str, Any],
) -> httpx.Response:
    """Upsert via PUT; GCP Healthcare ignores client ids on POST."""
    resource_type = str(resource["resourceType"])
    resource_id = str(resource["id"])
    headers = client._headers()
    return httpx.put(
        f"{client._base}/{resource_type}/{resource_id}",
        headers=headers,
        json=resource,
        timeout=60,
    )


def main() -> int:
    load_root_env()
    patient_mocks = repo_root() / "mocks" / "fhir"
    hospital_mocks = repo_root() / "mocks" / "hospital"
    resources = _load_patient_resources(patient_mocks)
    resources.extend(_hospital_resources(hospital_mocks))
    if not resources:
        print("no FHIR fixtures found", file=sys.stderr)
        return 1

    client = GoogleHealthcareFhirClient(
        project=settings.fhir_project,
        location=settings.fhir_location,
        dataset=settings.fhir_dataset,
        store=settings.fhir_store,
        fallback_on_miss=False,
    )
    ordered = _ordered_resources(resources)
    for resource in ordered:
        resource_type = str(resource["resourceType"])
        resource_id = str(resource["id"])
        response = _upsert_resource(client, resource)
        if response.status_code >= 400:
            print(
                f"upsert {resource_type}/{resource_id} failed ({response.status_code}): "
                f"{response.text[:800]}",
                file=sys.stderr,
            )
            return 1

    client.reachable = True
    print(f"uploaded {len(ordered)} synthetic resources via idempotent upsert")
    for resource in ordered:
        print(f"  {resource['resourceType']}/{resource['id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
