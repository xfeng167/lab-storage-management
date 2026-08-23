import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from src.db.connection import SessionLocal
from src.main import app
from src.order import service as order_service
from src.user import service as user_service
from src.user.schemas import UserCreate, UserRead
from src.utils.constant import ROLE_ADMIN, ROLE_STAFF
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
    create_test_user_with_role(username, email, password, ROLE_ADMIN)


def create_test_user_with_role(
    username: str,
    email: str,
    password: str,
    role: str,
) -> None:
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
                "role": role,
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
    parent_location_id: int | None = None,
) -> dict:
    location_response = client.post(
        "/locations",
        json={
            "name": name,
            "location_type": "freezer",
            "parent_location_id": parent_location_id,
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


def page_items(response) -> list[dict]:
    body = response.json()
    assert set(body) == {"items", "page", "size", "total", "pages"}
    return body["items"]


def assert_order_audit_visible_in_api_and_report(
    client: TestClient,
    headers: dict[str, str],
    *,
    material_id: int,
    material_code: str,
    material_name: str,
    username: str,
    user_id: int,
    operation_type: str,
    before: dict[str, int],
    after: dict[str, int],
    reason: str,
) -> dict:
    audit_response = client.get(
        "/audit-logs",
        params={"material_id": material_id, "operation_type": operation_type},
        headers=headers,
    )
    assert audit_response.status_code == 200
    audit_logs = page_items(audit_response)
    assert len(audit_logs) == 1
    audit_log = audit_logs[0]
    assert audit_log["user_id"] == user_id
    assert audit_log["material_id"] == material_id
    assert audit_log["operation_type"] == operation_type
    assert json.loads(audit_log["before_value"]) == before
    assert json.loads(audit_log["after_value"]) == after
    assert audit_log["reason"] == reason

    report_response = client.get(
        "/reports/recent-inventory-activity",
        params={"material_id": material_id, "operation_type": operation_type},
        headers=headers,
    )
    assert report_response.status_code == 200
    report_entries = report_response.json()
    assert len(report_entries) == 1
    report_entry = report_entries[0]
    assert report_entry["id"] == audit_log["id"]
    assert report_entry["user_id"] == user_id
    assert report_entry["username"] == username
    assert report_entry["material_id"] == material_id
    assert report_entry["material_code"] == material_code
    assert report_entry["material_name"] == material_name
    assert report_entry["operation_type"] == operation_type
    assert json.loads(report_entry["before_value"]) == before
    assert json.loads(report_entry["after_value"]) == after
    assert report_entry["reason"] == reason
    assert report_entry["created_at"] == audit_log["created_at"]
    return audit_log


def assert_api_error(
    response,
    *,
    status_code: int,
    code: str,
    message: str | None = None,
) -> dict:
    assert response.status_code == status_code
    body = response.json()
    assert set(body) == {"error"}
    assert body["error"]["code"] == code
    if message is not None:
        assert body["error"]["message"] == message
    return body["error"]


def test_health_check() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["x-request-id"]


def test_database_readiness_check_reports_migration() -> None:
    response = TestClient(app).get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "database": "ok",
        "migration": "20260812_0004",
    }


def test_first_admin_bootstrap_is_single_use() -> None:
    db = SessionLocal()
    try:
        payload = UserCreate(
            username="bootstrap_admin",
            email="bootstrap_admin@example.com",
            password="password123",
        )
        user, error = user_service.bootstrap_admin(db, payload)
        assert error is None
        assert user is not None and user.role == ROLE_ADMIN

        duplicate, duplicate_error = user_service.bootstrap_admin(db, payload)
        assert duplicate is None
        assert duplicate_error == "admin_exists"
    finally:
        db.close()


def test_test_table_api_is_not_registered() -> None:
    client = TestClient(app)

    responses = [
        client.get("/test-table"),
        client.post("/test-table", json={"name": "test data"}),
        client.patch("/test-table/1", json={"name": "updated test data"}),
        client.delete("/test-table/1"),
    ]

    assert all(response.status_code == 404 for response in responses)
    assert all(
        response.json() == {
            "error": {"code": "ROUTE_NOT_FOUND", "message": "Route not found"}
        }
        for response in responses
    )
    openapi_paths = client.get("/openapi.json").json()["paths"]
    assert not any(path.startswith("/test-table") for path in openapi_paths)


def test_openapi_documents_auth_roles_stock_policy_and_planned_modules() -> None:
    client = TestClient(app)

    schema = client.get("/openapi.json").json()
    description = schema["info"]["description"]

    assert all(
        path in description
        for path in (
            "/users/register",
            "/users/login",
            "/users/logout",
            "/users/me",
        )
    )
    assert all(role in description for role in ("Viewer", "Staff", "Admin"))
    assert "quantity_available - quantity_reserved" in description
    assert "QC flags, QC execution, and shipment records are planned" in description
    assert schema["components"]["securitySchemes"]["BearerAuth"] == {
        "type": "http",
        "description": "Token returned by POST /users/login.",
        "scheme": "bearer",
        "bearerFormat": "opaque token",
    }
    assert schema["paths"]["/materials"]["get"]["security"] == [
        {"BearerAuth": []}
    ]
    assert "security" not in schema["paths"]["/users/login"]["post"]
    assert "/qc-flags" not in schema["paths"]
    assert "/qc/run" not in schema["paths"]
    assert not any(path.startswith("/shipments") for path in schema["paths"])


def test_errors_use_one_structured_contract() -> None:
    client = TestClient(app)

    auth_error = client.get("/materials")
    validation_error = client.post(
        "/users/register",
        json={"username": "bad", "email": "invalid", "password": "weak"},
    )

    assert_api_error(
        auth_error,
        status_code=401,
        code="AUTH_HEADER_MISSING",
        message="Missing authorization header",
    )
    assert auth_error.headers["www-authenticate"] == "Bearer"
    validation = assert_api_error(
        validation_error,
        status_code=422,
        code="VALIDATION_ERROR",
        message="Request validation failed",
    )
    assert isinstance(validation["details"], list)


def test_registration_rejects_invalid_username_email_and_password() -> None:
    client = TestClient(app)

    invalid_username_response = client.post(
        "/users/register",
        json={
            "username": "1bad",
            "email": "valid@example.com",
            "password": "password123",
        },
    )
    assert invalid_username_response.status_code == 422

    invalid_email_response = client.post(
        "/users/register",
        json={
            "username": "valid_user",
            "email": "not-an-email",
            "password": "password123",
        },
    )
    assert invalid_email_response.status_code == 422

    invalid_password_response = client.post(
        "/users/register",
        json={
            "username": "valid_user",
            "email": "valid@example.com",
            "password": "password",
        },
    )
    assert invalid_password_response.status_code == 422


def test_user_can_update_profile_and_picture() -> None:
    client = TestClient(app)

    username = "profile_user"
    email = "profile_user@example.com"
    password = "password123"

    create_test_viewer(client, username, email, password)
    headers = login_test_user(client, username, password)

    response = client.patch(
        "/users/me",
        json={
            "username": "profile_updated",
            "email": "profile_updated@example.com",
            "profile_picture": "data:image/png;base64,abc123",
        },
        headers=headers,
    )

    assert response.status_code == 200
    updated_user = response.json()
    assert updated_user["username"] == "profile_updated"
    assert updated_user["email"] == "profile_updated@example.com"
    assert updated_user["profile_picture"] == "data:image/png;base64,abc123"

    me_response = client.get("/users/me", headers=headers)
    assert me_response.status_code == 200
    assert me_response.json()["username"] == "profile_updated"

    clear_picture_response = client.patch(
        "/users/me",
        json={
            "username": "profile_updated",
            "email": "profile_updated@example.com",
            "profile_picture": None,
        },
        headers=headers,
    )
    assert clear_picture_response.status_code == 200
    assert clear_picture_response.json()["profile_picture"] is None


def test_user_cannot_update_profile_to_duplicate_identity() -> None:
    client = TestClient(app)

    first_username = "profile_first"
    first_email = "profile_first@example.com"
    second_username = "profile_second"
    second_email = "profile_second@example.com"
    password = "password123"

    create_test_viewer(client, first_username, first_email, password)
    create_test_viewer(client, second_username, second_email, password)
    headers = login_test_user(client, first_username, password)

    response = client.patch(
        "/users/me",
        json={
            "username": second_username,
            "email": first_email,
            "profile_picture": None,
        },
        headers=headers,
    )

    assert response.status_code == 409


def test_user_can_change_password() -> None:
    client = TestClient(app)

    username = "password_change_user"
    email = "password_change_user@example.com"
    current_password = "password123"
    new_password = "newpassword456"

    create_test_viewer(client, username, email, current_password)
    headers = login_test_user(client, username, current_password)

    response = client.post(
        "/users/me/password",
        json={
            "current_password": current_password,
            "new_password": new_password,
        },
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json() == {"message": "Password updated successfully."}
    assert client.post(
        "/users/login",
        json={"username": username, "password": current_password},
    ).status_code == 401
    assert client.post(
        "/users/login",
        json={"username": username, "password": new_password},
    ).status_code == 200


def test_password_change_revokes_every_existing_session() -> None:
    client = TestClient(app)
    username = "password_revoke_user"
    password = "password123"
    create_test_viewer(client, username, "password_revoke@example.com", password)
    first_headers = login_test_user(client, username, password)
    second_headers = login_test_user(client, username, password)

    response = client.post(
        "/users/me/password",
        json={"current_password": password, "new_password": "newpassword456"},
        headers=first_headers,
    )

    assert response.status_code == 200
    assert client.get("/users/me", headers=first_headers).status_code == 401
    assert client.get("/users/me", headers=second_headers).status_code == 401


def test_login_is_throttled_after_repeated_failures() -> None:
    client = TestClient(app)
    create_test_viewer(
        client,
        "throttled_user",
        "throttled_user@example.com",
        "password123",
    )

    for _ in range(5):
        assert client.post(
            "/users/login",
            json={"username": "throttled_user", "password": "incorrect123"},
        ).status_code == 401
    blocked = client.post(
        "/users/login",
        json={"username": "throttled_user", "password": "password123"},
    )
    assert_api_error(blocked, status_code=429, code="LOGIN_RATE_LIMITED")
    assert blocked.headers["retry-after"] == "900"


def test_password_change_validates_current_and_new_passwords() -> None:
    client = TestClient(app)

    username = "password_validation_user"
    email = "password_validation_user@example.com"
    password = "password123"

    create_test_viewer(client, username, email, password)
    headers = login_test_user(client, username, password)

    incorrect_current_response = client.post(
        "/users/me/password",
        json={
            "current_password": "incorrect123",
            "new_password": "newpassword456",
        },
        headers=headers,
    )
    assert_api_error(
        incorrect_current_response,
        status_code=400,
        code="CURRENT_PASSWORD_INVALID",
        message="Current password is incorrect.",
    )

    weak_password_response = client.post(
        "/users/me/password",
        json={
            "current_password": password,
            "new_password": "allletters",
        },
        headers=headers,
    )
    assert weak_password_response.status_code == 422

    unchanged_password_response = client.post(
        "/users/me/password",
        json={
            "current_password": password,
            "new_password": password,
        },
        headers=headers,
    )
    assert unchanged_password_response.status_code == 422

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


def test_location_parent_update_rejects_indirect_cycle() -> None:
    client = TestClient(app)

    username = "location_cycle_staff"
    email = "location_cycle_staff@example.com"
    password = "password123"
    create_test_user_with_role(username, email, password, ROLE_STAFF)
    headers = login_test_user(client, username, password)

    root_location = create_test_location(client, headers, "Cycle Root")
    child_location = create_test_location(
        client,
        headers,
        "Cycle Child",
        parent_location_id=root_location["id"],
    )
    grandchild_location = create_test_location(
        client,
        headers,
        "Cycle Grandchild",
        parent_location_id=child_location["id"],
    )

    response = client.patch(
        f"/locations/{root_location['id']}",
        json={"parent_location_id": grandchild_location["id"]},
        headers=headers,
    )

    assert_api_error(
        response,
        status_code=409,
        code="LOCATION_HIERARCHY_CYCLE",
        message="Location hierarchy cannot contain a cycle",
    )
    root_after = client.get(
        f"/locations/{root_location['id']}",
        headers=headers,
    ).json()
    assert root_after["parent_location_id"] is None


def test_concurrent_location_updates_cannot_create_a_cycle() -> None:
    client = TestClient(app)
    create_test_user_with_role(
        "location_race_staff",
        "location_race_staff@example.com",
        "password123",
        ROLE_STAFF,
    )
    headers = login_test_user(client, "location_race_staff", "password123")
    first = create_test_location(client, headers, "Concurrent Location A")
    second = create_test_location(client, headers, "Concurrent Location B")
    barrier = Barrier(2)

    def update(location_id: int, parent_id: int):
        barrier.wait()
        return TestClient(app).patch(
            f"/locations/{location_id}",
            json={"parent_location_id": parent_id},
            headers=headers,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(
            lambda pair: update(*pair),
            ((first["id"], second["id"]), (second["id"], first["id"])),
        ))

    assert sorted(response.status_code for response in responses) == [200, 409]
    first_after = client.get(f"/locations/{first['id']}", headers=headers).json()
    second_after = client.get(f"/locations/{second['id']}", headers=headers).json()
    assert not (
        first_after["parent_location_id"] == second["id"]
        and second_after["parent_location_id"] == first["id"]
    )


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


def test_viewer_can_create_and_cancel_own_order_but_cannot_manage_inventory() -> None:
    client = TestClient(app)

    admin_username = "viewer_permissions_admin"
    admin_email = "viewer_permissions_admin@example.com"
    viewer_username = "viewer_permissions_user"
    viewer_email = "viewer_permissions_user@example.com"
    password = "password123"
    material_code = "TEST-VIEWER-PERMISSIONS-001"

    clean_up_order_workflow_test_data(admin_username, admin_email, material_code)
    clean_up_order_workflow_test_data(viewer_username, viewer_email, material_code)
    create_test_admin(admin_username, admin_email, password)
    create_test_viewer(client, viewer_username, viewer_email, password)
    admin_headers = login_test_user(client, admin_username, password)
    viewer_headers = login_test_user(client, viewer_username, password)
    material = create_test_material(
        client,
        admin_headers,
        material_code,
        "Viewer Permissions Material",
        5,
    )

    order_response = client.post(
        "/orders",
        json={
            "material_id": material["id"],
            "requested_quantity": 1,
            "request_notes": "Viewer-created request",
        },
        headers=viewer_headers,
    )
    assert order_response.status_code == 201

    order_id = order_response.json()["id"]
    cancel_response = client.post(
        f"/orders/{order_id}/cancel",
        headers=viewer_headers,
    )
    inventory_response = client.post(
        f"/materials/{material['id']}/check-in",
        json={"quantity": 1, "reason": "Viewer must not manage stock"},
        headers=viewer_headers,
    )

    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == "canceled"
    assert inventory_response.status_code == 403


def test_viewer_cannot_cancel_another_users_order() -> None:
    client = TestClient(app)

    admin_username = "viewer_cancel_scope_admin"
    admin_email = "viewer_cancel_scope_admin@example.com"
    first_username = "viewer_cancel_scope_first"
    first_email = "viewer_cancel_scope_first@example.com"
    second_username = "viewer_cancel_scope_second"
    second_email = "viewer_cancel_scope_second@example.com"
    password = "password123"
    material_code = "TEST-VIEWER-CANCEL-SCOPE-001"

    for username, email in (
        (admin_username, admin_email),
        (first_username, first_email),
        (second_username, second_email),
    ):
        clean_up_order_workflow_test_data(username, email, material_code)
    create_test_admin(admin_username, admin_email, password)
    create_test_viewer(client, first_username, first_email, password)
    create_test_viewer(client, second_username, second_email, password)
    admin_headers = login_test_user(client, admin_username, password)
    first_headers = login_test_user(client, first_username, password)
    second_headers = login_test_user(client, second_username, password)
    material = create_test_material(
        client,
        admin_headers,
        material_code,
        "Viewer Cancel Scope Material",
        5,
    )
    order = create_test_order(client, first_headers, material["id"], 1)

    response = client.post(
        f"/orders/{order['id']}/cancel",
        headers=second_headers,
    )

    assert response.status_code == 404


def test_staff_permissions_match_the_documented_role_contract() -> None:
    client = TestClient(app)

    username = "role_contract_staff"
    email = "role_contract_staff@example.com"
    password = "password123"
    material_code = "TEST-ROLE-CONTRACT-STAFF-001"

    clean_up_order_workflow_test_data(username, email, material_code)
    create_test_user_with_role(username, email, password, ROLE_STAFF)
    headers = login_test_user(client, username, password)
    location = create_test_location(client, headers, "Staff Contract Location")
    material = create_test_material(
        client,
        headers,
        material_code,
        "Staff Contract Material",
        5,
        location["id"],
    )
    order = create_test_order(client, headers, material["id"], 1)

    assert client.get("/reports/low-stock", headers=headers).status_code == 200
    assert client.post(
        f"/materials/{material['id']}/check-in",
        json={"quantity": 1, "reason": "Staff inventory attempt"},
        headers=headers,
    ).status_code == 403
    assert client.post(
        f"/materials/{material['id']}/archive",
        params={"reason": "Staff archive attempt"},
        headers=headers,
    ).status_code == 403
    assert client.post(
        f"/orders/{order['id']}/approve",
        headers=headers,
    ).status_code == 403
    assert client.get("/audit-logs", headers=headers).status_code == 403
    assert client.get("/users", headers=headers).status_code == 403


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

def test_order_approval_and_fulfillment_audits_are_visible_via_api_and_report() -> None:
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
        json={"outcome_notes": "Inventory reserved for the request"},
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

    assert_order_audit_visible_in_api_and_report(
        client,
        headers,
        material_id=material_id,
        material_code=material_code,
        material_name="Order Workflow Test Material",
        username=username,
        user_id=approved_order["reviewed_by_user_id"],
        operation_type="order_reservation_created",
        before={"quantity_available": 10, "quantity_reserved": 0},
        after={"quantity_available": 10, "quantity_reserved": 3},
        reason=(
            f"Order #{order_id} approved; reservation created. "
            "Outcome notes: Inventory reserved for the request"
        ),
    )

    fulfill_response = client.post(
        f"/orders/{order_id}/fulfill",
        json={"outcome_notes": "Material handed to requester"},
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

    assert_order_audit_visible_in_api_and_report(
        client,
        headers,
        material_id=material_id,
        material_code=material_code,
        material_name="Order Workflow Test Material",
        username=username,
        user_id=fulfilled_order["reviewed_by_user_id"],
        operation_type="order_fulfilled",
        before={"quantity_available": 10, "quantity_reserved": 3},
        after={"quantity_available": 7, "quantity_reserved": 0},
        reason=(
            f"Order #{order_id} fulfilled. "
            "Outcome notes: Material handed to requester"
        ),
    )


def test_order_submission_rejects_insufficient_unreserved_stock() -> None:
    client = TestClient(app)

    username = "order_submission_stock_admin"
    email = "order_submission_stock_admin@example.com"
    password = "password123"
    material_code = "TEST-ORDER-SUBMISSION-STOCK-001"

    clean_up_order_workflow_test_data(username, email, material_code)
    create_test_admin(username, email, password)
    headers = login_test_user(client, username, password)
    material = create_test_material(
        client,
        headers,
        material_code,
        "Order Submission Stock Test Material",
        5,
    )
    order = create_test_order(
        client,
        headers,
        material["id"],
        requested_quantity=4,
    )
    approve_response = client.post(
        f"/orders/{order['id']}/approve",
        headers=headers,
    )
    assert approve_response.status_code == 200

    rejected_response = client.post(
        "/orders",
        json={
            "material_id": material["id"],
            "requested_quantity": 2,
            "request_notes": "Direct request exceeding unreserved stock",
        },
        headers=headers,
    )
    accepted_response = client.post(
        "/orders",
        json={
            "material_id": material["id"],
            "requested_quantity": 1,
            "request_notes": "Request exactly the unreserved stock",
        },
        headers=headers,
    )

    assert_api_error(
        rejected_response,
        status_code=409,
        code="ORDER_STOCK_INSUFFICIENT",
        message="Insufficient unreserved stock to submit order",
    )
    assert accepted_response.status_code == 201
    assert accepted_response.json()["requested_quantity"] == 1


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
        3,
    )

    material_id = material["id"]
    assert material["quantity_available"] == 3
    assert material["quantity_reserved"] == 0

    order = create_test_order(
        client,
        headers,
        material_id,
        request_notes="Request more than available",
    )

    order_id = order["id"]
    assert order["status"] == "submitted"
    assert order["requested_quantity"] == 3
    assert order["reserved_quantity"] == 0

    db = SessionLocal()
    try:
        db.execute(
            text(
                """
                UPDATE materials
                SET quantity_available = 2
                WHERE id = :material_id
                """
            ),
            {"material_id": material_id},
        )
        db.commit()
    finally:
        db.close()

    approve_response = client.post(
        f"/orders/{order_id}/approve",
        headers=headers,
    )

    assert_api_error(
        approve_response,
        status_code=409,
        code="ORDER_STOCK_INSUFFICIENT",
        message="Insufficient unreserved stock to approve order",
    )

    material_after_approve_response = client.get(
        f"/materials/{material_id}",
        headers=headers,
    )

    assert material_after_approve_response.status_code == 200
    material_after_approve = material_after_approve_response.json()
    assert material_after_approve["quantity_available"] == 2
    assert material_after_approve["quantity_reserved"] == 0

    order_after_approve_response = client.get(
        f"/orders/{order_id}",
        headers=headers,
    )
    assert order_after_approve_response.status_code == 200
    order_after_approve = order_after_approve_response.json()
    assert order_after_approve["status"] == "submitted"
    assert order_after_approve["reserved_quantity"] == 0

    audit_response = client.get(
        "/audit-logs",
        params={"material_id": material_id},
        headers=headers,
    )
    assert audit_response.status_code == 200
    assert page_items(audit_response) == []


def test_fulfillment_revalidates_reserved_stock_consistency() -> None:
    client = TestClient(app)

    username = "fulfillment_stock_validation_admin"
    email = "fulfillment_stock_validation_admin@example.com"
    password = "password123"
    material_code = "TEST-FULFILLMENT-STOCK-VALIDATION-001"

    clean_up_order_workflow_test_data(username, email, material_code)
    create_test_admin(username, email, password)
    headers = login_test_user(client, username, password)
    material = create_test_material(
        client,
        headers,
        material_code,
        "Fulfillment Stock Validation Test Material",
        10,
    )
    order = create_test_order(
        client,
        headers,
        material["id"],
        requested_quantity=3,
    )
    approve_response = client.post(
        f"/orders/{order['id']}/approve",
        headers=headers,
    )
    assert approve_response.status_code == 200

    db = SessionLocal()
    try:
        db.execute(
            text(
                """
                UPDATE materials
                SET quantity_reserved = 2
                WHERE id = :material_id
                """
            ),
            {"material_id": material["id"]},
        )
        db.commit()
    finally:
        db.close()

    fulfill_response = client.post(
        f"/orders/{order['id']}/fulfill",
        headers=headers,
    )

    assert_api_error(
        fulfill_response,
        status_code=409,
        code="ORDER_RESERVATION_INCONSISTENT",
        message="Reserved stock is inconsistent; order cannot be fulfilled",
    )

    material_after = client.get(
        f"/materials/{material['id']}",
        headers=headers,
    ).json()
    order_after = client.get(
        f"/orders/{order['id']}",
        headers=headers,
    ).json()
    audit_after_response = client.get(
        "/audit-logs",
        params={"material_id": material["id"]},
        headers=headers,
    )
    audit_items = page_items(audit_after_response)

    assert material_after["quantity_available"] == 10
    assert material_after["quantity_reserved"] == 2
    assert order_after["status"] == "approved"
    assert order_after["reserved_quantity"] == 3
    assert [entry["operation_type"] for entry in audit_items] == [
        "order_reservation_created"
    ]


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


def test_approved_order_cancellation_audit_is_visible_via_api_and_report() -> None:
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
        json={"outcome_notes": "Request withdrawn"},
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

    assert_order_audit_visible_in_api_and_report(
        client,
        headers,
        material_id=material_id,
        material_code=material_code,
        material_name="Cancel Approved Order Test Material",
        username=username,
        user_id=canceled_order["reviewed_by_user_id"],
        operation_type="order_reservation_released",
        before={"quantity_available": 10, "quantity_reserved": 3},
        after={"quantity_available": 10, "quantity_reserved": 0},
        reason=(
            f"Order #{order_id} canceled; reservation released. "
            "Outcome notes: Request withdrawn"
        ),
    )


def test_order_inventory_change_rolls_back_when_audit_write_fails(
    monkeypatch,
) -> None:
    client = TestClient(app)

    username = "order_audit_rollback_admin"
    email = "order_audit_rollback_admin@example.com"
    password = "password123"
    material_code = "TEST-ORDER-AUDIT-ROLLBACK-001"

    clean_up_order_workflow_test_data(username, email, material_code)
    create_test_admin(username, email, password)
    headers = login_test_user(client, username, password)
    current_user = UserRead(**client.get("/users/me", headers=headers).json())
    material = create_test_material(
        client,
        headers,
        material_code,
        "Order Audit Rollback Test Material",
        10,
    )
    order = create_test_order(
        client,
        headers,
        material["id"],
        requested_quantity=3,
    )
    approve_response = client.post(
        f"/orders/{order['id']}/approve",
        headers=headers,
    )
    assert approve_response.status_code == 200

    audit_before = client.get(
        "/audit-logs",
        params={"material_id": material["id"]},
        headers=headers,
    )
    audit_before_items = page_items(audit_before)

    def fail_audit_write(*args, **kwargs) -> None:
        raise RuntimeError("audit write failed")

    monkeypatch.setattr(
        order_service,
        "_log_order_inventory_audit",
        fail_audit_write,
    )

    db = SessionLocal()
    try:
        with pytest.raises(RuntimeError, match="audit write failed"):
            order_service.fulfill_order(db, order["id"], current_user)
        db.rollback()
    finally:
        db.close()

    material_after = client.get(
        f"/materials/{material['id']}",
        headers=headers,
    ).json()
    order_after = client.get(
        f"/orders/{order['id']}",
        headers=headers,
    ).json()
    audit_after = client.get(
        "/audit-logs",
        params={"material_id": material["id"]},
        headers=headers,
    )
    audit_after_items = page_items(audit_after)

    assert material_after["quantity_available"] == 10
    assert material_after["quantity_reserved"] == 3
    assert order_after["status"] == "approved"
    assert audit_after_items == audit_before_items


def test_concurrent_order_approvals_do_not_over_reserve_stock(monkeypatch) -> None:
    client = TestClient(app)

    username = "concurrent_approval_admin"
    email = "concurrent_approval_admin@example.com"
    password = "password123"
    material_code = "TEST-CONCURRENT-APPROVAL-001"

    clean_up_order_workflow_test_data(username, email, material_code)
    create_test_admin(username, email, password)
    headers = login_test_user(client, username, password)
    current_user = UserRead(**client.get("/users/me", headers=headers).json())
    material = create_test_material(
        client,
        headers,
        material_code,
        "Concurrent Approval Test Material",
        5,
    )
    orders = [
        create_test_order(client, headers, material["id"], requested_quantity=3),
        create_test_order(client, headers, material["id"], requested_quantity=3),
    ]

    unlocked_read_barrier = Barrier(2)
    original_get_material_inventory = order_service._get_material_inventory

    def synchronized_material_read(db, material_id, *, for_update=False):
        row = original_get_material_inventory(
            db,
            material_id,
            for_update=for_update,
        )
        if not for_update:
            unlocked_read_barrier.wait(timeout=5)
        return row

    monkeypatch.setattr(
        order_service,
        "_get_material_inventory",
        synchronized_material_read,
    )

    def approve(order_id: int):
        db = SessionLocal()
        try:
            return order_service.approve_order(db, order_id, current_user)
        finally:
            db.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(approve, [order["id"] for order in orders]))

    approved_orders = [order for order, error in results if order is not None]
    errors = [error for order, error in results if order is None]
    assert len(approved_orders) == 1
    assert errors == ["insufficient_quantity"]

    db = SessionLocal()
    try:
        inventory = db.execute(
            text(
                """
                SELECT quantity_available, quantity_reserved
                FROM materials
                WHERE id = :material_id
                """
            ),
            {"material_id": material["id"]},
        ).mappings().one()
        order_rows = db.execute(
            text(
                """
                SELECT status, reserved_quantity
                FROM orders
                WHERE id IN (:first_order_id, :second_order_id)
                """
            ),
            {
                "first_order_id": orders[0]["id"],
                "second_order_id": orders[1]["id"],
            },
        ).mappings().all()
    finally:
        db.close()

    assert inventory["quantity_available"] == 5
    assert inventory["quantity_reserved"] == 3
    assert inventory["quantity_reserved"] <= inventory["quantity_available"]
    assert sorted(row["status"] for row in order_rows) == ["approved", "submitted"]
    assert sum(row["reserved_quantity"] for row in order_rows) == 3


def test_concurrent_fulfillment_and_cancellation_apply_reservation_once(
    monkeypatch,
) -> None:
    client = TestClient(app)

    username = "concurrent_transition_admin"
    email = "concurrent_transition_admin@example.com"
    password = "password123"
    material_code = "TEST-CONCURRENT-TRANSITION-001"

    clean_up_order_workflow_test_data(username, email, material_code)
    create_test_admin(username, email, password)
    headers = login_test_user(client, username, password)
    current_user = UserRead(**client.get("/users/me", headers=headers).json())
    material = create_test_material(
        client,
        headers,
        material_code,
        "Concurrent Transition Test Material",
        5,
    )
    order = create_test_order(
        client,
        headers,
        material["id"],
        requested_quantity=3,
    )
    approve_response = client.post(f"/orders/{order['id']}/approve", headers=headers)
    assert approve_response.status_code == 200

    unlocked_read_barrier = Barrier(2)
    original_get_order_row = order_service._get_order_row

    def synchronized_order_read(db, order_id, *, for_update=False):
        row = original_get_order_row(db, order_id, for_update=for_update)
        if not for_update and row is not None and row["status"] == "approved":
            unlocked_read_barrier.wait(timeout=5)
        return row

    monkeypatch.setattr(order_service, "_get_order_row", synchronized_order_read)

    def transition(operation: str):
        db = SessionLocal()
        try:
            if operation == "fulfill":
                return order_service.fulfill_order(db, order["id"], current_user)
            return order_service.cancel_order(db, order["id"], current_user)
        finally:
            db.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(transition, ["fulfill", "cancel"]))

    successful_orders = [result for result, error in results if result is not None]
    errors = [error for result, error in results if result is None]
    assert len(successful_orders) == 1
    assert errors == ["invalid_status"]

    db = SessionLocal()
    try:
        inventory = db.execute(
            text(
                """
                SELECT quantity_available, quantity_reserved
                FROM materials
                WHERE id = :material_id
                """
            ),
            {"material_id": material["id"]},
        ).mappings().one()
        final_order = db.execute(
            text("SELECT status FROM orders WHERE id = :order_id"),
            {"order_id": order["id"]},
        ).mappings().one()
    finally:
        db.close()

    assert inventory["quantity_reserved"] == 0
    assert inventory["quantity_available"] in {2, 5}
    assert final_order["status"] in {"fulfilled", "canceled"}
    if final_order["status"] == "fulfilled":
        assert inventory["quantity_available"] == 2
    else:
        assert inventory["quantity_available"] == 5


