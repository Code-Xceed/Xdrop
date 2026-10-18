from fastapi import APIRouter, Query
from typing import Optional
from pydantic import BaseModel

from xdrop.session import get_session_manager

router = APIRouter(prefix="/api/system/session", tags=["Session"])


class SessionPayload(BaseModel):
    client: Optional[str] = None
    ttl: Optional[int] = 20


@router.post("/open")
async def open_session(payload: Optional[SessionPayload] = None, client: Optional[str] = Query(None)):
    client_id = (payload.client if payload and payload.client else None) or client or "generic"
    sm = get_session_manager()
    sm.register_session(client_id)
    return {
        "status": "ok",
        "client": client_id,
        "activeSessions": sm.get_active_sessions()
    }


@router.post("/heartbeat")
async def session_heartbeat(payload: Optional[SessionPayload] = None, client: Optional[str] = Query(None)):
    client_id = (payload.client if payload and payload.client else None) or client or "generic"
    sm = get_session_manager()
    sm.heartbeat(client_id)
    return {
        "status": "ok",
        "client": client_id,
        "activeSessions": sm.get_active_sessions()
    }


@router.post("/close")
async def close_session(payload: Optional[SessionPayload] = None, client: Optional[str] = Query(None)):
    client_id = (payload.client if payload and payload.client else None) or client or "generic"
    sm = get_session_manager()
    sm.close_session(client_id)
    return {
        "status": "ok",
        "closed": client_id,
        "activeSessions": sm.get_active_sessions()
    }


@router.get("/status")
async def session_status():
    sm = get_session_manager()
    return {
        "status": "ok",
        "activeSessions": sm.get_active_sessions(),
        "isBusy": sm.is_system_busy(),
        "autoShutdownEnabled": sm.enable_auto_shutdown,
    }


@router.post("/shutdown")
async def trigger_shutdown():
    sm = get_session_manager()
    import asyncio
    asyncio.get_event_loop().call_later(0.5, sm.shutdown_engine)
    return {"status": "ok", "message": "Zero-trace shutdown scheduled."}
