import os
import sys
from pathlib import Path

# Ensure apps/desktop-service is at the beginning of sys.path
service_root = Path(__file__).resolve().parent.parent
if str(service_root) not in sys.path:
    sys.path.insert(0, str(service_root))

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
    yield
    # Shutdown
    app_logger.info("Xdrop service shutting down...")
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

@app.get("/api/health")
async def health_check():
    """Health check endpoint used by NLE launcher scripts and panels."""
    return {
        "status": "healthy",
        "service": "Xdrop",
        "version": "1.0.0"
    }

# Serve React frontend build if present
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    DIST_DIR = Path(sys._MEIPASS) / "apps" / "resolve-plugin" / "dist"
else:
    DIST_DIR = Path(__file__).resolve().parent.parent.parent / "resolve-plugin" / "dist"

if DIST_DIR.exists():
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
    """Launches the service alongside a pywebview native desktop companion window or falls back to default browser."""
    import threading
    import time
    import webbrowser

    service_thread = threading.Thread(target=run_service, args=(host, port), daemon=True)
    service_thread.start()

    url = f"http://{host}:{port}"
    try:
        import webview
        window = webview.create_window(
            title="Xdrop - Video Asset Importer",
            url=url,
            width=1020,
            height=720,
            min_size=(780, 520),
            background_color="#08090d"
        )
        webview.start()
    except Exception as e:
        app_logger.warning(f"Native desktop window unavailable ({e}). Opening in default browser instead.")
        webbrowser.open(url)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass

def main():
    parser = argparse.ArgumentParser(description="Xdrop Desktop Service")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind (default 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8484, help="Port to bind (default 8484)")
    parser.add_argument("--gui", action="store_true", help="Launch native companion desktop window")
    args = parser.parse_args()

    if args.gui:
        run_gui(args.host, args.port)
    else:
        run_service(args.host, args.port)

if __name__ == "__main__":
    main()
