from typing import List, Optional
from fastapi import APIRouter
from pydantic import BaseModel
from xdrop.audition import get_audition_bridge

router = APIRouter(prefix="/api/audition", tags=["Adobe Audition"])

class AuditionHeartbeatRequest(BaseModel):
    isAvailable: bool = True
    currentProject: Optional[str] = None
    activeSequence: Optional[str] = None
    projectPath: Optional[str] = None
    error: Optional[str] = None

class AuditionImportRequest(BaseModel):
    file_paths: List[str]
    target_bin: str = "Audition Files"

class PanelImportResultRequest(BaseModel):
    requestId: str
    success: bool
    error: Optional[str] = None
    clipName: Optional[str] = None
    binName: Optional[str] = None

@router.get("/status")
async def get_audition_status():
    """Returns availability and session information for Adobe Audition."""
    bridge = get_audition_bridge()
    return bridge.get_status()

@router.post("/heartbeat")
async def receive_audition_heartbeat(req: AuditionHeartbeatRequest):
    """Receives live session updates from Audition CEP extension."""
    bridge = get_audition_bridge()
    bridge.record_heartbeat(req.model_dump())
    return {"success": True, "message": "Heartbeat recorded"}

@router.post("/import")
async def direct_import_to_audition(req: AuditionImportRequest):
    """Triggers import into active Audition session via CEP bridge."""
    bridge = get_audition_bridge()
    return await bridge.import_media(req.file_paths, req.target_bin)

@router.post("/import-result")
async def receive_audition_import_result(req: PanelImportResultRequest):
    """Receives the real ExtendScript outcome of an import from the CEP panel."""
    bridge = get_audition_bridge()
    return await bridge.apply_import_result(
        req.requestId, req.success, req.error, req.clipName, req.binName
    )
