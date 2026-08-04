from fastapi.testclient import TestClient

from src.main import app


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
