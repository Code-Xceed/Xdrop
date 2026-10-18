"""
Xdrop Session & Lifecycle Watchdog.

Manages active client sessions (DaVinci Resolve, Adobe Premiere Pro, After Effects, Audition)
and provides automated, zero-trace background shutdown when all editors are closed and the queue is idle.
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Set

from xdrop.logger import app_logger


def get_ipc_sessions_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "Xdrop" / "ipc" / "sessions"
    else:
        base = Path.home() / ".xdrop" / "ipc" / "sessions"
    base.mkdir(parents=True, exist_ok=True)
    return base


class SessionManager:
    """Tracks active client sessions and orchestrates zero-trace auto-shutdown."""

    def __init__(
        self,
        idle_timeout_seconds: float = 15.0,
        startup_grace_seconds: float = 30.0,
        enable_auto_shutdown: bool = True,
    ):
        self._active_sessions: Dict[str, float] = {}
        self._idle_timeout: float = idle_timeout_seconds
        self._startup_grace: float = startup_grace_seconds
        self._startup_time: float = time.time()
        self._idle_start: Optional[float] = None
        self._running: bool = False
        self._watchdog_task: Optional[asyncio.Task] = None
        self.enable_auto_shutdown: bool = enable_auto_shutdown

    def register_session(self, client_id: str) -> None:
        """Registers or refreshes an active client session."""
        now = time.time()
        self._active_sessions[client_id] = now
        self._idle_start = None
        self._touch_lease_file(client_id, now)
        app_logger.info(f"Client session registered: {client_id}")

    def heartbeat(self, client_id: str) -> None:
        """Heartbeat to keep a session alive."""
        now = time.time()
        self._active_sessions[client_id] = now
        self._idle_start = None
        self._touch_lease_file(client_id, now)

    def close_session(self, client_id: str) -> None:
        """Explicitly closes a client session when the extension window closes."""
        self._active_sessions.pop(client_id, None)
        self._remove_lease_file(client_id)
        app_logger.info(f"Client session closed: {client_id}")

    def _touch_lease_file(self, client_id: str, ts: float) -> None:
        try:
            s_dir = get_ipc_sessions_dir()
            lease_file = s_dir / f"{client_id}.lease"
            lease_file.write_text(str(int(ts)), encoding="utf-8")
        except Exception:
            pass

    def _remove_lease_file(self, client_id: str) -> None:
        try:
            s_dir = get_ipc_sessions_dir()
            lease_file = s_dir / f"{client_id}.lease"
            if lease_file.is_file():
                lease_file.unlink(missing_ok=True)
        except Exception:
            pass

    def _scan_ipc_leases(self) -> Set[str]:
        """Scans the IPC sessions directory for active leases updated within the last 20 seconds."""
        active: Set[str] = set()
        try:
            s_dir = get_ipc_sessions_dir()
            now = time.time()
            for f in s_dir.glob("*.lease"):
                try:
                    mtime = f.stat().st_mtime
                    if now - mtime <= 20.0:
                        active.add(f.stem)
                    else:
                        f.unlink(missing_ok=True)
                except Exception:
                    pass
        except Exception:
            pass
        return active

    def get_active_sessions(self) -> List[str]:
        """Returns all currently active client session names."""
        now = time.time()
        expired = [cid for cid, ts in self._active_sessions.items() if now - ts > 20.0]
        for exp in expired:
            self._active_sessions.pop(exp, None)

        sessions = set(self._active_sessions.keys())
        sessions.update(self._scan_ipc_leases())

        try:
            from xdrop.api.websocket import manager as ws_manager
            if ws_manager.active_connections:
                sessions.add("websocket_panel")
        except Exception:
            pass

        return sorted(list(sessions))

    def has_active_sessions(self) -> bool:
        return len(self.get_active_sessions()) > 0

    def is_system_busy(self) -> bool:
        """Returns True if there are active client sessions or active downloads in queue."""
        if self.has_active_sessions():
            return True
        try:
            from xdrop.download_queue import get_queue_manager
            qm = get_queue_manager()
            if qm and qm.is_busy():
                return True
        except Exception:
            pass
        return False

    def cleanup_all_ipc_traces(self) -> None:
        """Purges heartbeat, temporary files, and IPC directories for zero-trace exit."""
        if sys.platform == "win32":
            ipc_dir = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "Xdrop" / "ipc"
        else:
            ipc_dir = Path.home() / ".xdrop" / "ipc"

        try:
            if ipc_dir.is_dir():
                hb = ipc_dir / "heartbeat.json"
                if hb.is_file():
                    hb.unlink(missing_ok=True)
                hb_tmp = ipc_dir / "heartbeat.tmp"
                if hb_tmp.is_file():
                    hb_tmp.unlink(missing_ok=True)
                sessions_dir = ipc_dir / "sessions"
                if sessions_dir.is_dir():
                    for s in sessions_dir.glob("*.lease"):
                        s.unlink(missing_ok=True)
        except Exception as e:
            app_logger.debug(f"IPC cleanup notice: {e}")

    def shutdown_engine(self) -> None:
        """Performs immediate clean zero-trace shutdown of the backend engine."""
        app_logger.info("Executing zero-trace engine shutdown...")
        self.cleanup_all_ipc_traces()
        try:
            from xdrop.download_queue import get_queue_manager
            qm = get_queue_manager()
            if qm:
                asyncio.create_task(qm.stop())
        except Exception:
            pass
        os._exit(0)

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._watchdog_task = asyncio.create_task(self._watchdog_loop())
        app_logger.info("SessionManager and Auto-Shutdown Watchdog started.")

    async def stop(self) -> None:
        self._running = False
        if self._watchdog_task:
            self._watchdog_task.cancel()
            self._watchdog_task = None

    async def _watchdog_loop(self) -> None:
        """Periodically evaluates session activity and terminates when idle."""
        while self._running:
            try:
                await asyncio.sleep(2.0)

                if time.time() - self._startup_time < self._startup_grace:
                    continue

                if not self.enable_auto_shutdown:
                    continue

                if self.is_system_busy():
                    self._idle_start = None
                else:
                    if self._idle_start is None:
                        self._idle_start = time.time()
                    elif time.time() - self._idle_start >= self._idle_timeout:
                        app_logger.info(
                            f"No active editor extension sessions or downloads detected for {self._idle_timeout}s. "
                            "Shutting down zero-trace background engine."
                        )
                        self.shutdown_engine()
                        break
            except asyncio.CancelledError:
                break
            except Exception as e:
                app_logger.error(f"Watchdog error: {e}")


_global_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    global _global_session_manager
    if _global_session_manager is None:
        _global_session_manager = SessionManager()
    return _global_session_manager
