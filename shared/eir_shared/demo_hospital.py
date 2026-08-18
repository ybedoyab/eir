"""Synthetic hospital catalog with relative demo dates. Never real PHI."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

DEMO_TZ = ZoneInfo("America/Chicago")

PATIENTS: list[dict[str, str]] = [
    {
        "id": "patient-synthetic-001",
        "name": "Alex Rivera",
        "date_of_birth": "1988-04-12",
        "preferred_language": "en",
        "preferred_contact_channel": "voice",
    },
    {
        "id": "patient-synthetic-002",
        "name": "Jordan Lee",
        "date_of_birth": "1975-11-03",
        "preferred_language": "en",
        "preferred_contact_channel": "sms",
    },
    {
        "id": "patient-synthetic-003",
        "name": "Sofia Martinez",
        "date_of_birth": "1991-06-18",
        "preferred_language": "en",
        "preferred_contact_channel": "email",
    },
    {
        "id": "patient-synthetic-004",
        "name": "Marcus Thompson",
        "date_of_birth": "1968-02-09",
        "preferred_language": "en",
        "preferred_contact_channel": "voice",
    },
    {
        "id": "patient-synthetic-005",
        "name": "Priya Shah",
        "date_of_birth": "1984-09-27",
        "preferred_language": "en",
        "preferred_contact_channel": "sms",
    },
    {
        "id": "patient-synthetic-006",
        "name": "Elena Garcia",
        "date_of_birth": "1959-12-01",
        "preferred_language": "en",
        "preferred_contact_channel": "voice",
    },
    {
        "id": "patient-synthetic-007",
        "name": "Noah Williams",
        "date_of_birth": "1996-03-22",
        "preferred_language": "en",
        "preferred_contact_channel": "email",
    },
    {
        "id": "patient-synthetic-008",
        "name": "Mei Chen",
        "date_of_birth": "1980-07-14",
        "preferred_language": "en",
        "preferred_contact_channel": "sms",
    },
    {
        "id": "patient-synthetic-009",
        "name": "Amina Hassan",
        "date_of_birth": "1972-01-30",
        "preferred_language": "en",
        "preferred_contact_channel": "email",
    },
    {
        "id": "patient-synthetic-010",
        "name": "Daniel Brooks",
        "date_of_birth": "1964-05-08",
        "preferred_language": "en",
        "preferred_contact_channel": "voice",
    },
    {
        "id": "patient-synthetic-011",
        "name": "Leah Okonkwo",
        "date_of_birth": "1993-10-05",
        "preferred_language": "en",
        "preferred_contact_channel": "sms",
    },
    {
        "id": "patient-synthetic-012",
        "name": "Henrik Larsen",
        "date_of_birth": "1986-08-19",
        "preferred_language": "en",
        "preferred_contact_channel": "email",
    },
]

PRACTITIONERS: list[dict[str, Any]] = [
    {
        "id": "practitioner-maya-chen",
        "name": "Dr. Maya Chen",
        "specialty": "Cardiology",
        "location_id": "location-main-clinic",
    },
    {
        "id": "practitioner-sam-ortiz",
        "name": "Dr. Sam Ortiz",
        "specialty": "Primary Care",
        "location_id": "location-main-clinic",
    },
    {
        "id": "practitioner-lee-park",
        "name": "Dr. Lee Park",
        "specialty": "Orthopedics",
        "location_id": "location-north-clinic",
    },
    {
        "id": "practitioner-olivia-bennett",
        "name": "Dr. Olivia Bennett",
        "specialty": "Primary Care",
        "location_id": "location-main-clinic",
    },
    {
        "id": "practitioner-rachel-kim",
        "name": "Dr. Rachel Kim",
        "specialty": "Dermatology",
        "location_id": "location-specialty-center",
    },
    {
        "id": "practitioner-amir-rahman",
        "name": "Dr. Amir Rahman",
        "specialty": "Neurology",
        "location_id": "location-specialty-center",
    },
]

LOCATIONS: list[dict[str, str]] = [
    {
        "id": "location-main-clinic",
        "name": "Main Clinic",
        "address": "100 Harbor Way",
    },
    {
        "id": "location-north-clinic",
        "name": "North Clinic",
        "address": "480 North Ridge Ave",
    },
    {
        "id": "location-specialty-center",
        "name": "Specialty Center",
        "address": "22 Medical Plaza",
    },
]

SERVICES: list[dict[str, str]] = [
    {
        "id": "service-primary-care",
        "name": "Primary Care",
        "location_id": "location-main-clinic",
    },
    {
        "id": "service-cardiology",
        "name": "Cardiology",
        "location_id": "location-main-clinic",
    },
    {
        "id": "service-orthopedics",
        "name": "Orthopedics",
        "location_id": "location-north-clinic",
    },
    {
        "id": "service-dermatology",
        "name": "Dermatology",
        "location_id": "location-specialty-center",
    },
    {
        "id": "service-neurology",
        "name": "Neurology",
        "location_id": "location-specialty-center",
    },
]

SCHEDULES: list[dict[str, str]] = [
    {
        "id": "schedule-cardiology-main",
        "specialty": "Cardiology",
        "practitioner_id": "practitioner-maya-chen",
        "location_id": "location-main-clinic",
    },
    {
        "id": "schedule-primary-main",
        "specialty": "Primary Care",
        "practitioner_id": "practitioner-sam-ortiz",
        "location_id": "location-main-clinic",
    },
    {
        "id": "schedule-primary-bennett",
        "specialty": "Primary Care",
        "practitioner_id": "practitioner-olivia-bennett",
        "location_id": "location-main-clinic",
    },
    {
        "id": "schedule-ortho-north",
        "specialty": "Orthopedics",
        "practitioner_id": "practitioner-lee-park",
        "location_id": "location-north-clinic",
    },
    {
        "id": "schedule-derm-specialty",
        "specialty": "Dermatology",
        "practitioner_id": "practitioner-rachel-kim",
        "location_id": "location-specialty-center",
    },
    {
        "id": "schedule-neuro-specialty",
        "specialty": "Neurology",
        "practitioner_id": "practitioner-amir-rahman",
        "location_id": "location-specialty-center",
    },
]


def demo_now() -> datetime:
    return datetime.now(DEMO_TZ)


def demo_today() -> datetime:
    now = demo_now()
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _at(
    offset_days: int, hour: int, minute: int, duration_minutes: int = 30
) -> tuple[datetime, datetime]:
    start = demo_today() + timedelta(days=offset_days, hours=hour, minutes=minute)
    return start, start + timedelta(minutes=duration_minutes)


def _lookup(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(item["id"]): item for item in rows}


def _slot_row(
    *,
    slot_id: str,
    schedule_id: str,
    offset_days: int,
    hour: int,
    minute: int,
    status: str,
) -> dict[str, Any]:
    schedule = _lookup(SCHEDULES)[schedule_id]
    practitioner = _lookup(PRACTITIONERS)[str(schedule["practitioner_id"])]
    location = _lookup(LOCATIONS)[str(schedule["location_id"])]
    start, end = _at(offset_days, hour, minute)
    return {
        "id": slot_id,
        "schedule_id": schedule_id,
        "status": status,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "specialty": schedule["specialty"],
        "service_name": schedule["specialty"],
        "practitioner_id": practitioner["id"],
        "practitioner_name": practitioner["name"],
        "location_id": location["id"],
        "location_name": location["name"],
        "appointment_type": "routine",
    }


def _appointment_row(
    *,
    appointment_id: str,
    patient_id: str,
    slot: dict[str, Any],
    status: str,
    cancellation_reason: str = "",
) -> dict[str, Any]:
    row = {
        "id": appointment_id,
        "patient_id": patient_id,
        "status": status,
        "specialty": slot["specialty"],
        "service_name": slot["service_name"],
        "practitioner_id": slot["practitioner_id"],
        "practitioner_name": slot["practitioner_name"],
        "location_id": slot["location_id"],
        "location_name": slot["location_name"],
        "start": slot["start"],
        "end": slot["end"],
        "slot_id": slot["id"],
        "appointment_type": "routine",
    }
    if cancellation_reason:
        row["cancellation_reason"] = cancellation_reason
    return row


def build_slots() -> list[dict[str, Any]]:
    specs: list[tuple[str, str, int, int, int, str]] = [
        ("slot-cardio-2026-08-27-1000", "schedule-cardiology-main", 9, 15, 0, "busy"),
        ("slot-primary-2026-08-21-1100", "schedule-primary-main", 3, 11, 0, "busy"),
        ("slot-demo-cardio-today-0900", "schedule-cardiology-main", 0, 9, 0, "busy"),
        ("slot-demo-ortho-today-1330", "schedule-ortho-north", 0, 13, 30, "busy"),
        ("slot-demo-primary-today-1015", "schedule-primary-bennett", 0, 10, 15, "busy"),
        ("slot-demo-sofia-ortho-p02", "schedule-ortho-north", 2, 11, 0, "busy"),
        ("slot-demo-marcus-cardio-p05", "schedule-cardiology-main", 5, 14, 30, "busy"),
        ("slot-demo-priya-primary-p12", "schedule-primary-main", 12, 9, 30, "busy"),
        ("slot-demo-elena-ortho-p04", "schedule-ortho-north", 4, 15, 0, "busy"),
        ("slot-demo-noah-cardio-past", "schedule-cardiology-main", -18, 10, 0, "busy"),
        ("slot-demo-noah-cardio-p07", "schedule-cardiology-main", 7, 16, 0, "busy"),
        ("slot-demo-mei-derm-p06", "schedule-derm-specialty", 6, 10, 30, "busy"),
        ("slot-demo-amina-neuro-p11", "schedule-neuro-specialty", 11, 13, 0, "busy"),
        ("slot-demo-daniel-primary-past", "schedule-primary-bennett", -21, 9, 0, "busy"),
        ("slot-demo-leah-derm-p08", "schedule-derm-specialty", 8, 14, 0, "busy"),
        ("slot-demo-henrik-neuro-p01", "schedule-neuro-specialty", 1, 9, 30, "busy"),
        ("slot-demo-jordan-primary-past", "schedule-primary-main", -14, 10, 0, "busy"),
        ("slot-demo-alex-cardio-past", "schedule-cardiology-main", -30, 14, 30, "busy"),
        ("slot-demo-sofia-ortho-cancelled", "schedule-ortho-north", -4, 11, 0, "busy"),
        ("slot-demo-marcus-cardio-cancelled", "schedule-cardiology-main", -7, 15, 30, "busy"),
        ("slot-demo-qa-primary-p20", "schedule-primary-bennett", 20, 11, 30, "busy"),
    ]
    free_days = (1, 2, 3, 6, 8, 10, 14, 16, 21, 28)
    free_times = ((9, 0), (11, 30), (14, 30), (16, 0))
    schedules = [
        "schedule-cardiology-main",
        "schedule-primary-main",
        "schedule-primary-bennett",
        "schedule-ortho-north",
        "schedule-derm-specialty",
        "schedule-neuro-specialty",
    ]
    for schedule_id in schedules:
        short = schedule_id.replace("schedule-", "")
        for day in free_days:
            hour, minute = free_times[day % len(free_times)]
            if hour >= 13 and "cardiology" in schedule_id:
                hour, minute = 14, 30
            specs.append(
                (
                    f"slot-demo-{short}-p{day:02d}-{hour:02d}{minute:02d}",
                    schedule_id,
                    day,
                    hour,
                    minute,
                    "free",
                )
            )
    seen: set[str] = set()
    slots: list[dict[str, Any]] = []
    for slot_id, schedule_id, offset, hour, minute, status in specs:
        if slot_id in seen:
            continue
        seen.add(slot_id)
        slots.append(
            _slot_row(
                slot_id=slot_id,
                schedule_id=schedule_id,
                offset_days=offset,
                hour=hour,
                minute=minute,
                status=status,
            )
        )
    return slots


def build_appointments(slots: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    by_id = {item["id"]: item for item in (slots or build_slots())}
    booked: list[tuple[str, str, str, str, str]] = [
        (
            "appt-alex-cardio-2026-08-27",
            "patient-synthetic-001",
            "slot-cardio-2026-08-27-1000",
            "booked",
            "",
        ),
        (
            "appt-jordan-primary-2026-08-21",
            "patient-synthetic-002",
            "slot-primary-2026-08-21-1100",
            "booked",
            "",
        ),
        (
            "appt-demo-marcus-today-cardio",
            "patient-synthetic-004",
            "slot-demo-cardio-today-0900",
            "booked",
            "",
        ),
        (
            "appt-demo-sofia-today-ortho",
            "patient-synthetic-003",
            "slot-demo-ortho-today-1330",
            "booked",
            "",
        ),
        (
            "appt-demo-priya-today-primary",
            "patient-synthetic-005",
            "slot-demo-primary-today-1015",
            "booked",
            "",
        ),
        (
            "appt-demo-sofia-ortho-next",
            "patient-synthetic-003",
            "slot-demo-sofia-ortho-p02",
            "booked",
            "",
        ),
        (
            "appt-demo-marcus-cardio-next",
            "patient-synthetic-004",
            "slot-demo-marcus-cardio-p05",
            "booked",
            "",
        ),
        (
            "appt-demo-priya-primary-next",
            "patient-synthetic-005",
            "slot-demo-priya-primary-p12",
            "booked",
            "",
        ),
        (
            "appt-demo-elena-ortho-next",
            "patient-synthetic-006",
            "slot-demo-elena-ortho-p04",
            "booked",
            "",
        ),
        (
            "appt-demo-noah-cardio-past",
            "patient-synthetic-007",
            "slot-demo-noah-cardio-past",
            "fulfilled",
            "",
        ),
        (
            "appt-demo-noah-cardio-next",
            "patient-synthetic-007",
            "slot-demo-noah-cardio-p07",
            "booked",
            "",
        ),
        (
            "appt-demo-mei-derm-next",
            "patient-synthetic-008",
            "slot-demo-mei-derm-p06",
            "booked",
            "",
        ),
        (
            "appt-demo-amina-neuro-next",
            "patient-synthetic-009",
            "slot-demo-amina-neuro-p11",
            "booked",
            "",
        ),
        (
            "appt-demo-daniel-primary-past",
            "patient-synthetic-010",
            "slot-demo-daniel-primary-past",
            "fulfilled",
            "",
        ),
        (
            "appt-demo-leah-derm-next",
            "patient-synthetic-011",
            "slot-demo-leah-derm-p08",
            "booked",
            "",
        ),
        (
            "appt-demo-henrik-neuro-next",
            "patient-synthetic-012",
            "slot-demo-henrik-neuro-p01",
            "booked",
            "",
        ),
        (
            "appt-demo-jordan-primary-past",
            "patient-synthetic-002",
            "slot-demo-jordan-primary-past",
            "fulfilled",
            "",
        ),
        (
            "appt-demo-alex-cardio-past",
            "patient-synthetic-001",
            "slot-demo-alex-cardio-past",
            "fulfilled",
            "",
        ),
        (
            "appt-demo-sofia-ortho-cancelled",
            "patient-synthetic-003",
            "slot-demo-sofia-ortho-cancelled",
            "cancelled",
            "patient requested a later date",
        ),
        (
            "appt-demo-marcus-cardio-cancelled",
            "patient-synthetic-004",
            "slot-demo-marcus-cardio-cancelled",
            "cancelled",
            "schedule conflict",
        ),
        (
            "appt-demo-qa-disposable",
            "patient-synthetic-012",
            "slot-demo-qa-primary-p20",
            "booked",
            "",
        ),
    ]
    return [
        _appointment_row(
            appointment_id=appointment_id,
            patient_id=patient_id,
            slot=by_id[slot_id],
            status=status,
            cancellation_reason=reason,
        )
        for appointment_id, patient_id, slot_id, status, reason in booked
    ]


def practitioner_fhir() -> list[dict[str, Any]]:
    return [
        {
            "id": item["id"],
            "resourceType": "Practitioner",
            "name": [{"text": item["name"]}],
            "qualification": [{"code": {"text": item["specialty"]}}],
        }
        for item in PRACTITIONERS
    ]


def location_fhir() -> list[dict[str, Any]]:
    return [
        {
            "id": item["id"],
            "resourceType": "Location",
            "name": item["name"],
            "address": {"text": item["address"]},
        }
        for item in LOCATIONS
    ]


def service_fhir() -> list[dict[str, Any]]:
    return [
        {
            "id": item["id"],
            "resourceType": "HealthcareService",
            "name": item["name"],
            "specialty": [{"text": item["name"]}],
            "location": [{"reference": f"Location/{item['location_id']}"}],
        }
        for item in SERVICES
    ]


def schedule_fhir() -> list[dict[str, Any]]:
    return [
        {
            "id": item["id"],
            "resourceType": "Schedule",
            "serviceCategory": [{"text": item["specialty"]}],
            "actor": [
                {"reference": f"Practitioner/{item['practitioner_id']}"},
                {"reference": f"Location/{item['location_id']}"},
            ],
        }
        for item in SCHEDULES
    ]


def practitioner_role_fhir() -> list[dict[str, Any]]:
    service_by_specialty = {item["name"]: item["id"] for item in SERVICES}
    return [
        {
            "id": f"role-{item['id'].removeprefix('practitioner-')}",
            "resourceType": "PractitionerRole",
            "practitioner": {"reference": f"Practitioner/{item['id']}"},
            "location": [{"reference": f"Location/{item['location_id']}"}],
            "healthcareService": [
                {"reference": f"HealthcareService/{service_by_specialty[item['specialty']]}"}
            ],
            "specialty": [{"text": item["specialty"]}],
        }
        for item in PRACTITIONERS
    ]


def patient_fhir(patient: dict[str, str]) -> dict[str, Any]:
    parts = patient["name"].split(" ", 1)
    given = parts[0]
    family = parts[1] if len(parts) > 1 else parts[0]
    return {
        "resourceType": "Patient",
        "id": patient["id"],
        "meta": {
            "tag": [
                {
                    "system": "https://eir.local/tags",
                    "code": "synthetic",
                    "display": "SYNTHETIC — not real patient data",
                }
            ]
        },
        "text": {
            "status": "generated",
            "div": (
                '<div xmlns="http://www.w3.org/1999/xhtml">'
                f"SYNTHETIC — not real patient data. {patient['name']}, "
                f"born {patient['date_of_birth']}.</div>"
            ),
        },
        "identifier": [
            {
                "system": "https://eir.local/synthetic-patients",
                "value": patient["id"],
            }
        ],
        "active": True,
        "name": [{"use": "official", "family": family, "given": [given]}],
        "gender": "unknown",
        "birthDate": patient["date_of_birth"],
        "communication": [
            {
                "language": {
                    "coding": [
                        {
                            "system": "urn:ietf:bcp:47",
                            "code": patient["preferred_language"],
                            "display": "English",
                        }
                    ],
                    "text": "English",
                },
                "preferred": True,
            }
        ],
    }


def validate_hospital(
    slots: list[dict[str, Any]] | None = None,
    appointments: list[dict[str, Any]] | None = None,
) -> list[str]:
    slots = slots or build_slots()
    appointments = appointments or build_appointments(slots)
    errors: list[str] = []
    patient_ids = {item["id"] for item in PATIENTS}
    slot_ids = {item["id"] for item in slots}
    schedule_ids = {item["id"] for item in SCHEDULES}
    practitioner_ids = {item["id"] for item in PRACTITIONERS}
    if len(PATIENTS) < 10:
        errors.append("need at least 10 patients")
    if len(SERVICES) < 5:
        errors.append("need at least 5 services")
    if len(PRACTITIONERS) < 6:
        errors.append("need at least 6 practitioners")
    if len(LOCATIONS) < 3:
        errors.append("need at least 3 locations")
    if len(slots) < 30:
        errors.append("need at least 30 slots")
    if len(appointments) < 15:
        errors.append("need at least 15 appointments")
    for slot in slots:
        if slot["schedule_id"] not in schedule_ids:
            errors.append(f"slot {slot['id']} missing schedule")
        if slot["practitioner_id"] not in practitioner_ids:
            errors.append(f"slot {slot['id']} missing practitioner")
    for appointment in appointments:
        if appointment["patient_id"] not in patient_ids:
            errors.append(f"appointment {appointment['id']} missing patient")
        if appointment["slot_id"] not in slot_ids:
            errors.append(f"appointment {appointment['id']} missing slot")
        slot = next(item for item in slots if item["id"] == appointment["slot_id"])
        if appointment["status"] != "cancelled" and slot["status"] != "busy":
            errors.append(f"booked appointment {appointment['id']} slot is not busy")
    return errors
