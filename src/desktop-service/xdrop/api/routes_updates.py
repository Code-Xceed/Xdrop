"""
API Routes for Xdrop Auto-Updater.
"""

from __future__ import annotations

import asyncio
from typing import Optional
from fastapi import APIRouter, BackgroundTasks, Query
from pydantic import BaseModel

from xdrop.updater import get_update_manager

router = APIRouter(prefix="/api/system/update", tags=["System / Updates"])


class InstallUpdateRequest(BaseModel):
    downloadUrl: Optional[str] = None


class DismissUpdateRequest(BaseModel):
    version: str


@router.get("/check")
async def check_updates(force: bool = Query(default=False)):
    """Checks GitHub for newer releases or version.json updates."""
    mgr = get_update_manager()
    info = await mgr.check_for_updates(force=force)
    return info.to_dict()


@router.get("/status")
async def get_update_status():
    """Retrieves current update progress, stage, and messages."""
    mgr = get_update_manager()
    return mgr.current_status


@router.post("/install")
async def install_update(
    payload: InstallUpdateRequest = InstallUpdateRequest(),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """Triggers silent download and deployment of the latest update."""
    mgr = get_update_manager()

    # Launch installation as an asyncio background task
    asyncio.create_task(mgr.install_update(download_url=payload.downloadUrl))
    return {"status": "started", "message": "Update process launched"}


@router.post("/dismiss")
async def dismiss_update(payload: DismissUpdateRequest):
    """Dismisses update notification for a specific version."""
    mgr = get_update_manager()
    mgr.dismiss_version(payload.version)
    return {"success": True, "dismissedVersion": payload.version}
