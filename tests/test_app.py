from fastapi.testclient import TestClient
from sqlalchemy import text

from src.db.connection import SessionLocal
from src.main import app
from src.utils.constant import ROLE_ADMIN
from src.utils.security import hash_password


def clean_up_order_workflow_test_data(username: str, email: str, material_code: str) -> None:
    db = SessionLocal()
    try:
        db.execute(
            text(
                """
                DELETE FROM orders
                WHERE material_id IN (
                    SELECT id FROM materials
                    WHERE material_code = :material_code
                )
                OR requested_by_user_id IN (
                    SELECT id FROM users
                    WHERE username = :username OR email = :email
                )
                OR reviewed_by_user_id IN (
                    SELECT id FROM users
                    WHERE username = :username OR email = :email
                )
                """
            ),
            {"username": username, "email": email, "material_code": material_code},
        )
        db.execute(
            text(
                """
                DELETE FROM inventory_audit_logs
                WHERE material_id IN (
                    SELECT id FROM materials
                    WHERE material_code = :material_code
                )
                """
            ),
            {"material_code": material_code},
        )
        db.execute(
            text("DELETE FROM materials WHERE material_code = :material_code"),
            {"material_code": material_code},
        )
        db.execute(
            text(
                """
                DELETE FROM token_table
                WHERE user_id IN (
                    SELECT id FROM users
                    WHERE username = :username OR email = :email
                )
                """
            ),
            {"username": username, "email": email},
        )
        db.execute(
            text("DELETE FROM users WHERE username = :username OR email = :email"),
            {"username": username, "email": email},
        )
        db.commit()
    finally:
        db.close()


def create_test_admin(username: str, email: str, password: str) -> None:
    db = SessionLocal()
    try:
        db.execute(
            text(
                """
                DELETE FROM token_table
                WHERE user_id IN (
                    SELECT id FROM users
                    WHERE username = :username OR email = :email
                )
                """
            ),
            {"username": username, "email": email},
        )
        db.execute(
            text("DELETE FROM users WHERE username = :username OR email = :email"),
            {"username": username, "email": email},
        )
        db.execute(
            text(
                """
                INSERT INTO users (username, email, password_hash, role)
                VALUES (:username, :email, :password_hash, :role)
                """
            ),
            {
                "username": username,
                "email": email,
                "password_hash": hash_password(password),
                "role": ROLE_ADMIN,
            },
        )
        db.commit()
    finally:
        db.close()


def create_test_viewer(
    client: TestClient,
    username: str,
    email: str,
    password: str,
) -> dict:
    response = client.post(
        "/users/register",
        json={
            "username": username,
            "email": email,
            "password": password,
        },
    )

    assert response.status_code == 201
    return response.json()


def login_test_user(client: TestClient, username: str, password: str) -> dict[str, str]:
    login_response = client.post(
        "/users/login",
        json={"username": username, "password": password},
    )

    assert login_response.status_code == 200
    token = login_response.json()["token"]
    return {"Authorization": f"Bearer {token}"}


def create_test_material(
    client: TestClient,
    headers: dict[str, str],
    material_code: str,
    material_name: str,
    quantity_available: int,
    location_id: int | None = None,
) -> dict:
    material_response = client.post(
        "/materials",
        json={
            "material_code": material_code,
            "material_name": material_name,
            "material_type": "chemical",
            "description": "Created by automated test",
            "source": "test",
            "quantity_available": quantity_available,
            "unit": "bottle",
            "minimum_quantity": 1,
            "qc_status": "passed",
            "storage_condition": "room temperature",
            "location_id": location_id,
        },
        headers=headers,
    )

    assert material_response.status_code == 201
    return material_response.json()


def create_test_location(
    client: TestClient,
    headers: dict[str, str],
    name: str,
) -> dict:
    location_response = client.post(
        "/locations",
        json={
            "name": name,
            "location_type": "freezer",
            "parent_location_id": None,
            "temperature_zone": "-20C",
            "description": "Created by automated test",
        },
        headers=headers,
    )

    assert location_response.status_code == 201
    return location_response.json()


