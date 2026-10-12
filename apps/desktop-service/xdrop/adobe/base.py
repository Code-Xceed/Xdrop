"""Shared bridge for the Adobe CEP panel used by Premiere Pro and After Effects.

Both hosts talk to the service the same way: the CEP panel heartbeats its project state,
and imports are handed to the panel over the WebSocket, which performs the ExtendScript
import and reports the real outcome back. The only differences between the two hosts are
the product name, the process name, and the event name, so the logic lives here once.
"""

import os
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from xdrop.logger import app_logger, errors_logger


class AdobePanelBridge:
    """Base class for Adobe panel bridges (Premiere Pro, After Effects)."""

    #: Service-side identifier, also used as the import-state key in the database.
    editor_id: str = ""
    #: Human readable product name used in status payloads and error messages.
    product_name: str = ""
    #: Executable names to look for in the OS process list.
    process_candidates: Tuple[str, ...] = ()
    #: Pattern passed to pgrep on macOS/Linux.
    process_grep: str = ""
    #: WebSocket event the panel listens for when we hand it an import.
    import_event: str = ""
    #: How long a heartbeat is considered proof that the panel is still open.
    panel_stale_after: float = 30.0

    def __init__(self) -> None:
        self._last_heartbeat: Optional[Dict[str, Any]] = None
        self._last_heartbeat_time: Optional[datetime] = None
        self._last_process_check_time: Optional[datetime] = None
        self._last_process_running: bool = False
        # Imports handed to the panel that have not reported a result back yet.
        self._pending_requests: Dict[str, Dict[str, Any]] = {}

    # ------------------------------------------------------------------ process ---

    def is_running(self) -> bool:
        """Checks whether the host application process is active, cached for 20 seconds."""
        now = datetime.now(timezone.utc)
        if self._last_process_check_time and (now - self._last_process_check_time).total_seconds() < 20.0:
            return self._last_process_running

        try:
            from xdrop.process_util import is_process_running
            running = is_process_running(self.process_candidates)
            self._last_process_running = running
            self._last_process_check_time = now
            return running
        except Exception as e:
            errors_logger.debug(f"{self.product_name} process check exception: {e}")
            return self._last_process_running

    # ---------------------------------------------------------------- heartbeat ---

    def record_heartbeat(self, info: Dict[str, Any]) -> None:
        """Stores status reported by the CEP panel and marks the panel as attached."""
        self._last_heartbeat = info
        self._last_heartbeat_time = datetime.now(timezone.utc)
        self._last_process_running = True
        self._last_process_check_time = self._last_heartbeat_time
        app_logger.debug(
            f"{self.product_name} heartbeat received: project "
            f"'{info.get('currentProject')}' (item: {info.get('activeSequence')})"
        )

    def has_live_panel(self) -> bool:
        """True only when the CEP panel is actually open and checking in.

        The host process being alive is not enough. Premiere Pro running with the Xdrop
        panel never opened cannot receive anything we broadcast, so treating the process
        alone as "available" is what let imports be reported as successful while doing
        nothing at all.
        """
        if not self._last_heartbeat_time:
            return False
        age = (datetime.now(timezone.utc) - self._last_heartbeat_time).total_seconds()
        return age < self.panel_stale_after

    # ------------------------------------------------------------------- status ---

    def get_status(self) -> Dict[str, Any]:
        """Returns availability and active project/composition status for the host."""
        now = datetime.now(timezone.utc)
        now_str = now.isoformat()

        recent_heartbeat = False
        if self._last_heartbeat_time:
            recent_heartbeat = (now - self._last_heartbeat_time).total_seconds() < 45.0

        running = True if recent_heartbeat else self.is_running()

        if not running and not recent_heartbeat:
            return {
                "isAvailable": False,
                "panelAttached": False,
                "productName": self.product_name,
                "currentProject": None,
                "activeSequence": None,
                "error": f"{self.product_name} is not currently running.",
                "lastChecked": now_str,
            }

        current_proj = None
        current_item = None
        proj_path = None
        if self._last_heartbeat:
            current_proj = self._last_heartbeat.get("currentProject")
            current_item = self._last_heartbeat.get("activeSequence")
            proj_path = self._last_heartbeat.get("projectPath")

        # The host is running but the panel itself may never have been opened, in which
        # case imports cannot be delivered until the user docks it.
        panel_attached = self.has_live_panel()
        error = None
        if not panel_attached:
            error = (
                f"{self.product_name} is running, but the Xdrop panel is not open. "
                f"Open Window > Extensions > Xdrop to enable imports."
            )

        return {
            "isAvailable": True,
            "panelAttached": panel_attached,
            "productName": self.product_name,
            "currentProject": current_proj or "Active Project",
            "activeSequence": current_item,
            "projectPath": proj_path,
            "error": error,
            "lastChecked": now_str,
        }

    # ------------------------------------------------------------------- import ---

    def _prune_pending_requests(self, max_age_seconds: float = 600.0) -> None:
        """Drops import requests the panel never answered so the registry cannot grow."""
        now = datetime.now(timezone.utc)
        stale = [
            req_id
            for req_id, req in self._pending_requests.items()
            if (now - req["createdAt"]).total_seconds() > max_age_seconds
        ]
        for req_id in stale:
            self._pending_requests.pop(req_id, None)

    def pop_import_request(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Removes and returns a tracked import request, or None if it is unknown."""
        return self._pending_requests.pop(request_id, None)

    def pending_request_count(self) -> int:
        return len(self._pending_requests)

    async def import_media(
        self,
        file_paths: List[str],
        target_bin: str = "000_Xdrop Assets",
        job_ids: Optional[List[str]] = None,
        asset_paths: Optional[List[str]] = None,
        insert_timeline: bool = False,
    ) -> Dict[str, Any]:
        """Hands files to the CEP panel for import into the active project.

        Returns as soon as the panel has been given the work: the ExtendScript result
        arrives later and is applied by `apply_import_result`. A request is only ever
        sent to a panel that is actually open, so `success` means the panel accepted it
        rather than that the clip has landed in the project.
        """
        import asyncio
        from xdrop.download_queue import get_queue_manager
        from xdrop.processor import get_ffmpeg_processor

        if not file_paths:
            return {"success": False, "confirmed": False, "error": "No files were given to import."}

        if not self.has_live_panel():
            return {
                "success": False,
                "confirmed": False,
                "requestId": None,
                "error": (
                    f"The Xdrop panel is not open in {self.product_name}. "
                    f"Open Window > Extensions > Xdrop, then import again."
                ),
            }

        qm = get_queue_manager()
        ffmpeg = get_ffmpeg_processor()
        loop = asyncio.get_running_loop()

        compatible_paths: List[str] = []
        for fp in file_paths:
            ok, final_fp, _ = await loop.run_in_executor(
                None, lambda p=fp: ffmpeg.ensure_nle_compatible(p)
            )
            compatible_paths.append(final_fp if ok else fp)

        deliverable = [p for p in compatible_paths if os.path.isfile(p)]
        missing = [p for p in compatible_paths if not os.path.isfile(p)]
        if not deliverable:
            return {
                "success": False,
                "confirmed": False,
                "requestId": None,
                "error": "None of the files to import exist on disk any more.",
                "missing": missing,
            }

        self._prune_pending_requests()
        request_id = f"imp_{uuid.uuid4().hex[:10]}"
        self._pending_requests[request_id] = {
            "filePaths": deliverable,
            "targetBin": target_bin,
            "jobIds": list(job_ids or []),
            # Library rows are keyed by the path the user sees, which is the pre-conversion
            # path, so it is tracked separately from the (possibly transcoded) import path.
            "assetPaths": list(asset_paths) if asset_paths else list(deliverable),
            "insertTimeline": bool(insert_timeline),
            "createdAt": datetime.now(timezone.utc),
        }

        await qm.broadcast_event(self.import_event, {
            "requestId": request_id,
            "filePaths": deliverable,
            "targetBin": target_bin,
            "jobIds": list(job_ids or []),
            "insertTimeline": bool(insert_timeline),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        return {
            "success": True,
            "confirmed": False,
            "requestId": request_id,
            "message": f"Sent {len(deliverable)} file(s) to {self.product_name} for import.",
            "targetBin": target_bin,
            "filePaths": deliverable,
            "missing": missing,
        }

    async def import_media_async(
        self,
        file_path: str,
        target_bin: str = "000_Xdrop Assets",
        job_ids: Optional[List[str]] = None,
        asset_paths: Optional[List[str]] = None,
        insert_timeline: bool = False,
    ) -> Dict[str, Any]:
        return await self.import_media([file_path], target_bin, job_ids, asset_paths, insert_timeline)

    async def apply_import_result(
        self,
        request_id: str,
        success: bool,
        error: Optional[str] = None,
        clip_name: Optional[str] = None,
        bin_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Applies the panel's real ExtendScript outcome to the jobs that requested it."""
        from xdrop.database import (
            get_download_by_id,
            set_asset_import_flag,
            update_download_import_state,
        )
        from xdrop.download_queue import get_queue_manager

        request = self.pop_import_request(request_id)
        if not request:
            return {"success": False, "error": f"Unknown or already-settled import request: {request_id}"}

        target_bin = bin_name or request.get("targetBin") or "Xdrop"
        job_ids: List[str] = request.get("jobIds") or []
        reason = None if success else (error or "The editor rejected the import.")

        for job_id in job_ids:
            update_download_import_state(
                job_id,
                self.editor_id,
                imported=bool(success),
                pending=not success,
                error=None if success else reason,
                bin_name=target_bin,
                clip_name=clip_name if success else None,
            )


        if success:
            # Keep the library view in step with the confirmed import.
            for asset_path in request.get("assetPaths") or []:
                set_asset_import_flag(asset_path, self.editor_id, True)
            app_logger.info(f"Confirmed import into {self.product_name} bin '{target_bin}'.")
        else:
            app_logger.warning(f"Import into {self.product_name} failed: {reason}")

        qm = get_queue_manager()
        for job_id in job_ids:
            await qm.broadcast_event("JOB_IMPORT_STATE", {
                "jobId": job_id,
                "editor": self.editor_id,
                "success": bool(success),
                "binName": target_bin,
                "clipName": clip_name,
                "error": reason,
                "job": get_download_by_id(job_id),
            })

        return {
            "success": True,
            "confirmed": bool(success),
            "jobIds": job_ids,
            "binName": target_bin,
            "clipName": clip_name,
            "error": reason,
        }
