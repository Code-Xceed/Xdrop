import asyncio
import json
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from xdrop.updater import (
    parse_version,
    compare_versions,
    UpdateInfo,
    UpdateManager,
    get_update_manager,
)
from xdrop.main import app

client = TestClient(app)


def test_parse_version():
    assert parse_version("1.2.0") == (1, 2, 0)
    assert parse_version("v1.2.0") == (1, 2, 0)
    assert parse_version("V2.10.5") == (2, 10, 5)
    assert parse_version("1.3.0-rc1") == (1, 3, 0)
    assert parse_version("") == (0, 0, 0)


def test_compare_versions():
    assert compare_versions("1.2.1", "1.2.0") == 1
    assert compare_versions("1.2.0", "1.2.0") == 0
    assert compare_versions("1.1.9", "1.2.0") == -1
    assert compare_versions("v2.0.0", "1.9.9") == 1
    assert compare_versions("1.2", "1.2.0") == 0
    assert compare_versions("1.2.0.1", "1.2.0") == 1


def test_update_info_dict():
    info = UpdateInfo(
        update_available=True,
        current_version="1.2.0",
        latest_version="1.2.1",
        release_name="v1.2.1 Bug Fixes",
        changelog="Fixed Adobe auto-start",
        download_url="https://github.com/Code-Xceed/Xdrop/archive/refs/tags/v1.2.1.zip",
    )
    d = info.to_dict()
    assert d["updateAvailable"] is True
    assert d["currentVersion"] == "1.2.0"
    assert d["latestVersion"] == "1.2.1"
    assert d["releaseName"] == "v1.2.1 Bug Fixes"
    assert d["isDismissed"] is False


@pytest.mark.anyio
async def test_check_for_updates_mocked():
    mgr = get_update_manager()

    mock_release = {
        "tag_name": "v1.3.0",
        "name": "Xdrop v1.3.0",
        "body": "Major improvements across all editors",
        "published_at": "2026-10-21T00:00:00Z",
        "zipball_url": "https://api.github.com/repos/Code-Xceed/Xdrop/zipball/v1.3.0",
    }

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(mock_release).encode("utf-8")
        mock_urlopen.return_value = mock_resp

        info = await mgr.check_for_updates(force=True)
        assert info.update_available is True
        assert info.latest_version == "1.3.0"
        assert info.release_name == "Xdrop v1.3.0"
        assert "Major improvements" in info.changelog


def test_api_update_endpoints():
    # 1. Check status
    res = client.get("/api/system/update/status")
    assert res.status_code == 200
    data = res.json()
    assert "stage" in data
    assert "percent" in data

    # 2. Dismiss endpoint
    dismiss_res = client.post("/api/system/update/dismiss", json={"version": "1.3.0"})
    assert dismiss_res.status_code == 200
    assert dismiss_res.json()["success"] is True

    # 3. Check endpoint returns json
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "version": "1.2.0",
            "name": "Xdrop v1.2.0",
            "releaseDate": "2026-10-20",
        }).encode("utf-8")
        mock_urlopen.return_value = mock_resp

        check_res = client.get("/api/system/update/check?force=true")
        assert check_res.status_code == 200
        check_data = check_res.json()
        assert "updateAvailable" in check_data
        assert "currentVersion" in check_data
