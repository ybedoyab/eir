"""Supply & replenishment workflow.

The load-bearing claim of this module is that an agent can source a purchase but
cannot spend money on its own. Most of these tests exist to keep that true.
"""

from datetime import UTC, datetime
from pathlib import Path

from app.core.deps import get_container
from app.main import app
from app.services.stock_monitor import StockMonitor
from eir_shared.events import RECOVERY_EVENT_TYPES, SUPPLY_EVENT_TYPES
from eir_shared.supply import InventoryItem
from fastapi.testclient import TestClient

DEMO_SKU = "MED-ENOX-40"


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


def _open_demo_case(client: TestClient) -> dict:
    response = client.post("/api/v1/demo/supply/bootstrap", json={"sku": DEMO_SKU})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["opened"] is True
    return body


def test_low_stock_runs_the_fleet_and_stops_at_a_draft_order() -> None:
    with TestClient(app) as client:
        admin = _login(client, "admin")
        body = _open_demo_case(client)
        case_id = body["case_id"]

        case = client.get(f"/api/v1/supply/cases/{case_id}", headers=admin).json()
        assert case["status"] == "AWAITING_APPROVAL"
        assert case["assigned_agents"] == ["inventory", "procurement"]

        order = case["purchase_order"]
        assert order is not None
        assert order["status"] == "DRAFT", "an agent must not place its own order"
        assert order["approved_by"] == ""

        events = client.get(f"/api/v1/supply/cases/{case_id}/events", headers=admin).json()
        types = [item["event_type"] for item in events]
        assert types[0] == "InventoryLevelLow"
        assert "ReplenishmentRequested" in types
        assert types.count("SupplierContacted") == 3
        assert "SupplierQuoteReceived" in types
        assert "PurchaseOrderDrafted" in types
        assert "PurchaseOrderApproved" not in types
        assert "RestockScheduled" not in types


def test_supplier_choice_prefers_availability_over_price() -> None:
    with TestClient(app) as client:
        admin = _login(client, "admin")
        case_id = _open_demo_case(client)["case_id"]
        case = client.get(f"/api/v1/supply/cases/{case_id}", headers=admin).json()

        quotes = {item["supplier_name"]: item for item in case["quotes"]}
        cheapest = min(case["quotes"], key=lambda item: item["unit_price"])
        chosen = case["purchase_order"]["supplier_name"]

        assert cheapest["supplier_name"] != chosen, "cheapest quote should have lost"
        assert cheapest["available_units"] < case["requested_quantity"]
        assert quotes[chosen]["available_units"] >= case["requested_quantity"]


def test_quotes_only_record_what_a_supplier_stated() -> None:
    with TestClient(app) as client:
        admin = _login(client, "admin")
        case_id = _open_demo_case(client)["case_id"]
        case = client.get(f"/api/v1/supply/cases/{case_id}", headers=admin).json()

        for quote in case["quotes"]:
            spoken = " ".join(
                turn["text"] for turn in quote["transcript"] if turn["role"] == "supplier"
            )
            assert str(quote["available_units"]) in spoken
            assert f"{quote['unit_price']:.2f}" in spoken


def test_approval_places_the_order_and_records_the_approver() -> None:
    with TestClient(app) as client:
        admin = _login(client, "admin")
        case_id = _open_demo_case(client)["case_id"]

        approved = client.post(
            f"/api/v1/supply/cases/{case_id}/approve",
            json={"note": "authorized in test"},
            headers=admin,
        )
        assert approved.status_code == 200, approved.text
        case = approved.json()

        assert case["status"] == "ORDERED"
        order = case["purchase_order"]
        assert order["status"] == "PLACED"
        assert order["approved_by"] == "admin"
        assert order["expected_delivery"] is not None

        events = client.get(f"/api/v1/supply/cases/{case_id}/events", headers=admin).json()
        types = [item["event_type"] for item in events]
        assert "SupplyApprovalGranted" in types
        assert "PurchaseOrderApproved" in types
        assert "RestockScheduled" in types


def test_approval_is_rejected_when_nothing_is_awaiting_authorization() -> None:
    with TestClient(app) as client:
        admin = _login(client, "admin")
        case_id = _open_demo_case(client)["case_id"]
        client.post(f"/api/v1/supply/cases/{case_id}/approve", json={}, headers=admin)

        # A second approval has no pending authorization to consume.
        again = client.post(
            f"/api/v1/supply/cases/{case_id}/approve",
            json={},
            headers=admin,
        )
        assert again.status_code == 409


def test_only_operations_can_authorize_a_purchase() -> None:
    with TestClient(app) as client:
        clinician = _login(client, "clinician")
        case_id = _open_demo_case(client)["case_id"]

        response = client.post(
            f"/api/v1/supply/cases/{case_id}/approve",
            json={},
            headers=clinician,
        )
        assert response.status_code == 403


def test_purchase_approvals_stay_out_of_the_clinician_queue() -> None:
    with TestClient(app) as client:
        admin = _login(client, "admin")
        _open_demo_case(client)

        clinical = client.get("/api/v1/reviews").json()
        assert all(item.get("workflow", "recovery") == "recovery" for item in clinical)

        supply_reviews = client.get("/api/v1/supply/approvals", headers=admin).json()
        assert supply_reviews
        assert all(item["workflow"] == "supply" for item in supply_reviews)
        assert all(item["capability"] == "purchase_order.approve" for item in supply_reviews)