def test_adjustment_and_check_out_preserve_existing_reservations() -> None:
    client = TestClient(app)

    username = "reserved_inventory_admin"
    email = "reserved_inventory_admin@example.com"
    password = "password123"
    material_code = "TEST-RESERVED-INVENTORY-001"

    clean_up_order_workflow_test_data(username, email, material_code)
    create_test_admin(username, email, password)
    headers = login_test_user(client, username, password)
    material = create_test_material(
        client,
        headers,
        material_code,
        "Reserved Inventory Test Material",
        10,
    )
    order = create_test_order(
        client,
        headers,
        material["id"],
        requested_quantity=4,
    )
    approve_response = client.post(f"/orders/{order['id']}/approve", headers=headers)
    assert approve_response.status_code == 200

    invalid_adjustment = client.post(
        f"/materials/{material['id']}/adjust-quantity",
        json={"quantity_available": 3, "reason": "Must preserve reservations"},
        headers=headers,
    )
    invalid_check_out = client.post(
        f"/materials/{material['id']}/check-out",
        json={"quantity": 7, "reason": "Must preserve reservations"},
        headers=headers,
    )
    valid_check_out = client.post(
        f"/materials/{material['id']}/check-out",
        json={"quantity": 6, "reason": "Leave exactly the reserved stock"},
        headers=headers,
    )

    assert invalid_adjustment.status_code == 409
    assert invalid_check_out.status_code == 409
    assert valid_check_out.status_code == 200
    assert valid_check_out.json()["quantity_available"] == 4
    assert valid_check_out.json()["quantity_reserved"] == 4