def create_test_order(
    client: TestClient,
    headers: dict[str, str],
    material_id: int,
    requested_quantity: int = 3,
    request_notes: str = "Automated order test",
) -> dict:
    order_response = client.post(
        "/orders",
        json={
            "material_id": material_id,
            "requested_quantity": requested_quantity,
            "request_notes": request_notes,
        },
        headers=headers,
    )

    assert order_response.status_code == 201
    return order_response.json()


def test_health_check() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_list_materials_requires_auth() -> None:
    client = TestClient(app)

    response = client.get("/materials")

    assert response.status_code == 401

def test_search_materials_requires_auth() -> None:
    client = TestClient(app)

    response = client.get("/materials/search")

    assert response.status_code == 401

def test_create_material_requires_auth() -> None:
    client = TestClient(app)

    response = client.post("/materials", json={})

    assert response.status_code == 401

def test_update_material_requires_auth() -> None:
    client = TestClient(app)

    response = client.patch("/materials/1", json={})

    assert response.status_code == 401

def test_archive_material_requires_auth() -> None:
    client = TestClient(app)

    response = client.post("/materials/1/archive", params={"reason": "test"})

    assert response.status_code == 401

def test_restore_material_requires_auth() -> None:
    client = TestClient(app)

    response = client.post("/materials/1/restore")

    assert response.status_code == 401


def test_list_locations_requires_auth() -> None:
    client = TestClient(app)

    response = client.get("/locations")

    assert response.status_code == 401


def test_get_location_requires_auth() -> None:
    client = TestClient(app)

    response = client.get("/locations/1")

    assert response.status_code == 401


def test_create_location_requires_auth() -> None:
    client = TestClient(app)

    response = client.post("/locations", json={})

    assert response.status_code == 401


def test_update_location_requires_auth() -> None:
    client = TestClient(app)

    response = client.patch("/locations/1", json={})

    assert response.status_code == 401


def test_adjust_quantity_requires_auth() -> None:
    client = TestClient(app)

    response = client.post(
        "/materials/1/adjust-quantity",
        json={"quantity_available": 5, "reason": "cycle count correction"},
    )

    assert response.status_code == 401


def test_check_in_requires_auth() -> None:
    client = TestClient(app)

    response = client.post(
        "/materials/1/check-in",
        json={"quantity": 2, "reason": "received new stock"},
    )

    assert response.status_code == 401


def test_check_out_requires_auth() -> None:
    client = TestClient(app)

    response = client.post(
        "/materials/1/check-out",
        json={"quantity": 2, "reason": "used in experiment"},
    )

    assert response.status_code == 401


def test_move_material_requires_auth() -> None:
    client = TestClient(app)

    response = client.post(
        "/materials/1/move",
        json={"location_id": 1, "reason": "moved to freezer rack"},
    )

    assert response.status_code == 401


def test_audit_logs_requires_auth() -> None:
    client = TestClient(app)

    response = client.get("/audit-logs")

    assert response.status_code == 401


def test_low_stock_report_requires_auth() -> None:
    client = TestClient(app)

    response = client.get("/reports/low-stock")

    assert response.status_code == 401


def test_pending_orders_report_requires_auth() -> None:
    client = TestClient(app)

    response = client.get("/reports/pending-orders")

    assert response.status_code == 401


def test_recent_inventory_activity_report_requires_auth() -> None:
    client = TestClient(app)

    response = client.get("/reports/recent-inventory-activity")

    assert response.status_code == 401


def test_materials_by_location_report_requires_auth() -> None:
    client = TestClient(app)

    response = client.get("/reports/materials-by-location")

    assert response.status_code == 401


def test_create_order_requires_auth() -> None:
    client = TestClient(app)

    response = client.post(
        "/orders",
        json={"material_id": 1, "requested_quantity": 1},
    )

    assert response.status_code == 401


def test_list_orders_requires_auth() -> None:
    client = TestClient(app)

    response = client.get("/orders")

    assert response.status_code == 401


