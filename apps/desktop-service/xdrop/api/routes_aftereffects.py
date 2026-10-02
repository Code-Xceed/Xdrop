from typing import List, Optional, Dict, Any
from fastapi import APIRouter
from pydantic import BaseModel
from xdrop.aftereffects import get_aftereffects_bridge

router = APIRouter(prefix="/api/aftereffects", tags=["Adobe After Effects"])

class AfterEffectsHeartbeatRequest(BaseModel):
    isAvailable: bool = True
    currentProject: Optional[str] = None
    activeSequence: Optional[str] = None # In AE, represents active composition
    projectPath: Optional[str] = None
    error: Optional[str] = None

class AfterEffectsImportRequest(BaseModel):
    file_paths: List[str]
    target_bin: str = "Xdrop"

@router.get("/status")
async def get_aftereffects_status():
    """Returns availability and project information for Adobe After Effects."""
    bridge = get_aftereffects_bridge()
    return bridge.get_status()

@router.post("/heartbeat")
async def receive_aftereffects_heartbeat(req: AfterEffectsHeartbeatRequest):
    """Receives live project updates from After Effects CEP extension."""
    bridge = get_aftereffects_bridge()
    bridge.record_heartbeat(req.model_dump())
    return {"success": True, "message": "Heartbeat recorded"}

@router.post("/import")
async def direct_import_to_aftereffects(req: AfterEffectsImportRequest):
    """Triggers import into active After Effects project via CEP bridge."""
    bridge = get_aftereffects_bridge()
    return await bridge.import_media(req.file_paths, req.target_bin)