def test_material_with_reserved_stock_cannot_be_archived() -> None:
    client = TestClient(app)

    username = "reserved_material_archive_admin"
    email = "reserved_material_archive_admin@example.com"
    password = "password123"
    material_code = "TEST-RESERVED-MATERIAL-ARCHIVE-001"

    clean_up_order_workflow_test_data(username, email, material_code)
    create_test_admin(username, email, password)
    headers = login_test_user(client, username, password)
    material = create_test_material(
        client,
        headers,
        material_code,
        "Reserved Material Archive Test",
        10,
    )
    order = create_test_order(
        client,
        headers,
        material["id"],
        requested_quantity=3,
    )
    approve_response = client.post(
        f"/orders/{order['id']}/approve",
        headers=headers,
    )
    assert approve_response.status_code == 200

    archive_response = client.post(
        f"/materials/{material['id']}/archive",
        params={"reason": "Attempted archival with an active reservation"},
        headers=headers,
    )

    assert_api_error(
        archive_response,
        status_code=409,
        code="MATERIAL_HAS_ACTIVE_RESERVATION",
        message=(
            "Material with an approved order or reserved stock cannot be archived; "
            "fulfill or cancel the order first"
        ),
    )
    material_after = client.get(
        f"/materials/{material['id']}",
        headers=headers,
    ).json()
    assert material_after["is_archived"] is False
    assert material_after["quantity_reserved"] == 3

    cancel_response = client.post(
        f"/orders/{order['id']}/cancel",
        headers=headers,
    )
    assert cancel_response.status_code == 200
    archive_after_cancel_response = client.post(
        f"/materials/{material['id']}/archive",
        params={"reason": "Reservation released"},
        headers=headers,
    )
    assert archive_after_cancel_response.status_code == 200


