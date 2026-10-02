import pytest
import sys
import os
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "apps", "desktop-service")))

import xdrop.config as config
from xdrop.database import init_db
from xdrop.main import app

@pytest.fixture(autouse=True)
def setup_api_test(tmp_path, monkeypatch):
    test_db = tmp_path / "api_test.db"
    monkeypatch.setattr(config, "DB_PATH", test_db)
    init_db()

def test_api_health():
    client = TestClient(app)
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["service"] == "Xdrop"

def test_api_resolve_status():
    client = TestClient(app)
    resp = client.get("/api/resolve/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "isAvailable" in data
    assert "lastChecked" in data

def test_api_settings():
    client = TestClient(app)
    resp = client.get("/api/settings")
    assert resp.status_code == 200
    data = resp.json()
    assert "download_dir" in data
    assert "concurrent_downloads" in data

    # Update settings
    data["concurrent_downloads"] = 5
    put_resp = client.put("/api/settings", json=data)
    assert put_resp.status_code == 200
    assert put_resp.json()["settings"]["concurrent_downloads"] == 5

def test_api_batch_analyze():
    client = TestClient(app)
    resp = client.post("/api/analyze/batch", json={
        "urls": [
            "https://www.youtube.com/watch?v=123",
            "https://www.instagram.com/reel/abc/",
            "https://cdn.example.com/file.mp4"
        ]
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert data["detected"][0]["platform"] == "youtube"
    assert data["detected"][1]["platform"] == "instagram"
    assert data["detected"][2]["platform"] == "direct"

def test_api_thumbnail_proxy_invalid_url():
    client = TestClient(app)
    resp = client.get("/api/analyze/thumbnail-proxy?url=ftp://bad.com/img.jpg")
    assert resp.status_code == 400

def test_api_create_download_with_auto_import_options():
    client = TestClient(app)
    payload = {
        "source_url": "https://example.com/sample.mp4",
        "asset_id": "direct_original",
        "format": "mp4",
        "quality_label": "Original File",
        "media_type": "video",
        "title": "Sample Auto Import Asset",
        "target_editor": "premiere",
        "auto_import_to_premiere": True,
        "target_premiere_bin": "Xdrop",
    }
    resp = client.post("/api/downloads", json=payload)
    assert resp.status_code == 201
    job = resp.json()
    assert job["target_editor"] == "premiere"
    assert job["auto_import"] == 1

