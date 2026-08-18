from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from app.core.config import Settings
from app.core.deps import Container, _build_fhir_client, get_container
from app.integrations.fhir.client import GoogleHealthcareFhirClient
from app.integrations.fhir.gcp_scheduling import GcpSchedulingClient
from app.repositories.firestore_access_repository import FirestorePatientAccessSessionRepository
from app.repositories.operational_store import InMemoryOperationalSchedulingStore
from eir_agents.records.fhir_client import LocalFhirClient
from eir_shared.appointments import SlotSearchParams, SlotStatus
from pydantic import ValidationError


class _FakeResponse:
    def __init__(self, status_code: int = 200, payload: dict | None = None, text: str = "") -> None:
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.text = text or str(self._payload)

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"http {self.status_code}")

    def json(self) -> dict:
        return self._payload


def setup_function() -> None:
    get_container.cache_clear()


def test_build_fhir_client_uses_gcp_in_production_mode() -> None:
    operational = InMemoryOperationalSchedulingStore()
    client = _build_fhir_client(testing=False, operational_store=operational)
    assert isinstance(client, GoogleHealthcareFhirClient)
    assert isinstance(client._fallback, LocalFhirClient)


def test_appointment_service_receives_gcp_adapter_when_fhir_mode_gcp(monkeypatch) -> None:
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "")
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    from app.core import deps

    monkeypatch.setattr(deps, "_in_pytest", lambda: False)
    monkeypatch.setattr(deps.settings, "fhir_mode", "gcp")
    monkeypatch.setattr(deps.settings, "episode_store", "memory")
    monkeypatch.setattr(deps.settings, "event_bus", "memory")
    monkeypatch.setattr(deps.settings, "environment", "development")
    get_container.cache_clear()
    container = Container()
    assert isinstance(container.appointments._fhir, GoogleHealthcareFhirClient)
    assert container.appointments._fhir is container.fhir
    get_container.cache_clear()


def test_production_session_secret_fail_closed() -> None:
    with pytest.raises(ValidationError):
        Settings(environment="production", session_secret="local-dev-session-secret")
    with pytest.raises(ValidationError):
        Settings(environment="production", session_secret="short")


def test_gcp_scheduling_list_appointments(monkeypatch) -> None:
    client = GcpSchedulingClient(
        base_url="https://example/fhir",
        headers=lambda: {"Authorization": "Bearer test"},
        patient_ref=lambda patient_id: f"Patient/{patient_id}",
    )

    def fake_get(url: str, **kwargs):
        if url.endswith("/Appointment"):
            return _FakeResponse(
                200,
                {
                    "entry": [
                        {
                            "resource": {
                                "resourceType": "Appointment",
                                "id": "appt-1",
                                "status": "booked",
                                "start": "2026-08-27T15:00:00+00:00",
                                "end": "2026-08-27T15:30:00+00:00",
                                "participant": [
                                    {
                                        "actor": {"reference": "Patient/patient-synthetic-001"},
                                        "status": "accepted",
                                    }
                                ],
                                "extension": [
                                    {
                                        "url": "https://eir.local/scheduling/synthetic-patient-id",
                                        "valueString": "patient-synthetic-001",
                                    },
                                    {
                                        "url": "https://eir.local/scheduling/specialty",
                                        "valueString": "Cardiology",
                                    },
                                    {
                                        "url": "https://eir.local/scheduling/service-name",
                                        "valueString": "Cardiology",
                                    },
                                    {
                                        "url": "https://eir.local/scheduling/practitioner-name",
                                        "valueString": "Dr. Maya Chen",
                                    },
                                    {
                                        "url": "https://eir.local/scheduling/location-name",
                                        "valueString": "Main Clinic",
                                    },
                                ],
                            }
                        }
                    ]
                },
            )
        raise AssertionError(url)

    monkeypatch.setattr("httpx.get", fake_get)
    items = client.list_appointments("patient-synthetic-001")
    assert len(items) == 1
    assert items[0].specialty == "Cardiology"


