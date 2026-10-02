import pytest
import sys
import os
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "apps", "desktop-service")))

import xdrop.config as config
from xdrop.database import init_db
from xdrop.main import app

@pytest.fixture(autouse=True)
def setup_ae_test(tmp_path, monkeypatch):
    test_db = tmp_path / "ae_test.db"
    monkeypatch.setattr(config, "DB_PATH", test_db)
    init_db()

def test_aftereffects_status():
    client = TestClient(app)
    resp = client.get("/api/aftereffects/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "isAvailable" in data
    assert data["productName"] == "Adobe After Effects"

def test_aftereffects_heartbeat():
    client = TestClient(app)
    resp = client.post("/api/aftereffects/heartbeat", json={
        "isAvailable": True,
        "currentProject": "MotionGraphicsComp.aep",
        "activeSequence": "MainTitle_4K",
        "projectPath": "C:/Projects/MotionGraphicsComp.aep"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True

    from xdrop.aftereffects import get_aftereffects_bridge
    bridge = get_aftereffects_bridge()
    assert bridge._last_heartbeat["currentProject"] == "MotionGraphicsComp.aep"
    assert bridge._last_heartbeat["activeSequence"] == "MainTitle_4K"

def test_editors_status():
    client = TestClient(app)
    resp = client.get("/api/editors/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "resolve" in data
    assert "premiere" in data
    assert "aftereffects" in data
    assert "activeEditor" in data
    assert "isAvailable" in data["aftereffects"]
    assert data["aftereffects"]["productName"] == "Adobe After Effects"

def test_aftereffects_import_broadcast(monkeypatch, tmp_path):
    client = TestClient(app)
    test_media = tmp_path / "sample.mp4"
    test_media.write_bytes(b"dummy mp4 content")

    resp = client.post("/api/aftereffects/import", json={
        "file_paths": [str(test_media)],
        "target_bin": "Xdrop"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["targetBin"] == "Xdrop"
    assert len(data["filePaths"]) == 1

def test_aftereffects_settings():
    client = TestClient(app)
    resp = client.get("/api/settings")
    assert resp.status_code == 200
    data = resp.json()
    assert "auto_import_to_aftereffects" in data
    assert "target_aftereffects_bin" in data

    # Update settings
    data["auto_import_to_aftereffects"] = True
    data["target_aftereffects_bin"] = "AE_Footage"
    put_resp = client.put("/api/settings", json=data)
    assert put_resp.status_code == 200
    updated = put_resp.json()["settings"]
    assert updated["auto_import_to_aftereffects"] is True
    assert updated["target_aftereffects_bin"] == "AE_Footage"

def test_install_aftereffects_extension():
    client = TestClient(app)
    resp = client.post("/api/settings/install-aftereffects-extension")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "message" in data
