import os
import sys
from pathlib import Path
from typing import Optional

# Ensure apps/desktop-service is at the beginning of sys.path
service_root = Path(__file__).resolve().parent.parent
if str(service_root) not in sys.path:
    sys.path.insert(0, str(service_root))

# Safe stream redirection for background / detached daemon processes (pythonw, wscript, Electron)
def _ensure_safe_stream(stream_name, mode="a"):
    appdata = os.environ.get("LOCALAPPDATA")
    if appdata:
        log_dir = Path(appdata) / "Xdrop"
    else:
        log_dir = Path.home() / ".xdrop"
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    cur = getattr(sys, stream_name, None)
    safe = False
    try:
        if cur is not None and not getattr(cur, "closed", True):
            if "w" in mode or "a" in mode:
                cur.write("")
                cur.flush()
            safe = True
    except Exception:
        safe = False

    if not safe:
        try:
            if "r" in mode:
                setattr(sys, stream_name, open(os.devnull, "r"))
            else:
                setattr(sys, stream_name, open(log_dir / "engine.log", "a", encoding="utf-8"))
        except Exception:
            pass

_ensure_safe_stream("stdin", "r")
_ensure_safe_stream("stdout", "a")
_ensure_safe_stream("stderr", "a")

from xdrop.process_util import install_silent_subprocess_hook
install_silent_subprocess_hook()

import argparse
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn

from xdrop.database import init_db
from xdrop.download_queue import get_queue_manager
from xdrop.session import get_session_manager
from xdrop.api import api_router
from xdrop.logger import app_logger
from xdrop.config import THUMBNAILS_DIR

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app_logger.info("Xdrop service starting up...")
    init_db()
    qm = get_queue_manager()
    await qm.start()
    app_logger.info("Xdrop queue manager started.")
    sm = get_session_manager()
    await sm.start()
    app_logger.info("Xdrop session manager and zero-trace watchdog started.")
    yield
    # Shutdown
    app_logger.info("Xdrop service shutting down...")
    await sm.stop()
    await qm.stop()

app = FastAPI(
    title="Xdrop Desktop Service",
    description="Cross-NLE Universal Social Media & Web Asset Importer for DaVinci Resolve, Premiere Pro & After Effects",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration for local React dev server and NLE panels
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all API endpoints
app.include_router(api_router)

# Serve generated thumbnails statically
if THUMBNAILS_DIR.exists():
    app.mount("/thumbnails", StaticFiles(directory=str(THUMBNAILS_DIR)), name="thumbnails")

@app.get("/api/system/health")
@app.get("/api/health")
async def health_check():
    """Health check endpoint used by NLE launcher scripts and panels."""
    return {
        "status": "ok",
        "healthy": True,
        "service": "Xdrop",
        "version": "1.0.0"
    }

# Serve React frontend build if present
def find_dist_dir() -> Optional[Path]:
    candidates = [
        Path(sys._MEIPASS) / "apps" / "resolve-plugin" / "dist" if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS") else None,
        Path(sys._MEIPASS) / "dist" if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS") else None,
        # LocalAppData installation
        Path(__file__).resolve().parent.parent / "dist",
        # Local monorepo paths
        Path(__file__).resolve().parent.parent.parent / "resolve-plugin" / "dist",
        Path(__file__).resolve().parent.parent.parent.parent / "dist",
        Path(__file__).resolve().parent.parent.parent / "dist",
    ]
    for c in candidates:
        if c and c.is_dir() and (c / "index.html").is_file():
            return c
    return None

DIST_DIR = find_dist_dir()

if DIST_DIR and DIST_DIR.exists():
    if (DIST_DIR / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=str(DIST_DIR / "assets")), name="static_assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = DIST_DIR / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(DIST_DIR / "index.html")

def run_service(host: str = "127.0.0.1", port: int = 8484):
    """Starts the FastAPI service with Uvicorn."""
    config = uvicorn.Config(app=app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)
    server.run()

def run_gui(host: str = "127.0.0.1", port: int = 8484):
    """Launches the service alongside a dedicated standalone desktop app window."""
    import threading
    import time
    from xdrop.app_window import launch_app_window

    service_thread = threading.Thread(target=run_service, args=(host, port), daemon=True)
    service_thread.start()

    time.sleep(0.5)
    url = f"http://{host}:{port}"
    launch_app_window(url, title="Xdrop — Media Importer", width=390, height=640, wait=True)

def main():
    parser = argparse.ArgumentParser(description="Xdrop Desktop Service")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind (default 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8484, help="Port to bind (default 8484)")
    parser.add_argument("--gui", action="store_true", help="Launch native companion desktop window")
    parser.add_argument("--background", action="store_true", help="Run headlessly as background daemon")
    parser.add_argument("--no-auto-shutdown", action="store_true", help="Disable automatic zero-trace idle shutdown")
    args = parser.parse_args()

    if args.no_auto_shutdown:
        get_session_manager().enable_auto_shutdown = False

    if args.gui:
        run_gui(args.host, args.port)
    else:
        run_service(args.host, args.port)

if __name__ == "__main__":
    main()
