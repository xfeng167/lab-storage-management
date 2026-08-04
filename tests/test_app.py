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