def test_legacy_archived_material_blocks_fulfillment_but_allows_cancellation() -> None:
    client = TestClient(app)

    username = "legacy_archived_order_admin"
    email = "legacy_archived_order_admin@example.com"
    password = "password123"
    material_code = "TEST-LEGACY-ARCHIVED-ORDER-001"

    clean_up_order_workflow_test_data(username, email, material_code)
    create_test_admin(username, email, password)
    headers = login_test_user(client, username, password)
    material = create_test_material(
        client,
        headers,
        material_code,
        "Legacy Archived Order Material",
        5,
    )
    order = create_test_order(client, headers, material["id"], 2)
    assert client.post(
        f"/orders/{order['id']}/approve",
        headers=headers,
    ).status_code == 200

    db = SessionLocal()
    try:
        db.execute(
            text(
                """
                UPDATE materials
                SET
                    is_archived = TRUE,
                    archived_at = CURRENT_TIMESTAMP,
                    archive_reason = 'Legacy inconsistent state'
                WHERE id = :material_id
                """
            ),
            {"material_id": material["id"]},
        )
        db.commit()
    finally:
        db.close()

    fulfill_response = client.post(
        f"/orders/{order['id']}/fulfill",
        headers=headers,
    )
    cancel_response = client.post(
        f"/orders/{order['id']}/cancel",
        headers=headers,
    )

    assert_api_error(
        fulfill_response,
        status_code=409,
        code="MATERIAL_ARCHIVED",
        message="Archived material cannot be ordered",
    )
    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == "canceled"
    material_after = client.get(
        f"/materials/{material['id']}",
        headers=headers,
    ).json()
    assert material_after["is_archived"] is True
    assert material_after["quantity_reserved"] == 0
    audit_operations = {
        item["operation_type"]
        for item in page_items(
            client.get(
                "/audit-logs",
                params={"material_id": material["id"]},
                headers=headers,
            )
        )
    }
    assert "order_reservation_released" in audit_operations


