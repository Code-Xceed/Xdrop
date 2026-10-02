import os
import pytest
from pathlib import Path

@pytest.fixture(autouse=True)
def isolate_test_environment(tmp_path, monkeypatch):
    """Ensures all tests run in an isolated temporary directory, protecting the live user database."""
    test_data_dir = tmp_path / "xdrop_test_data"
    test_data_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("XDROP_DATA_DIR", str(test_data_dir))
    monkeypatch.setenv("RESOLVEFETCH_DATA_DIR", str(test_data_dir))
    
    import xdrop.config as cfg
    monkeypatch.setattr(cfg, "DATA_DIR", test_data_dir)
    monkeypatch.setattr(cfg, "DB_PATH", test_data_dir / "xdrop.db")
    monkeypatch.setattr(cfg, "THUMBNAILS_DIR", test_data_dir / "thumbnails")
    monkeypatch.setattr(cfg, "PROXIES_DIR", test_data_dir / "proxies")
    
    import xdrop.database.connection as conn_mod
    monkeypatch.setattr(conn_mod, "DB_PATH", test_data_dir / "xdrop.db")
    if hasattr(conn_mod._local, "connection"):
        conn_mod._local.connection = None
        
    conn_mod.init_db()
    yield
    if hasattr(conn_mod._local, "connection") and conn_mod._local.connection:
        try:
            conn_mod._local.connection.close()
        except Exception:
            pass
        conn_mod._local.connection = None