def test_gcp_scheduling_book_conflict(monkeypatch) -> None:
    client = GcpSchedulingClient(
        base_url="https://example/fhir",
        headers=lambda: {"Authorization": "Bearer test"},
        patient_ref=lambda patient_id: f"Patient/{patient_id}",
    )
    slot = {
        "resourceType": "Slot",
        "id": "slot-1",
        "status": SlotStatus.FREE.value,
        "start": "2026-09-01T19:30:00+00:00",
        "end": "2026-09-01T20:00:00+00:00",
        "schedule": {"reference": "Schedule/schedule-1"},
        "extension": [
            {"url": "https://eir.local/scheduling/specialty", "valueString": "Cardiology"},
            {"url": "https://eir.local/scheduling/service-name", "valueString": "Cardiology"},
            {
                "url": "https://eir.local/scheduling/practitioner-name",
                "valueString": "Dr. Maya Chen",
            },
            {
                "url": "https://eir.local/scheduling/practitioner-id",
                "valueString": "practitioner-maya-chen",
            },
            {"url": "https://eir.local/scheduling/location-name", "valueString": "Main Clinic"},
            {"url": "https://eir.local/scheduling/location-id", "valueString": "location-main"},
        ],
    }

    def fake_get(url: str, **kwargs):
        if url.endswith("/Appointment"):
            return _FakeResponse(200, {"entry": []})
        if url.endswith("/Slot/slot-1"):
            return _FakeResponse(200, slot)
        raise AssertionError(url)

    def fake_post(url: str, **kwargs):
        return _FakeResponse(409, text="conflict")

    monkeypatch.setattr("httpx.get", fake_get)
    monkeypatch.setattr("httpx.post", fake_post)
    with pytest.raises(ValueError, match="conflict"):
        client.book_appointment(patient_id="patient-synthetic-001", slot_id="slot-1")


def test_gcp_scheduling_search_slots(monkeypatch) -> None:
    client = GcpSchedulingClient(
        base_url="https://example/fhir",
        headers=lambda: {"Authorization": "Bearer test"},
        patient_ref=lambda patient_id: f"Patient/{patient_id}",
    )

    def fake_get(url: str, **kwargs):
        if url.endswith("/Slot"):
            return _FakeResponse(
                200,
                {
                    "entry": [
                        {
                            "resource": {
                                "resourceType": "Slot",
                                "id": "slot-2",
                                "status": "free",
                                "start": "2030-01-01T14:30:00+00:00",
                                "end": "2030-01-01T15:00:00+00:00",
                                "schedule": {"reference": "Schedule/schedule-cardiology-main"},
                                "extension": [
                                    {
                                        "url": "https://eir.local/scheduling/specialty",
                                        "valueString": "Cardiology",
                                    },
                                    {
                                        "url": "https://eir.local/scheduling/service-name",
                                        "valueString": "Cardiology",
                                    },
                                    {
                                        "url": "https://eir.local/scheduling/practitioner-name",
                                        "valueString": "Dr. Maya Chen",
                                    },
                                    {
                                        "url": "https://eir.local/scheduling/practitioner-id",
                                        "valueString": "practitioner-maya-chen",
                                    },
                                    {
                                        "url": "https://eir.local/scheduling/location-name",
                                        "valueString": "Main Clinic",
                                    },
                                    {
                                        "url": "https://eir.local/scheduling/location-id",
                                        "valueString": "location-main-clinic",
                                    },
                                ],
                            }
                        }
                    ]
                },
            )
        raise AssertionError(url)

    monkeypatch.setattr("httpx.get", fake_get)
    params = SlotSearchParams(
        patient_id="patient-synthetic-001",
        specialty="Cardiology",
        time_of_day="afternoon",
    )
    slots = client.search_available_slots(params)
    assert len(slots) == 1
    assert slots[0].id == "slot-2"


def test_firestore_access_session_repository_roundtrip() -> None:
    store: dict[str, dict] = {}

    class _Doc:
        def __init__(self, doc_id: str) -> None:
            self._id = doc_id

        def set(self, data: dict) -> None:
            store[self._id] = data

        def get(self):
            exists = self._id in store
            return type("Snap", (), {"exists": exists, "to_dict": lambda s: store.get(self._id)})()

    class _Col:
        def document(self, doc_id: str) -> _Doc:
            return _Doc(doc_id)

        def where(self, *_args, **_kwargs):
            return self

        def stream(self):
            for value in store.values():
                yield type("Snap", (), {"to_dict": lambda s, v=value: v})()

    repo = FirestorePatientAccessSessionRepository(MagicMock(collection=lambda _n: _Col()))
    from app.domain.access.models import AccessChannel, PatientAccessSession

    session = PatientAccessSession(
        id="access-1",
        patient_id="patient-synthetic-001",
        channel=AccessChannel.WEB,
    )
    repo.save(session)
    loaded = repo.get("access-1")
    assert loaded is not None
    assert loaded.patient_id == "patient-synthetic-001"