def test_material_archive_and_restore_are_audited_and_clear_metadata() -> None:
    client = TestClient(app)

    username = "material_archive_restore_admin"
    email = "material_archive_restore_admin@example.com"
    password = "password123"
    material_code = "TEST-MATERIAL-ARCHIVE-RESTORE-001"

    clean_up_order_workflow_test_data(username, email, material_code)
    create_test_admin(username, email, password)
    headers = login_test_user(client, username, password)
    material = create_test_material(
        client,
        headers,
        material_code,
        "Material Archive Restore Test",
        8,
    )

    archive_response = client.post(
        f"/materials/{material['id']}/archive",
        params={"reason": "Retired from the active catalogue"},
        headers=headers,
    )
    assert archive_response.status_code == 200

    archived_material = client.get(
        f"/materials/{material['id']}",
        headers=headers,
    ).json()
    assert archived_material["is_archived"] is True
    assert archived_material["archived_at"] is not None
    assert archived_material["archived_by_user_id"] is not None
    assert archived_material["archive_reason"] == "Retired from the active catalogue"

    restore_response = client.post(
        f"/materials/{material['id']}/restore",
        headers=headers,
    )
    assert restore_response.status_code == 200

    restored_material = client.get(
        f"/materials/{material['id']}",
        headers=headers,
    ).json()
    assert restored_material["is_archived"] is False
    assert restored_material["archived_at"] is None
    assert restored_material["archived_by_user_id"] is None
    assert restored_material["archive_reason"] is None

    audit_response = client.get(
        "/audit-logs",
        params={"material_id": material["id"]},
        headers=headers,
    )
    logs_by_operation = {
        item["operation_type"]: item for item in page_items(audit_response)
    }
    assert logs_by_operation["archive_material"]["before_value"] == "active"
    assert logs_by_operation["archive_material"]["after_value"] == "archived"
    assert logs_by_operation["restore_material"]["before_value"] == "archived"
    assert logs_by_operation["restore_material"]["after_value"] == "active"
    assert "Retired from the active catalogue" in logs_by_operation["restore_material"][
        "reason"
    ]


