import subprocess
import os
import sys
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from xdrop.logger import app_logger, errors_logger

class PremiereBridge:
    """Bridge for Adobe Premiere Pro integration and CEP communication."""

    def __init__(self):
        self._last_heartbeat: Optional[Dict[str, Any]] = None
        self._last_heartbeat_time: Optional[datetime] = None
        self._last_process_check_time: Optional[datetime] = None
        self._last_process_running: bool = False

    def is_running(self) -> bool:
        """Checks if Adobe Premiere Pro process is active with 20s cache."""
        now = datetime.now(timezone.utc)
        if self._last_process_check_time and (now - self._last_process_check_time).total_seconds() < 20.0:
            return self._last_process_running

        try:
            if sys.platform == "win32":
                res = subprocess.run(
                    ["tasklist", "/FI", "IMAGENAME eq Adobe Premiere Pro.exe", "/NH"],
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=2.0
                )
                running = "Adobe Premiere Pro.exe" in res.stdout
            else:
                # macOS / Unix fallback
                res = subprocess.run(
                    ["pgrep", "-f", "Adobe Premiere Pro"],
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=2.0
                )
                running = res.returncode == 0
            self._last_process_running = running
            self._last_process_check_time = now
            return running
        except Exception as e:
            errors_logger.debug(f"Premiere process check exception: {e}")
            return self._last_process_running

    def record_heartbeat(self, info: Dict[str, Any]) -> None:
        """Stores status reported by Premiere Pro CEP panel."""
        self._last_heartbeat = info
        self._last_heartbeat_time = datetime.now(timezone.utc)
        self._last_process_running = True
        self._last_process_check_time = self._last_heartbeat_time
        app_logger.info(f"Premiere Pro heartbeat received: project '{info.get('currentProject')}'")

    def get_status(self) -> Dict[str, Any]:
        """Returns availability and active project status for Adobe Premiere Pro."""
        now = datetime.now(timezone.utc)
        now_str = now.isoformat()

        # If a heartbeat arrived within the last 45s, Premiere is undeniably active
        recent_heartbeat = False
        if self._last_heartbeat_time:
            recent_heartbeat = (now - self._last_heartbeat_time).total_seconds() < 45.0

        running = True if recent_heartbeat else self.is_running()

        if not running and not recent_heartbeat:
            return {
                "isAvailable": False,
                "productName": "Adobe Premiere Pro",
                "currentProject": None,
                "activeSequence": None,
                "error": "Adobe Premiere Pro is not currently running.",
                "lastChecked": now_str
            }

        # Check if we have recent CEP heartbeat
        current_proj = None
        current_seq = None
        proj_path = None
        if self._last_heartbeat:
            current_proj = self._last_heartbeat.get("currentProject")
            current_seq = self._last_heartbeat.get("activeSequence")
            proj_path = self._last_heartbeat.get("projectPath")

        return {
            "isAvailable": True,
            "productName": "Adobe Premiere Pro",
            "currentProject": current_proj or "Active Project",
            "activeSequence": current_seq,
            "projectPath": proj_path,
            "error": None,
            "lastChecked": now_str
        }

    async def import_media(self, file_paths: List[str], target_bin: str = "Xdrop") -> Dict[str, Any]:
        """Broadcasts import request to Premiere Pro CEP extension after ensuring NLE compatibility."""
        import asyncio
        from xdrop.download_queue import get_queue_manager
        from xdrop.processor import get_ffmpeg_processor
        qm = get_queue_manager()
        ffmpeg = get_ffmpeg_processor()
        loop = asyncio.get_running_loop()

        compatible_paths = []
        for fp in file_paths:
            ok, final_fp, _ = await loop.run_in_executor(
                None,
                lambda p=fp: ffmpeg.ensure_nle_compatible(p)
            )
            compatible_paths.append(final_fp if ok else fp)
        
        await qm.broadcast_event("PREMIERE_IMPORT_REQUEST", {
            "filePaths": compatible_paths,
            "targetBin": target_bin,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        return {
            "success": True,
            "message": f"Broadcasted import request for {len(compatible_paths)} files to Premiere Pro.",
            "targetBin": target_bin,
            "filePaths": compatible_paths
        }

    async def import_media_async(self, file_path: str, target_bin: str = "Xdrop") -> Dict[str, Any]:
        return await self.import_media([file_path], target_bin)

_premiere_bridge_instance: Optional[PremiereBridge] = None

def get_premiere_bridge() -> PremiereBridge:
    global _premiere_bridge_instance
    if _premiere_bridge_instance is None:
        _premiere_bridge_instance = PremiereBridge()
    return _premiere_bridge_instance
