from typing import List, Optional
from fastapi import APIRouter
from pydantic import BaseModel
from xdrop.resolve import get_resolve_bridge

router = APIRouter(prefix="/api/resolve", tags=["DaVinci Resolve"])

class DirectImportRequest(BaseModel):
    file_paths: List[str]
    target_bin: str = "Xdrop"

@router.get("/status")
async def get_resolve_status():
    """Returns the live connection status of DaVinci Resolve and the active project."""
    bridge = get_resolve_bridge()
    return bridge.get_status()

@router.post("/import")
async def direct_import_to_resolve(req: DirectImportRequest):
    """Directly imports specified files into the active Resolve project's Media Pool."""
    bridge = get_resolve_bridge()
    return bridge.import_media(req.file_paths, req.target_bin)