def test_get_order_requires_auth() -> None:
    client = TestClient(app)

    response = client.get("/orders/1")

    assert response.status_code == 401


def test_approve_order_requires_auth() -> None:
    client = TestClient(app)

    response = client.post("/orders/1/approve")

    assert response.status_code == 401


def test_reject_order_requires_auth() -> None:
    client = TestClient(app)

    response = client.post("/orders/1/reject")

    assert response.status_code == 401


def test_fulfill_order_requires_auth() -> None:
    client = TestClient(app)

    response = client.post("/orders/1/fulfill")

    assert response.status_code == 401


def test_cancel_order_requires_auth() -> None:
    client = TestClient(app)

    response = client.post("/orders/1/cancel")

    assert response.status_code == 401

def test_order_workflow_approve_and_fulfill() -> None:
    client = TestClient(app)

    username = "order_admin_test"
    email = "order_admin_test@example.com"
    password = "password123"
    material_code = "TEST-ORDER-WORKFLOW-001"
    clean_up_order_workflow_test_data(username, email, material_code)
    create_test_admin(username, email, password)

    headers = login_test_user(client, username, password)
    material = create_test_material(
        client,
        headers,
        material_code,
        "Order Workflow Test Material",
        10,
    )

    material_id = material["id"]
    assert material["quantity_available"] == 10
    assert material["quantity_reserved"] == 0

    order = create_test_order(
        client,
        headers,
        material_id,
        request_notes="Automated workflow test",
    )

    order_id = order["id"]
    assert order["status"] == "submitted"
    assert order["reserved_quantity"] == 0

    approve_response = client.post(
        f"/orders/{order_id}/approve",
        headers=headers,
    )

    assert approve_response.status_code == 200
    approved_order = approve_response.json()
    assert approved_order["status"] == "approved"
    assert approved_order["reserved_quantity"] == 3

    material_after_approve_response = client.get(
        f"/materials/{material_id}",
        headers=headers,
    )

    assert material_after_approve_response.status_code == 200
    material_after_approve = material_after_approve_response.json()
    assert material_after_approve["quantity_available"] == 10
    assert material_after_approve["quantity_reserved"] == 3

    fulfill_response = client.post(
        f"/orders/{order_id}/fulfill",
        headers=headers,
    )

    assert fulfill_response.status_code == 200
    fulfilled_order = fulfill_response.json()
    assert fulfilled_order["status"] == "fulfilled"

    material_after_fulfill_response = client.get(
        f"/materials/{material_id}",
        headers=headers,
    )

    assert material_after_fulfill_response.status_code == 200
    material_after_fulfill = material_after_fulfill_response.json()
    assert material_after_fulfill["quantity_available"] == 7
    assert material_after_fulfill["quantity_reserved"] == 0

def test_cannot_approve_order_with_insufficient_stock() -> None:
    client = TestClient(app)

    username = "insufficient_stock_admin"
    email = "insufficient_stock_admin@example.com"
    password = "password123"
    material_code = "TEST-INSUFFICIENT-STOCK-001"

    clean_up_order_workflow_test_data(username, email, material_code)
    create_test_admin(username, email, password)

    headers = login_test_user(client, username, password)
    material = create_test_material(
        client,
        headers,
        material_code,
        "Insufficient Stock Test Material",
        2,
    )

    material_id = material["id"]
    assert material["quantity_available"] == 2
    assert material["quantity_reserved"] == 0

    order = create_test_order(
        client,
        headers,
        material_id,
        request_notes="Request more than available",
    )

    order_id = order["id"]
    assert order["status"] == "submitted"

    approve_response = client.post(
        f"/orders/{order_id}/approve",
        headers=headers,
    )

    assert approve_response.status_code == 400

    material_after_approve_response = client.get(
        f"/materials/{material_id}",
        headers=headers,
    )

    assert material_after_approve_response.status_code == 200
    material_after_approve = material_after_approve_response.json()
    assert material_after_approve["quantity_available"] == 2
    assert material_after_approve["quantity_reserved"] == 0


