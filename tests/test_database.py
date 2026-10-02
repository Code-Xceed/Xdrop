import pytest
import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "apps", "desktop-service")))

import xdrop.config as config
from xdrop.database import (
    init_db,
    insert_download,
    get_download_by_id,
    update_download_progress,
    update_download_status,
    delete_download,
    insert_library_item,
    get_library_items,
    delete_library_item,
    save_settings_to_db,
    get_settings_from_db,
)

@pytest.fixture(autouse=True)
def setup_test_db(tmp_path, monkeypatch):
    test_db = tmp_path / "test_xdrop.db"
    monkeypatch.setattr(config, "DB_PATH", test_db)
    init_db()

def test_download_crud():
    job_data = {
        "id": "dl_test_1",
        "source_url": "https://example.com/video.mp4",
        "platform": "direct",
        "title": "Test Clip",
        "author": "Creator",
        "media_type": "video",
        "format": "mp4",
        "quality_label": "1080p",
        "status": "queued",
    }
    insert_download(job_data)
    
    retrieved = get_download_by_id("dl_test_1")
    assert retrieved is not None
    assert retrieved["title"] == "Test Clip"
    assert retrieved["status"] == "queued"

    update_download_progress("dl_test_1", "downloading", 50.0, 5000000, 10000000, "2.5 MB/s", "00:02")
    updated = get_download_by_id("dl_test_1")
    assert updated["progress"] == 50.0
    assert updated["speed"] == "2.5 MB/s"
    assert updated["status"] == "downloading"

    update_download_status("dl_test_1", "completed")
    completed = get_download_by_id("dl_test_1")
    assert completed["status"] == "completed"
    assert completed["completed_at"] is not None

    delete_download("dl_test_1")
    assert get_download_by_id("dl_test_1") is None

def test_library_crud():
    item = {
        "id": "ast_test_1",
        "download_id": None,
        "source_url": "https://example.com/sound.wav",
        "platform": "direct",
        "title": "Ambient Sound",
        "author": "Audio Guy",
        "media_type": "audio",
        "format": "wav",
        "resolution": None,
        "duration": 12.5,
        "file_size_bytes": 1024000,
        "file_path": "C:/Media/Ambient Sound.wav",
        "thumbnail_path": None,
        "resolve_imported": False,
    }
    insert_library_item(item)

    items = get_library_items(search="Ambient")
    assert len(items) == 1
    assert items[0]["title"] == "Ambient Sound"

    # Search non-matching
    assert len(get_library_items(search="NonExistent")) == 0

    deleted_path = delete_library_item("ast_test_1")
    assert deleted_path == "C:/Media/Ambient Sound.wav"
    assert len(get_library_items()) == 0

def test_settings_persistence():
    data = {"download_dir": "D:/MyAssets", "concurrent_downloads": 4}
    save_settings_to_db(data)
    loaded = get_settings_from_db()
    assert loaded["download_dir"] == "D:/MyAssets"
    assert loaded["concurrent_downloads"] == 4
