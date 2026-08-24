from app.core.deps import get_container
from app.main import app
from fastapi.testclient import TestClient


def setup_function() -> None:
    get_container.cache_clear()
    get_container().seed()


def _login(client: TestClient, username: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": f"demo-{username}"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['token']}"}


def test_alex_medications_api_returns_coded_prescriptions() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/patients/patient-synthetic-001/medications")
        assert response.status_code == 200
        body = response.json()
        skus = {item["sku"] for item in body}
        assert skus == {"MED-ENOX-40", "MED-PARA-500", "MED-AMOX-500"}
        enox = next(item for item in body if item["sku"] == "MED-ENOX-40")
        assert enox["critical"] is True


def test_inventory_lists_patient_counts() -> None:
    with TestClient(app) as client:
        admin = _login(client, "admin")
        response = client.get("/api/v1/inventory", headers=admin)
        assert response.status_code == 200
        by_sku = {item["sku"]: item for item in response.json()}
        assert by_sku["MED-ENOX-40"]["patient_count"] == 1
        assert by_sku["MED-PARA-500"]["patient_count"] == 1
        assert by_sku["MED-METF-850"]["patient_count"] == 0
        assert "rxnorm_code" in by_sku["MED-ENOX-40"]


def test_prescription_usage_floor_keeps_fixture_when_derived_is_lower() -> None:
    from app.services.medications import overlay_daily_usage
    from eir_shared.supply import InventoryItem, daily_units_from_medication_request

    item = InventoryItem(sku="MED-ENOX-40", name="Enoxaparin", daily_usage=18.0)
    overlaid = overlay_daily_usage(item, 1.0)
    assert overlaid.daily_usage == 18.0
    raised = overlay_daily_usage(item, 22.0)
    assert raised.daily_usage == 22.0
    resource = {
        "status": "active",
        "dosageInstruction": [
            {"timing": {"repeat": {"frequency": 1, "period": 8, "periodUnit": "h"}}}
        ],
    }
    assert daily_units_from_medication_request(resource) == 3.0