def test_cannot_fulfill_order_twice() -> None:
    client = TestClient(app)

    username = "double_fulfill_admin"
    email = "double_fulfill_admin@example.com"
    password = "password123"
    material_code = "TEST-DOUBLE-FULFILL-001"

    clean_up_order_workflow_test_data(username, email, material_code)
    create_test_admin(username, email, password)

    headers = login_test_user(client, username, password)
    material = create_test_material(
        client,
        headers,
        material_code,
        "Double Fulfill Test Material",
        10,
    )

    material_id = material["id"]

    order = create_test_order(
        client,
        headers,
        material_id,
        request_notes="Double fulfill test",
    )

    order_id = order["id"]

    approve_response = client.post(
        f"/orders/{order_id}/approve",
        headers=headers,
    )

    assert approve_response.status_code == 200

    first_fulfill_response = client.post(
        f"/orders/{order_id}/fulfill",
        headers=headers,
    )

    assert first_fulfill_response.status_code == 200
    assert first_fulfill_response.json()["status"] == "fulfilled"

    second_fulfill_response = client.post(
        f"/orders/{order_id}/fulfill",
        headers=headers,
    )

    assert second_fulfill_response.status_code == 409

    material_after_second_fulfill_response = client.get(
        f"/materials/{material_id}",
        headers=headers,
    )

    assert material_after_second_fulfill_response.status_code == 200
    material_after_second_fulfill = material_after_second_fulfill_response.json()
    assert material_after_second_fulfill["quantity_available"] == 7
    assert material_after_second_fulfill["quantity_reserved"] == 0


def test_cancel_approved_order_releases_reserved_quantity() -> None:
    client = TestClient(app)

    username = "cancel_order_admin"
    email = "cancel_order_admin@example.com"
    password = "password123"
    material_code = "TEST-CANCEL-APPROVED-ORDER-001"

    clean_up_order_workflow_test_data(username, email, material_code)
    create_test_admin(username, email, password)

    headers = login_test_user(client, username, password)
    material = create_test_material(
        client,
        headers,
        material_code,
        "Cancel Approved Order Test Material",
        10,
    )

    material_id = material["id"]

    order = create_test_order(
        client,
        headers,
        material_id,
        request_notes="Cancel approved order test",
    )

    order_id = order["id"]

    approve_response = client.post(
        f"/orders/{order_id}/approve",
        headers=headers,
    )

    assert approve_response.status_code == 200
    approved_order = approve_response.json()
    assert approved_order["status"] == "approved"
    assert approved_order["reserved_quantity"] == 3

    material_after_approve_response = client.get(
        f"/materials/{material_id}",
        headers=headers,
    )

    assert material_after_approve_response.status_code == 200
    material_after_approve = material_after_approve_response.json()
    assert material_after_approve["quantity_available"] == 10
    assert material_after_approve["quantity_reserved"] == 3

    cancel_response = client.post(
        f"/orders/{order_id}/cancel",
        headers=headers,
    )

    assert cancel_response.status_code == 200
    canceled_order = cancel_response.json()
    assert canceled_order["status"] == "canceled"

    material_after_cancel_response = client.get(
        f"/materials/{material_id}",
        headers=headers,
    )

    assert material_after_cancel_response.status_code == 200
    material_after_cancel = material_after_cancel_response.json()
    assert material_after_cancel["quantity_available"] == 10
    assert material_after_cancel["quantity_reserved"] == 0


