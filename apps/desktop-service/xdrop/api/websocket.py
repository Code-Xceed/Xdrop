import json
import asyncio
from typing import Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from xdrop.download_queue import get_queue_manager
from xdrop.resolve import get_resolve_bridge
from xdrop.database import get_all_downloads
from xdrop.logger import app_logger, errors_logger

router = APIRouter(tags=["WebSocket"])

class ConnectionManager:
    """Manages connected WebSocket clients."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self._listener_registered = False

    def ensure_queue_listener(self):
        if not self._listener_registered:
            qm = get_queue_manager()
            qm.subscribe(self.broadcast)
            self._listener_registered = True

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        self.ensure_queue_listener()

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)

    async def broadcast(self, message: dict):
        if not self.active_connections:
            return
        payload_str = json.dumps(message)
        dead = []
        for connection in list(self.active_connections):
            try:
                await connection.send_text(payload_str)
            except Exception:
                dead.append(connection)
        for d in dead:
            self.active_connections.discard(d)

manager = ConnectionManager()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    qm = get_queue_manager()
    bridge = get_resolve_bridge()

    try:
        # Send initial sync state on connection
        resolve_stat = bridge.get_status()
        downloads = get_all_downloads()
        await websocket.send_text(json.dumps({
            "type": "INITIAL_STATE",
            "payload": {
                "resolveStatus": resolve_stat,
                "downloads": downloads
            }
        }))

        # Message receive loop
        while True:
            data_text = await websocket.receive_text()
            try:
                msg = json.loads(data_text)
                msg_type = msg.get("type")

                if msg_type == "PING":
                    await websocket.send_text(json.dumps({"type": "PONG"}))
                elif msg_type == "CHECK_RESOLVE":
                    status = bridge.get_status()
                    await websocket.send_text(json.dumps({
                        "type": "RESOLVE_STATUS_CHANGED",
                        "payload": {"resolveStatus": status}
                    }))
                elif msg_type == "CANCEL_JOB":
                    job_id = msg.get("jobId")
                    if job_id:
                        await qm.cancel_job(job_id)
                elif msg_type == "RETRY_JOB":
                    job_id = msg.get("jobId")
                    if job_id:
                        await qm.retry_job(job_id)
                elif msg_type == "REMOVE_JOB":
                    job_id = msg.get("jobId")
                    if job_id:
                        await qm.remove_job(job_id)
                elif msg_type == "TRIGGER_RESOLVE_IMPORT":
                    job_id = msg.get("jobId")
                    if job_id:
                        await qm.import_existing_to_resolve(job_id)
            except json.JSONDecodeError:
                pass
            except Exception as e:
                errors_logger.error(f"WebSocket message handling error: {e}")

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        manager.disconnect(websocket)
