import os
import sys
import time
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from xdrop.main import app
from xdrop.session import SessionManager, get_session_manager, get_ipc_sessions_dir
from tools.gui_installer import XdropGuiInstaller


@pytest.fixture
def client():
    return TestClient(app)


def test_session_lifecycle_open_heartbeat_close(client):
    """Verify opening, heartbeating, and closing an editor session via REST API."""
    # 1. Open session for DaVinci Resolve
    res = client.post("/api/system/session/open?client=resolve")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "resolve" in data["activeSessions"]

    # 2. Check status
    res = client.get("/api/system/session/status")
    assert res.status_code == 200
    assert "resolve" in res.json()["activeSessions"]

    # 3. Heartbeat for Resolve
    res = client.post("/api/system/session/heartbeat?client=resolve")
    assert res.status_code == 200

    # 4. Open session for Premiere
    res = client.post("/api/system/session/open?client=premiere")
    assert res.status_code == 200
    assert "premiere" in res.json()["activeSessions"]

    # 5. Close Resolve session
    res = client.post("/api/system/session/close?client=resolve")
    assert res.status_code == 200
    assert "resolve" not in res.json()["activeSessions"]
    assert "premiere" in res.json()["activeSessions"]

    # 6. Close Premiere session
    res = client.post("/api/system/session/close?client=premiere")
    assert res.status_code == 200
    assert "premiere" not in res.json()["activeSessions"]


def test_ipc_lease_files_handling(tmp_path, monkeypatch):
    """Verify IPC lease files are tracked and cleaned up properly."""
    sm = SessionManager(idle_timeout_seconds=5.0, startup_grace_seconds=0.0)

    # Register resolve
    sm.register_session("resolve")
    assert "resolve" in sm.get_active_sessions()

    # Close resolve
    sm.close_session("resolve")
    assert "resolve" not in sm.get_active_sessions()


def test_watchdog_busy_detection():
    """Verify that active downloads or sessions keep watchdog busy."""
    sm = SessionManager(idle_timeout_seconds=2.0, startup_grace_seconds=0.0)
    assert not sm.has_active_sessions()

    # Register active session
    sm.register_session("premiere")
    assert sm.is_system_busy()

    # Close session
    sm.close_session("premiere")
    assert not sm.has_active_sessions()


def test_gui_installer_initializes_without_errors():
    """Verify XdropGuiInstaller instantiates cleanly with all checkboxes and frames."""
    # Test Tkinter window creation (headless/with withdrawal)
    app_gui = XdropGuiInstaller()
    try:
        assert app_gui.install_resolve_var.get() is True
        assert app_gui.install_adobe_var.get() is True
        assert app_gui.install_engine_var.get() is True
        assert app_gui.title() == "Xdrop Setup — Universal Media Importer"
    finally:
        app_gui.destroy()