def test_user_cannot_view_another_users_order() -> None:
    client = TestClient(app)

    admin_username = "order_privacy_admin"
    admin_email = "order_privacy_admin@example.com"
    requester_username = "order_requester_user"
    requester_email = "order_requester_user@example.com"
    other_username = "other_order_user"
    other_email = "other_order_user@example.com"
    password = "password123"
    material_code = "TEST-ORDER-PRIVACY-001"

    clean_up_order_workflow_test_data(admin_username, admin_email, material_code)
    clean_up_order_workflow_test_data(requester_username, requester_email, material_code)
    clean_up_order_workflow_test_data(other_username, other_email, material_code)
    create_test_admin(admin_username, admin_email, password)

    requester_register_response = client.post(
        "/users/register",
        json={
            "username": requester_username,
            "email": requester_email,
            "password": password,
        },
    )
    other_register_response = client.post(
        "/users/register",
        json={
            "username": other_username,
            "email": other_email,
            "password": password,
        },
    )

    assert requester_register_response.status_code == 201
    assert other_register_response.status_code == 201

    admin_headers = login_test_user(client, admin_username, password)
    requester_headers = login_test_user(client, requester_username, password)
    other_headers = login_test_user(client, other_username, password)

    material = create_test_material(
        client,
        admin_headers,
        material_code,
        "Order Privacy Test Material",
        10,
    )

    material_id = material["id"]

    order = create_test_order(
        client,
        requester_headers,
        material_id,
        request_notes="Order privacy test",
    )

    order_id = order["id"]

    requester_get_response = client.get(
        f"/orders/{order_id}",
        headers=requester_headers,
    )
    other_get_response = client.get(
        f"/orders/{order_id}",
        headers=other_headers,
    )

    assert requester_get_response.status_code == 200
    assert other_get_response.status_code == 404


def test_admin_can_filter_orders_by_status() -> None:
    client = TestClient(app)

    username = "order_status_filter_admin"
    email = "order_status_filter_admin@example.com"
    password = "password123"
    submitted_material_code = "TEST-ORDER-STATUS-SUBMITTED-001"
    approved_material_code = "TEST-ORDER-STATUS-APPROVED-001"

    clean_up_order_workflow_test_data(username, email, submitted_material_code)
    clean_up_order_workflow_test_data(username, email, approved_material_code)
    create_test_admin(username, email, password)

    headers = login_test_user(client, username, password)
    submitted_material = create_test_material(
        client,
        headers,
        submitted_material_code,
        "Order Status Filter Submitted Material",
        10,
    )
    approved_material = create_test_material(
        client,
        headers,
        approved_material_code,
        "Order Status Filter Approved Material",
        10,
    )
    submitted_order = create_test_order(
        client,
        headers,
        submitted_material["id"],
        request_notes="Submitted filter test",
    )
    approved_order = create_test_order(
        client,
        headers,
        approved_material["id"],
        request_notes="Approved filter test",
    )

    approve_response = client.post(
        f"/orders/{approved_order['id']}/approve",
        headers=headers,
    )

    assert approve_response.status_code == 200

    filtered_response = client.get(
        "/orders",
        params={"status": "submitted"},
        headers=headers,
    )

    assert filtered_response.status_code == 200
    filtered_order_ids = {order["id"] for order in filtered_response.json()}
    assert submitted_order["id"] in filtered_order_ids
    assert approved_order["id"] not in filtered_order_ids


def test_admin_can_filter_orders_by_material_id() -> None:
    client = TestClient(app)

    username = "order_material_filter_admin"
    email = "order_material_filter_admin@example.com"
    password = "password123"
    first_material_code = "TEST-ORDER-MATERIAL-FILTER-001"
    second_material_code = "TEST-ORDER-MATERIAL-FILTER-002"

    clean_up_order_workflow_test_data(username, email, first_material_code)
    clean_up_order_workflow_test_data(username, email, second_material_code)
    create_test_admin(username, email, password)

    headers = login_test_user(client, username, password)
    first_material = create_test_material(
        client,
        headers,
        first_material_code,
        "Order Material Filter One",
        10,
    )
    second_material = create_test_material(
        client,
        headers,
        second_material_code,
        "Order Material Filter Two",
        10,
    )
    first_order = create_test_order(
        client,
        headers,
        first_material["id"],
        request_notes="First material filter test",
    )
    second_order = create_test_order(
        client,
        headers,
        second_material["id"],
        request_notes="Second material filter test",
    )

    filtered_response = client.get(
        "/orders",
        params={"material_id": first_material["id"]},
        headers=headers,
    )

    assert filtered_response.status_code == 200
    filtered_order_ids = {order["id"] for order in filtered_response.json()}
    assert first_order["id"] in filtered_order_ids
    assert second_order["id"] not in filtered_order_ids