def test_archive_order_hides_it_from_default_request_list() -> None:
    client = TestClient(app)

    username = "archive_order_admin"
    email = "archive_order_admin@example.com"
    password = "password123"
    material_code = "TEST-ARCHIVE-ORDER-001"

    clean_up_order_workflow_test_data(username, email, material_code)
    create_test_admin(username, email, password)

    headers = login_test_user(client, username, password)
    material = create_test_material(
        client,
        headers,
        material_code,
        "Archive Order Test Material",
        10,
    )
    order = create_test_order(
        client,
        headers,
        material["id"],
        request_notes="Archive order test",
    )

    reject_response = client.post(
        f"/orders/{order['id']}/reject",
        headers=headers,
    )
    assert reject_response.status_code == 200

    archive_response = client.post(
        f"/orders/{order['id']}/archive",
        json={"reason": "No longer needed in active queue"},
        headers=headers,
    )

    assert archive_response.status_code == 200
    archived_order = archive_response.json()
    assert archived_order["is_archived"] is True
    assert archived_order["archive_reason"] == "No longer needed in active queue"

    default_list_response = client.get("/orders", headers=headers)
    assert default_list_response.status_code == 200
    default_order_ids = {entry["id"] for entry in page_items(default_list_response)}
    assert order["id"] not in default_order_ids

    archived_list_response = client.get(
        "/orders",
        params={"include_archived": True},
        headers=headers,
    )
    assert archived_list_response.status_code == 200
    archived_order_ids = {entry["id"] for entry in page_items(archived_list_response)}
    assert order["id"] in archived_order_ids

    archived_at = archived_order["archived_at"]
    duplicate_archive = client.post(
        f"/orders/{order['id']}/archive",
        json={"reason": "Overwrite prior archive metadata"},
        headers=headers,
    )
    assert_api_error(
        duplicate_archive,
        status_code=409,
        code="ORDER_ALREADY_ARCHIVED",
    )
    order_after = client.get(f"/orders/{order['id']}", headers=headers).json()
    assert order_after["archived_at"] == archived_at
    assert order_after["archive_reason"] == "No longer needed in active queue"
    audit_entries = page_items(client.get(
        "/audit-logs",
        params={"material_id": material["id"], "operation_type": "order_archived"},
        headers=headers,
    ))
    assert len(audit_entries) == 1


def test_order_archive_requires_nonblank_reason() -> None:
    client = TestClient(app)
    create_test_admin("archive_reason_admin", "archive_reason_admin@example.com", "password123")
    headers = login_test_user(client, "archive_reason_admin", "password123")
    material = create_test_material(
        client, headers, "TEST-ARCHIVE-REASON-001", "Archive Reason Material", 2,
    )
    order = create_test_order(client, headers, material["id"], 1)
    assert client.post(f"/orders/{order['id']}/reject", headers=headers).status_code == 200

    response = client.post(
        f"/orders/{order['id']}/archive",
        json={"reason": "   "},
        headers=headers,
    )
    assert_api_error(response, status_code=422, code="VALIDATION_ERROR")


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
    filtered_order_ids = {order["id"] for order in page_items(filtered_response)}
    assert submitted_order["id"] in filtered_order_ids
    assert approved_order["id"] not in filtered_order_ids


