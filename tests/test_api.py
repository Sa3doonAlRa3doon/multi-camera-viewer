from fastapi.testclient import TestClient

from app.cameras import CameraManager
from app.config import ConfigStore, new_settings
from app.main import create_app


def authenticated_client(tmp_path):
    store = ConfigStore(tmp_path)
    store.save_settings(new_settings(8080, "0.0.0.0", "admin", "password123"))
    store.save_cameras([])
    client = TestClient(create_app(store, CameraManager()))
    client.__enter__()
    response = client.post("/login", data={"username": "admin", "password": "password123"}, follow_redirects=False)
    assert response.status_code == 303
    csrf = client.get("/api/session").json()["csrf_token"]
    return store, client, {"X-CSRF-Token": csrf}


def test_camera_crud_persists_and_redacts_credentials(tmp_path):
    store, client, headers = authenticated_client(tmp_path)
    try:
        payload = {"name": "Gate", "source_type": "rtsp", "source": "rtsp://camera/live?token=abc", "username": "viewer", "password": "secret-password", "enabled": True}
        created = client.post("/api/cameras", json=payload, headers=headers)
        assert created.status_code == 201
        camera_id = created.json()["id"]
        listing = client.get("/api/cameras").json()[0]
        assert listing["name"] == "Gate"
        assert "abc" not in listing["source"]
        assert "secret-password" not in str(listing)

        update = {**payload, "name": "Updated Gate", "source": "", "username": "", "password": ""}
        assert client.put(f"/api/cameras/{camera_id}", json=update, headers=headers).status_code == 200
        saved = store.load_cameras()[0]
        assert saved["source"] == payload["source"]
        assert saved["password"] == payload["password"]

        assert client.delete(f"/api/cameras/{camera_id}", headers=headers).status_code == 204
        assert store.load_cameras() == []
    finally:
        client.__exit__(None, None, None)


def test_api_requires_authentication_and_csrf(tmp_path):
    store = ConfigStore(tmp_path)
    store.save_settings(new_settings(8080, "0.0.0.0", "admin", "password123"))
    store.save_cameras([])
    with TestClient(create_app(store, CameraManager())) as client:
        assert client.get("/api/cameras").status_code == 401
        client.post("/login", data={"username": "admin", "password": "password123"})
        payload = {"name": "Camera", "source_type": "usb", "source": "0", "enabled": True}
        assert client.post("/api/cameras", json=payload).status_code == 403