def test_user_cannot_filter_into_another_users_orders() -> None:
    client = TestClient(app)

    admin_username = "order_user_filter_admin"
    admin_email = "order_user_filter_admin@example.com"
    requester_username = "order_filter_requester_user"
    requester_email = "order_filter_requester_user@example.com"
    other_username = "order_filter_other_user"
    other_email = "order_filter_other_user@example.com"
    password = "password123"
    material_code = "TEST-ORDER-USER-FILTER-001"

    clean_up_order_workflow_test_data(admin_username, admin_email, material_code)
    clean_up_order_workflow_test_data(requester_username, requester_email, material_code)
    clean_up_order_workflow_test_data(other_username, other_email, material_code)
    create_test_admin(admin_username, admin_email, password)
    requester = create_test_viewer(
        client,
        requester_username,
        requester_email,
        password,
    )
    other_user = create_test_viewer(
        client,
        other_username,
        other_email,
        password,
    )

    admin_headers = login_test_user(client, admin_username, password)
    requester_headers = login_test_user(client, requester_username, password)
    other_headers = login_test_user(client, other_username, password)

    material = create_test_material(
        client,
        admin_headers,
        material_code,
        "Order User Filter Test Material",
        10,
    )
    requester_order = create_test_order(
        client,
        requester_headers,
        material["id"],
        request_notes="Requester order filter test",
    )
    other_order = create_test_order(
        client,
        other_headers,
        material["id"],
        request_notes="Other user order filter test",
    )

    filtered_response = client.get(
        "/orders",
        params={"requested_by_user_id": other_user["id"]},
        headers=requester_headers,
    )

    assert filtered_response.status_code == 200
    filtered_order_ids = {order["id"] for order in filtered_response.json()}
    assert requester_order["id"] in filtered_order_ids
    assert other_order["id"] not in filtered_order_ids
    assert all(
        order["requested_by_user_id"] == requester["id"]
        for order in filtered_response.json()
    )


def test_low_stock_report_includes_material_at_or_below_minimum() -> None:
    client = TestClient(app)

    username = "low_stock_report_admin"
    email = "low_stock_report_admin@example.com"
    password = "password123"
    low_stock_material_code = "TEST-LOW-STOCK-REPORT-001"
    enough_stock_material_code = "TEST-ENOUGH-STOCK-REPORT-001"

    clean_up_order_workflow_test_data(username, email, low_stock_material_code)
    clean_up_order_workflow_test_data(username, email, enough_stock_material_code)
    create_test_admin(username, email, password)

    headers = login_test_user(client, username, password)
    low_stock_material = create_test_material(
        client,
        headers,
        low_stock_material_code,
        "Low Stock Report Material",
        1,
    )
    enough_stock_material = create_test_material(
        client,
        headers,
        enough_stock_material_code,
        "Enough Stock Report Material",
        10,
    )

    low_stock_response = client.get("/reports/low-stock", headers=headers)

    assert low_stock_response.status_code == 200
    reported_material_codes = {
        material["material_code"]
        for material in low_stock_response.json()
    }
    assert low_stock_material["material_code"] in reported_material_codes
    assert enough_stock_material["material_code"] not in reported_material_codes