def test_orders_include_requester_summary_and_filter_active_statuses() -> None:
    client = TestClient(app)

    admin_username = "order_active_filter_admin"
    admin_email = "order_active_filter_admin@example.com"
    requester_username = "order_active_filter_requester"
    requester_email = "order_active_filter_requester@example.com"
    password = "password123"
    material_code = "TEST-ORDER-ACTIVE-FILTER-001"

    clean_up_order_workflow_test_data(admin_username, admin_email, material_code)
    clean_up_order_workflow_test_data(requester_username, requester_email, material_code)
    create_test_admin(admin_username, admin_email, password)
    requester = create_test_viewer(client, requester_username, requester_email, password)
    admin_headers = login_test_user(client, admin_username, password)
    requester_headers = login_test_user(client, requester_username, password)
    material = create_test_material(
        client,
        admin_headers,
        material_code,
        "Order Active Filter Material",
        10,
    )

    submitted_order = create_test_order(client, requester_headers, material["id"])
    approved_order = create_test_order(client, requester_headers, material["id"])
    canceled_order = create_test_order(client, requester_headers, material["id"])

    assert client.post(f"/orders/{approved_order['id']}/approve", headers=admin_headers).status_code == 200
    assert client.post(f"/orders/{canceled_order['id']}/cancel", headers=requester_headers).status_code == 200

    active_response = client.get(
        "/orders",
        params={"requested_by_user_id": requester["id"], "active_only": True},
        headers=admin_headers,
    )

    assert active_response.status_code == 200
    active_orders = page_items(active_response)
    assert {order["id"] for order in active_orders} == {submitted_order["id"], approved_order["id"]}
    assert all(order["requested_by_username"] == requester_username for order in active_orders)

    detail_response = client.get(f"/orders/{submitted_order['id']}", headers=admin_headers)

    assert detail_response.status_code == 200
    assert detail_response.json()["requested_by_username"] == requester_username


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
    filtered_order_ids = {order["id"] for order in page_items(filtered_response)}
    assert first_order["id"] in filtered_order_ids
    assert second_order["id"] not in filtered_order_ids


def test_admin_can_filter_orders_by_reviewer() -> None:
    client = TestClient(app)

    username = "order_reviewer_filter_admin"
    email = "order_reviewer_filter_admin@example.com"
    password = "password123"
    reviewed_material_code = "TEST-ORDER-REVIEWER-FILTER-001"
    unreviewed_material_code = "TEST-ORDER-REVIEWER-FILTER-002"

    clean_up_order_workflow_test_data(username, email, reviewed_material_code)
    clean_up_order_workflow_test_data(username, email, unreviewed_material_code)
    create_test_admin(username, email, password)

    headers = login_test_user(client, username, password)
    reviewed_material = create_test_material(
        client,
        headers,
        reviewed_material_code,
        "Order Reviewer Filter Reviewed Material",
        10,
    )
    unreviewed_material = create_test_material(
        client,
        headers,
        unreviewed_material_code,
        "Order Reviewer Filter Unreviewed Material",
        10,
    )
    reviewed_order = create_test_order(
        client,
        headers,
        reviewed_material["id"],
        request_notes="Reviewed order filter test",
    )
    unreviewed_order = create_test_order(
        client,
        headers,
        unreviewed_material["id"],
        request_notes="Unreviewed order filter test",
    )

    approve_response = client.post(
        f"/orders/{reviewed_order['id']}/approve",
        headers=headers,
    )

    assert approve_response.status_code == 200
    reviewed_by_user_id = approve_response.json()["reviewed_by_user_id"]

    filtered_response = client.get(
        "/orders",
        params={"reviewed_by_user_id": reviewed_by_user_id},
        headers=headers,
    )

    assert filtered_response.status_code == 200
    filtered_order_ids = {order["id"] for order in page_items(filtered_response)}
    assert reviewed_order["id"] in filtered_order_ids
    assert unreviewed_order["id"] not in filtered_order_ids


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
    filtered_orders = page_items(filtered_response)
    filtered_order_ids = {order["id"] for order in filtered_orders}
    assert requester_order["id"] in filtered_order_ids
    assert other_order["id"] not in filtered_order_ids
    assert all(
        order["requested_by_user_id"] == requester["id"]
        for order in filtered_orders
    )


def test_material_search_supports_keyword_source_and_low_stock_filters() -> None:
    client = TestClient(app)

    username = "material_filter_admin"
    email = "material_filter_admin@example.com"
    password = "password123"
    low_stock_material_code = "TEST-MATERIAL-FILTER-LOW-001"
    enough_stock_material_code = "TEST-MATERIAL-FILTER-ENOUGH-001"

    clean_up_order_workflow_test_data(username, email, low_stock_material_code)
    clean_up_order_workflow_test_data(username, email, enough_stock_material_code)
    create_test_admin(username, email, password)

    headers = login_test_user(client, username, password)
    low_stock_material = create_test_material(
        client,
        headers,
        low_stock_material_code,
        "Special Buffer Filter Material",
        1,
    )
    enough_stock_material = create_test_material(
        client,
        headers,
        enough_stock_material_code,
        "Regular Solvent Filter Material",
        10,
    )

    keyword_response = client.get(
        "/materials/search",
        params={"keyword": "Special Buffer"},
        headers=headers,
    )
    source_response = client.get(
        "/materials/search",
        params={"source": "test"},
        headers=headers,
    )
    low_stock_response = client.get(
        "/materials/search",
        params={"low_stock": True},
        headers=headers,
    )
    low_stock_availability_response = client.get(
        "/materials/search",
        params={"availability_status": "low_stock"},
        headers=headers,
    )

    assert keyword_response.status_code == 200
    keyword_material_codes = {
        material["material_code"]
        for material in page_items(keyword_response)
    }
    assert low_stock_material["material_code"] in keyword_material_codes
    assert enough_stock_material["material_code"] not in keyword_material_codes

    assert source_response.status_code == 200
    source_material_codes = {
        material["material_code"]
        for material in page_items(source_response)
    }
    assert low_stock_material["material_code"] in source_material_codes
    assert enough_stock_material["material_code"] in source_material_codes

    assert low_stock_response.status_code == 200
    low_stock_material_codes = {
        material["material_code"]
        for material in page_items(low_stock_response)
    }
    assert low_stock_material["material_code"] in low_stock_material_codes
    assert enough_stock_material["material_code"] not in low_stock_material_codes

    assert low_stock_availability_response.status_code == 200
    low_stock_availability_material_codes = {
        material["material_code"]
        for material in page_items(low_stock_availability_response)
    }
    assert low_stock_material["material_code"] in low_stock_availability_material_codes
    assert enough_stock_material["material_code"] not in low_stock_availability_material_codes