def test_supply_review_cannot_be_resolved_through_the_clinical_endpoint() -> None:
    with TestClient(app) as client:
        admin = _login(client, "admin")
        _open_demo_case(client)
        review = client.get("/api/v1/supply/approvals", headers=admin).json()[0]

        response = client.post(f"/api/v1/reviews/{review['id']}/resolve", json={"note": "x"})
        assert response.status_code == 409


def test_delivery_restores_stock_and_closes_the_case() -> None:
    with TestClient(app) as client:
        admin = _login(client, "admin")
        case_id = _open_demo_case(client)["case_id"]
        client.post(f"/api/v1/supply/cases/{case_id}/approve", json={}, headers=admin)

        before = client.get(f"/api/v1/inventory/{DEMO_SKU}", headers=admin).json()
        received = client.post(f"/api/v1/supply/cases/{case_id}/receive", headers=admin)
        assert received.status_code == 200

        case = received.json()
        assert case["status"] == "COMPLETED"
        assert case["purchase_order"]["status"] == "RECEIVED"

        after = client.get(f"/api/v1/inventory/{DEMO_SKU}", headers=admin).json()
        assert after["on_hand"] == before["on_hand"] + case["purchase_order"]["quantity"]
        assert after["status"] == "HEALTHY"


def test_delivery_is_refused_for_an_unapproved_draft() -> None:
    with TestClient(app) as client:
        admin = _login(client, "admin")
        case_id = _open_demo_case(client)["case_id"]

        response = client.post(f"/api/v1/supply/cases/{case_id}/receive", headers=admin)
        assert response.status_code == 409


def test_stock_monitor_opens_one_case_per_stock_out() -> None:
    container = get_container()
    monitor = StockMonitor(container.supply)
    now = datetime.now(UTC)

    first = monitor.process_due(now=now, idempotency_key="run-1")
    assert first, "seeded fixtures include medications below the reorder point"

    # A second scheduler run must not stack a duplicate order on the same SKU.
    second = monitor.process_due(now=now, idempotency_key="run-2")
    assert second == []

    skus = [event.sku for event in first]
    assert len(skus) == len(set(skus))


def test_stock_monitor_ignores_a_replayed_scheduler_run() -> None:
    container = get_container()
    monitor = StockMonitor(container.supply, idempotency=container.scheduler_idempotency)
    now = datetime.now(UTC)

    monitor.process_due(now=now, idempotency_key="same-key")
    replay = monitor.process_due(now=now, idempotency_key="same-key")
    assert replay == []


def test_healthy_stock_does_not_open_a_case() -> None:
    container = get_container()
    container.supply.save_item(
        InventoryItem(
            sku="MED-TEST-OK",
            name="Well stocked",
            on_hand=500,
            reorder_point=100,
            target_level=600,
            daily_usage=5,
        )
    )
    claimed = container.supply.claim_replenishment("MED-TEST-OK", now=datetime.now(UTC))
    assert claimed is None


def test_each_runtime_subscribes_only_to_its_own_events() -> None:
    """Regression guard for the event-bus split.

    Each runtime returns silently for an aggregate it does not own, so a shared
    subscription would swallow the other workflow with no trace.
    """
    container = get_container()
    handlers = container.event_bus._handlers

    assert container.supply_runtime.handle in handlers["InventoryLevelLow"]
    assert container.runtime.handle not in handlers["InventoryLevelLow"]

    assert container.runtime.handle in handlers["FollowUpDue"]
    assert container.supply_runtime.handle not in handlers["FollowUpDue"]

    assert not (RECOVERY_EVENT_TYPES & SUPPLY_EVENT_TYPES)


def test_demo_controls_refuse_a_non_synthetic_sku() -> None:
    with TestClient(app) as client:
        response = client.post("/api/v1/demo/supply/bootstrap", json={"sku": "REAL-SKU-1"})
        assert response.status_code == 403


def test_admin_snapshot_reports_supply_pressure() -> None:
    with TestClient(app) as client:
        admin = _login(client, "admin")
        _open_demo_case(client)

        snapshot = client.get("/api/v1/admin/snapshot", headers=admin).json()
        assert snapshot["low_stock_skus"] >= 1
        assert snapshot["open_replenishments"] >= 1
        assert snapshot["pending_purchase_approvals"] >= 1


def test_file_store_survives_a_restart(tmp_path) -> None:
    """The default local store is file-backed, so the round-trip has to hold.

    Cloud Run restarts mid-demo are the failure this guards against: a lost case
    would let the scheduler open a duplicate purchase order for the same SKU.
    """
    from app.repositories.file_store import FileSupplyRepository
    from app.services.supply_service import SupplyService

    path = tmp_path / "supply.json"
    repo = FileSupplyRepository(path)
    SupplyService(repo).seed(
        Path("mocks/inventory/inventory.json"),
        Path("mocks/suppliers/suppliers.json"),
    )
    claimed = repo.claim_replenishment(DEMO_SKU, now=datetime.now(UTC))
    assert claimed is not None

    reloaded = FileSupplyRepository(path)
    case = reloaded.get_case(claimed.episode_id)
    item = reloaded.get_item(DEMO_SKU)

    assert case is not None and case.sku == DEMO_SKU
    assert [event.event_type for event in reloaded.list_events(case.id)] == ["InventoryLevelLow"]
    assert item is not None and item.days_of_cover is not None
    assert reloaded.open_case_for_sku(DEMO_SKU) is not None
    assert reloaded.claim_replenishment(DEMO_SKU, now=datetime.now(UTC)) is None
