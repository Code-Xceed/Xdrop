from typing import List, Optional, Dict, Any
from fastapi import APIRouter
from pydantic import BaseModel
from xdrop.premiere import get_premiere_bridge

router = APIRouter(prefix="/api/premiere", tags=["Adobe Premiere Pro"])

class PremiereHeartbeatRequest(BaseModel):
    isAvailable: bool = True
    currentProject: Optional[str] = None
    activeSequence: Optional[str] = None
    projectPath: Optional[str] = None
    error: Optional[str] = None

class PremiereImportRequest(BaseModel):
    file_paths: List[str]
    target_bin: str = "Xdrop"

@router.get("/status")
async def get_premiere_status():
    """Returns availability and project information for Adobe Premiere Pro."""
    bridge = get_premiere_bridge()
    return bridge.get_status()

@router.post("/heartbeat")
async def receive_premiere_heartbeat(req: PremiereHeartbeatRequest):
    """Receives live project updates from Premiere Pro CEP extension."""
    bridge = get_premiere_bridge()
    bridge.record_heartbeat(req.model_dump())
    return {"success": True, "message": "Heartbeat recorded"}

@router.post("/import")
async def direct_import_to_premiere(req: PremiereImportRequest):
    """Triggers import into active Premiere Pro project via CEP bridge."""
    bridge = get_premiere_bridge()
    return await bridge.import_media(req.file_paths, req.target_bin)
