import sqlite3
import threading
from contextlib import contextmanager
from typing import Generator
from xdrop.config import DB_PATH
from xdrop.database.schema import CREATE_TABLES_SQL
from xdrop.logger import app_logger, errors_logger

_local = threading.local()

def get_raw_connection() -> sqlite3.Connection:
    """Returns a thread-local SQLite connection with WAL enabled."""
    if not hasattr(_local, "connection") or _local.connection is None:
        conn = sqlite3.connect(
            str(DB_PATH),
            timeout=30.0,
            check_same_thread=False
        )
        conn.row_factory = sqlite3.Row
        # Enable WAL (Write-Ahead Logging) mode and foreign keys
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        _local.connection = conn
    return _local.connection

@contextmanager
def get_db_connection() -> Generator[sqlite3.Connection, None, None]:
    conn = get_raw_connection()
    try:
        yield conn
    except Exception as e:
        conn.rollback()
        errors_logger.error(f"Database error: {e}", exc_info=True)
        raise
    else:
        conn.commit()

def init_db() -> None:
    """Initializes SQLite database tables and default records."""
    try:
        app_logger.info(f"Initializing database at: {DB_PATH}")
        with get_db_connection() as conn:
            conn.executescript(CREATE_TABLES_SQL)
            # Safe schema migrations for existing local installations
            try:
                conn.execute("ALTER TABLE downloads ADD COLUMN asset_id TEXT;")
            except Exception:
                pass
            try:
                conn.execute("ALTER TABLE downloads ADD COLUMN premiere_imported INTEGER DEFAULT 0;")
            except Exception:
                pass
            try:
                conn.execute("ALTER TABLE downloads ADD COLUMN premiere_bin TEXT;")
            except Exception:
                pass
            try:
                conn.execute("ALTER TABLE assets ADD COLUMN premiere_imported INTEGER DEFAULT 0;")
            except Exception:
                pass
            try:
                conn.execute("ALTER TABLE downloads ADD COLUMN aftereffects_imported INTEGER DEFAULT 0;")
            except Exception:
                pass
            try:
                conn.execute("ALTER TABLE downloads ADD COLUMN aftereffects_bin TEXT;")
            except Exception:
                pass
            try:
                conn.execute("ALTER TABLE assets ADD COLUMN aftereffects_imported INTEGER DEFAULT 0;")
            except Exception:
                pass
        app_logger.info("Database initialized successfully.")
    except Exception as e:
        errors_logger.critical(f"Failed to initialize database: {e}", exc_info=True)
        raise