def test_list_apis_return_bounded_pagination_metadata() -> None:
    client = TestClient(app)

    username = "pagination_admin"
    email = "pagination_admin@example.com"
    password = "password123"
    first_code = "TEST-PAGINATION-MATERIAL-001"
    second_code = "TEST-PAGINATION-MATERIAL-002"

    clean_up_order_workflow_test_data(username, email, first_code)
    clean_up_order_workflow_test_data(username, email, second_code)
    create_test_admin(username, email, password)
    headers = login_test_user(client, username, password)
    first_material = create_test_material(
        client,
        headers,
        first_code,
        "Pagination Material One",
        5,
    )
    second_material = create_test_material(
        client,
        headers,
        second_code,
        "Pagination Material Two",
        5,
    )
    first_location = create_test_location(client, headers, "Pagination Location One")
    create_test_location(client, headers, "Pagination Location Two")
    first_order = create_test_order(client, headers, first_material["id"], 1)
    create_test_order(client, headers, second_material["id"], 1)
    assert client.post(
        f"/orders/{first_order['id']}/approve",
        headers=headers,
    ).status_code == 200

    endpoints = (
        ("/materials", {}),
        ("/orders", {}),
        ("/locations", {}),
        ("/audit-logs", {}),
    )
    for endpoint, params in endpoints:
        response = client.get(
            endpoint,
            params={**params, "page": 2, "size": 1},
            headers=headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["page"] == 2
        assert body["size"] == 1
        assert body["total"] >= 1
        assert body["pages"] == body["total"]
        assert len(body["items"]) <= 1

    for endpoint, _ in endpoints:
        assert client.get(
            endpoint,
            params={"size": 101},
            headers=headers,
        ).status_code == 422
    location_page = client.get(
        "/locations",
        params={"page": 1, "size": 1},
        headers=headers,
    ).json()
    assert location_page["items"][0]["id"] == first_location["id"]


def test_material_availability_status_is_derived_from_current_quantity() -> None:
    client = TestClient(app)

    username = "material_availability_admin"
    email = "material_availability_admin@example.com"
    password = "password123"
    unavailable_code = "TEST-MATERIAL-UNAVAILABLE-001"
    low_stock_code = "TEST-MATERIAL-LOW-STOCK-001"
    available_code = "TEST-MATERIAL-AVAILABLE-001"

    for material_code in (unavailable_code, low_stock_code, available_code):
        clean_up_order_workflow_test_data(username, email, material_code)
    create_test_admin(username, email, password)
    headers = login_test_user(client, username, password)

    unavailable_material = create_test_material(
        client,
        headers,
        unavailable_code,
        "Unavailable Material",
        0,
    )
    low_stock_material = create_test_material(
        client,
        headers,
        low_stock_code,
        "Low Stock Material",
        1,
    )
    available_material = create_test_material(
        client,
        headers,
        available_code,
        "Available Material",
        5,
    )

    assert unavailable_material["availability_status"] == "unavailable"
    assert low_stock_material["availability_status"] == "low_stock"
    assert available_material["availability_status"] == "available"

    low_after_check_out = client.post(
        f"/materials/{available_material['id']}/check-out",
        json={"quantity": 4, "reason": "Reduce to the replenishment threshold"},
        headers=headers,
    )
    unavailable_after_check_out = client.post(
        f"/materials/{available_material['id']}/check-out",
        json={"quantity": 1, "reason": "Consume the remaining stock"},
        headers=headers,
    )
    available_after_check_in = client.post(
        f"/materials/{available_material['id']}/check-in",
        json={"quantity": 2, "reason": "Replenish above the threshold"},
        headers=headers,
    )

    assert low_after_check_out.status_code == 200
    assert low_after_check_out.json()["availability_status"] == "low_stock"
    assert unavailable_after_check_out.status_code == 200
    assert unavailable_after_check_out.json()["availability_status"] == "unavailable"
    assert available_after_check_in.status_code == 200
    assert available_after_check_in.json()["availability_status"] == "available"

    status_by_code = {}
    for availability_status in ("available", "low_stock", "unavailable"):
        response = client.get(
            "/materials/search",
            params={"availability_status": availability_status},
            headers=headers,
        )
        assert response.status_code == 200
        status_by_code.update(
            {
                item["material_code"]: item["availability_status"]
                for item in page_items(response)
                if item["material_code"]
                in {unavailable_code, low_stock_code, available_code}
            }
        )

    assert status_by_code == {
        unavailable_code: "unavailable",
        low_stock_code: "low_stock",
        available_code: "available",
    }


def test_availability_status_is_not_stored_in_the_materials_table() -> None:
    db = SessionLocal()
    try:
        status_column = db.execute(
            text("SHOW COLUMNS FROM materials LIKE 'availability_status'")
        ).first()
    finally:
        db.close()

    assert status_column is None


def test_fully_reserved_material_is_unavailable_in_reads_and_search() -> None:
    client = TestClient(app)

    username = "fully_reserved_status_admin"
    email = "fully_reserved_status_admin@example.com"
    password = "password123"
    material_code = "TEST-FULLY-RESERVED-STATUS-001"

    clean_up_order_workflow_test_data(username, email, material_code)
    create_test_admin(username, email, password)
    headers = login_test_user(client, username, password)
    material = create_test_material(
        client,
        headers,
        material_code,
        "Fully Reserved Status Material",
        5,
    )
    order = create_test_order(
        client,
        headers,
        material["id"],
        requested_quantity=5,
    )
    assert client.post(
        f"/orders/{order['id']}/approve",
        headers=headers,
    ).status_code == 200

    material_after = client.get(
        f"/materials/{material['id']}",
        headers=headers,
    ).json()
    unavailable_response = client.get(
        "/materials/search",
        params={"availability_status": "unavailable"},
        headers=headers,
    )
    available_response = client.get(
        "/materials/search",
        params={"availability_status": "available"},
        headers=headers,
    )

    assert material_after["quantity_available"] == 5
    assert material_after["quantity_reserved"] == 5
    assert material_after["availability_status"] == "unavailable"
    assert material_code in {
        item["material_code"] for item in page_items(unavailable_response)
    }
    assert material_code not in {
        item["material_code"] for item in page_items(available_response)
    }


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


def test_recent_inventory_activity_report_supports_filters() -> None:
    client = TestClient(app)

    username = "recent_activity_filter_admin"
    email = "recent_activity_filter_admin@example.com"
    password = "password123"
    adjusted_material_code = "TEST-RECENT-ACTIVITY-FILTER-001"
    moved_material_code = "TEST-RECENT-ACTIVITY-FILTER-002"

    clean_up_order_workflow_test_data(username, email, adjusted_material_code)
    clean_up_order_workflow_test_data(username, email, moved_material_code)
    create_test_admin(username, email, password)

    headers = login_test_user(client, username, password)
    adjusted_material = create_test_material(
        client,
        headers,
        adjusted_material_code,
        "Recent Activity Filter Adjusted Material",
        10,
    )
    moved_material = create_test_material(
        client,
        headers,
        moved_material_code,
        "Recent Activity Filter Moved Material",
        10,
    )
    location = create_test_location(
        client,
        headers,
        "Recent Activity Filter Location",
    )

    adjust_response = client.post(
        f"/materials/{adjusted_material['id']}/adjust-quantity",
        json={
            "quantity_available": 7,
            "reason": "recent activity filter adjust test",
        },
        headers=headers,
    )
    move_response = client.post(
        f"/materials/{moved_material['id']}/move",
        json={
            "location_id": location["id"],
            "reason": "recent activity filter move test",
        },
        headers=headers,
    )

    assert adjust_response.status_code == 200
    assert move_response.status_code == 200

    filtered_response = client.get(
        "/reports/recent-inventory-activity",
        params={
            "material_id": adjusted_material["id"],
            "operation_type": "adjust_quantity",
            "limit": 1,
        },
        headers=headers,
    )

    assert filtered_response.status_code == 200
    activities = filtered_response.json()
    assert len(activities) == 1
    assert activities[0]["material_code"] == adjusted_material_code
    assert activities[0]["operation_type"] == "adjust_quantity"


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