def test_pending_orders_report_includes_submitted_orders_only() -> None:
    client = TestClient(app)

    username = "pending_orders_report_admin"
    email = "pending_orders_report_admin@example.com"
    password = "password123"
    pending_material_code = "TEST-PENDING-ORDERS-REPORT-001"
    approved_material_code = "TEST-APPROVED-ORDERS-REPORT-001"

    clean_up_order_workflow_test_data(username, email, pending_material_code)
    clean_up_order_workflow_test_data(username, email, approved_material_code)
    create_test_admin(username, email, password)

    headers = login_test_user(client, username, password)
    pending_material = create_test_material(
        client,
        headers,
        pending_material_code,
        "Pending Orders Report Material",
        10,
    )
    approved_material = create_test_material(
        client,
        headers,
        approved_material_code,
        "Approved Orders Report Material",
        10,
    )
    pending_order = create_test_order(
        client,
        headers,
        pending_material["id"],
        request_notes="Pending order report test",
    )
    approved_order = create_test_order(
        client,
        headers,
        approved_material["id"],
        request_notes="Approved order report test",
    )

    approve_response = client.post(
        f"/orders/{approved_order['id']}/approve",
        headers=headers,
    )

    assert approve_response.status_code == 200

    pending_orders_response = client.get("/reports/pending-orders", headers=headers)

    assert pending_orders_response.status_code == 200
    reported_order_ids = {
        order["id"]
        for order in pending_orders_response.json()
    }
    assert pending_order["id"] in reported_order_ids
    assert approved_order["id"] not in reported_order_ids


def test_recent_inventory_activity_report_includes_inventory_audit_details() -> None:
    client = TestClient(app)

    username = "recent_activity_report_admin"
    email = "recent_activity_report_admin@example.com"
    password = "password123"
    material_code = "TEST-RECENT-ACTIVITY-REPORT-001"

    clean_up_order_workflow_test_data(username, email, material_code)
    create_test_admin(username, email, password)

    headers = login_test_user(client, username, password)
    material = create_test_material(
        client,
        headers,
        material_code,
        "Recent Activity Report Material",
        10,
    )
    material_id = material["id"]

    adjust_response = client.post(
        f"/materials/{material_id}/adjust-quantity",
        json={
            "quantity_available": 7,
            "reason": "recent activity report test",
        },
        headers=headers,
    )

    assert adjust_response.status_code == 200

    recent_activity_response = client.get(
        "/reports/recent-inventory-activity",
        headers=headers,
    )

    assert recent_activity_response.status_code == 200
    matching_activity = [
        activity
        for activity in recent_activity_response.json()
        if activity["material_code"] == material_code
    ]

    assert len(matching_activity) == 1
    activity = matching_activity[0]
    assert activity["username"] == username
    assert activity["material_name"] == "Recent Activity Report Material"
    assert activity["operation_type"] == "adjust_quantity"
    assert activity["before_value"] in {"10", "10.00"}
    assert activity["after_value"] in {"7", "7.00"}
    assert activity["reason"] == "recent activity report test"


def test_materials_by_location_report_groups_material_inventory() -> None:
    client = TestClient(app)

    username = "materials_by_location_report_admin"
    email = "materials_by_location_report_admin@example.com"
    password = "password123"
    first_material_code = "TEST-MATERIALS-BY-LOCATION-001"
    second_material_code = "TEST-MATERIALS-BY-LOCATION-002"
    location_name = "Report Freezer A"

    clean_up_order_workflow_test_data(username, email, first_material_code)
    clean_up_order_workflow_test_data(username, email, second_material_code)
    create_test_admin(username, email, password)

    headers = login_test_user(client, username, password)
    location = create_test_location(
        client,
        headers,
        location_name,
    )
    location_id = location["id"]

    create_test_material(
        client,
        headers,
        first_material_code,
        "Materials By Location Report Material One",
        4,
        location_id,
    )
    create_test_material(
        client,
        headers,
        second_material_code,
        "Materials By Location Report Material Two",
        6,
        location_id,
    )

    materials_by_location_response = client.get(
        "/reports/materials-by-location",
        headers=headers,
    )

    assert materials_by_location_response.status_code == 200
    matching_locations = [
        location
        for location in materials_by_location_response.json()
        if location["location_id"] == location_id
    ]

    assert len(matching_locations) == 1
    location_report = matching_locations[0]
    assert location_report["location_name"] == location_name
    assert location_report["material_count"] == 2
    assert location_report["total_quantity_available"] == 10
    assert location_report["total_quantity_reserved"] == 0
