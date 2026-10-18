import asyncio
import os
import sys
import json
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable, Set
from datetime import datetime, timezone

from xdrop.download_queue.models import CreateDownloadRequest
from xdrop.database import (
    insert_download,
    update_download_progress,
    update_download_status,
    update_download_import_state,
    get_download_by_id,
    get_all_downloads,
    get_jobs_pending_import,
    set_asset_import_flag,
    delete_download,
    insert_library_item,
    get_settings_from_db,
)
from xdrop.providers import get_provider_manager
from xdrop.processor import get_ffmpeg_processor, MediaOrganizer, sanitize_filename_py
from xdrop.resolve import get_resolve_bridge
from xdrop.config import AppSettingsModel, DATA_DIR, PROXIES_DIR
from xdrop.logger import downloads_logger, errors_logger

#: Display names used when explaining why an import is waiting for an editor.
EDITOR_LABELS = {
    "resolve": "DaVinci Resolve",
    "premiere": "Adobe Premiere Pro",
    "aftereffects": "Adobe After Effects",
    "audition": "Adobe Audition",
}

class DownloadQueueManager:
    """Orchestrates asynchronous download queue, processing, and editor imports."""

    #: Editors in preference order; Resolve first because it is the signature integration.
    EDITOR_ORDER = ("resolve", "premiere", "aftereffects", "audition")
    #: How often deferred imports are retried against newly available editors.
    FLUSH_INTERVAL_SECONDS = 10.0

    def __init__(self):
        self._queue: asyncio.Queue = asyncio.Queue()
        self._active_tasks: Dict[str, asyncio.Task] = {}
        self._cancelled_jobs: Set[str] = set()
        self._subscribers: List[Callable[[Dict[str, Any]], Any]] = []
        self._workers: List[asyncio.Task] = []
        self._running = False
        # (job_id, editor) pairs already retried by the flush loop this service run, so a
        # permanently failing import cannot be retried forever in the background.
        self._flush_attempted: Set[tuple] = set()
        self._flush_task: Optional[asyncio.Task] = None
        self._ipc_task: Optional[asyncio.Task] = None

    def is_busy(self) -> bool:
        """Returns True if any downloads or processing tasks are currently active or queued."""
        return len(self._active_tasks) > 0 or self._queue.qsize() > 0

    def _get_ipc_dir(self) -> Path:
        if sys.platform == "win32":
            base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "Xdrop" / "ipc"
        else:
            base = Path.home() / ".xdrop" / "ipc"
        return base

    def _sync_ipc_status(self, event_type: str, payload: Dict[str, Any]) -> None:
        try:
            ipc_dir = self._get_ipc_dir()
            status_dir = ipc_dir / "status"
            status_dir.mkdir(parents=True, exist_ok=True)

            job_id = None
            status_data: Dict[str, Any] = {}

            if event_type == "JOB_PROGRESS":
                prog = payload.get("progress") or {}
                job_id = prog.get("id")
                if job_id:
                    status_data = {
                        "id": job_id,
                        "status": prog.get("status", "downloading"),
                        "progress": prog.get("progress", 0.0),
                        "speed": prog.get("speed") or "",
                        "eta": prog.get("eta"),
                        "downloaded_bytes": prog.get("downloadedBytes", 0),
                        "output_file_path": prog.get("outputFilePath") or prog.get("output_file_path"),
                        "error_message": prog.get("errorMessage")
                    }
            elif event_type == "JOB_COMPLETED":
                job_id = payload.get("jobId") or (payload.get("job") or {}).get("id")
                job_obj = payload.get("job") or {}
                if job_id:
                    status_data = {
                        "id": job_id,
                        "status": "completed",
                        "progress": 100.0,
                        "speed": "",
                        "output_file_path": job_obj.get("output_file_path") or payload.get("outputFilePath"),
                        "imported": True
                    }
            elif event_type == "JOB_FAILED":
                job_id = payload.get("jobId")
                if job_id:
                    status_data = {
                        "id": job_id,
                        "status": "failed",
                        "progress": 0.0,
                        "error_message": payload.get("message")
                    }

            if job_id and status_data:
                target_file = status_dir / f"job_{job_id}.json"
                temp_file = status_dir / f"job_{job_id}.tmp"
                temp_file.write_text(json.dumps(status_data), encoding="utf-8")
                temp_file.replace(target_file)
        except Exception as e:
            errors_logger.debug(f"IPC status sync error: {e}")

    async def _ipc_loop(self) -> None:
        """Watches ipc/jobs for requests from native Lua / editor scripts and updates heartbeat with zero flicker."""
        ipc_dir = self._get_ipc_dir()
        jobs_dir = ipc_dir / "jobs"
        status_dir = ipc_dir / "status"
        heartbeat_file = ipc_dir / "heartbeat.json"

        try:
            jobs_dir.mkdir(parents=True, exist_ok=True)
            status_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

        import time

        while self._running:
            try:
                # 1. Update heartbeat
                hb_tmp = ipc_dir / "heartbeat.tmp"
                hb_data = {
                    "status": "ok",
                    "healthy": True,
                    "pid": os.getpid(),
                    "timestamp": int(time.time()),
                    "service": "Xdrop",
                    "version": "1.1.0"
                }
                hb_tmp.write_text(json.dumps(hb_data), encoding="utf-8")
                hb_tmp.replace(heartbeat_file)

                # 2. Check for incoming job requests
                if jobs_dir.exists():
                    for job_file in list(jobs_dir.glob("*.json")):
                        try:
                            content = job_file.read_text(encoding="utf-8")
                            job_file.unlink(missing_ok=True)
                            data = json.loads(content)
                            explicit_id = data.get("id")
                            req = CreateDownloadRequest(**data)
                            await self.add_download(req, explicit_job_id=explicit_id)
                        except Exception as jerr:
                            errors_logger.error(f"Error parsing IPC job {job_file}: {jerr}")

                await asyncio.sleep(0.5)
            except asyncio.CancelledError:
                break
            except Exception as e:
                errors_logger.debug(f"IPC loop iteration exception: {e}")
                await asyncio.sleep(1.0)

    def subscribe(self, callback: Callable[[Dict[str, Any]], Any]) -> None:
        """Subscribes a listener (e.g. WebSocket broadcaster) to queue events."""
        if callback not in self._subscribers:
            self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[Dict[str, Any]], Any]) -> None:
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    async def broadcast_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Broadcasts event to all active WebSocket listeners and writes to IPC status files."""
        self._sync_ipc_status(event_type, payload)
        msg = {
            "type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": payload
        }
        for sub in list(self._subscribers):
            try:
                res = sub(msg)
                if asyncio.iscoroutine(res):
                    await res
            except Exception as e:
                errors_logger.error(f"Error notifying subscriber: {e}")

    async def start(self) -> None:
        """Starts worker pool for processing downloads."""
        if self._running:
            return
        self._running = True
        settings = self._get_settings()
        worker_count = max(1, min(settings.concurrent_downloads, 6))
        for i in range(worker_count):
            task = asyncio.create_task(self._worker_loop(f"worker-{i+1}"))
            self._workers.append(task)
        self._flush_task = asyncio.create_task(self._flush_pending_loop())
        self._ipc_task = asyncio.create_task(self._ipc_loop())
        downloads_logger.info(f"DownloadQueueManager started with {worker_count} workers and zero-flicker IPC.")

    async def stop(self) -> None:
        self._running = False
        if self._ipc_task:
            self._ipc_task.cancel()
            self._ipc_task = None
        if self._flush_task:
            self._flush_task.cancel()
            self._flush_task = None
        for task in self._workers:
            task.cancel()
        self._workers.clear()

    def _get_settings(self) -> AppSettingsModel:
        db_settings = get_settings_from_db()
        return AppSettingsModel(**db_settings)

    # ------------------------------------------------------------- editor imports ---

    def _import_flag(self, req: CreateDownloadRequest, settings: AppSettingsModel, editor: str) -> bool:
        """Resolves the per-editor auto-import flag, preferring the request over settings."""
        explicit = {
            "resolve": req.auto_import_to_resolve,
            "premiere": req.auto_import_to_premiere,
            "aftereffects": req.auto_import_to_aftereffects,
            "audition": getattr(req, "auto_import_to_audition", None),
        }.get(editor)
        if explicit is not None:
            return bool(explicit)
        return bool(getattr(settings, f"auto_import_to_{editor}", True))

    def requested_editors(self, req: CreateDownloadRequest, settings: AppSettingsModel) -> List[str]:
        """Editors this job should land in, in preference order.

        An explicit per-job target wins. Under 'auto' every enabled editor is a candidate
        and the ones actually open at completion time receive the file.
        """
        target = (req.target_editor or getattr(settings, "default_editor", "auto") or "auto").lower()
        if target in self.EDITOR_ORDER:
            return [target]
        return [e for e in self.EDITOR_ORDER if self._import_flag(req, settings, e)]

    def editor_available(self, editor: str) -> bool:
        """Whether the editor can receive an import right now.

        Resolve counts as available when the app is running. The Adobe hosts additionally
        require the Xdrop CEP panel to be open, because a broadcast can only be received
        by a panel that is actually listening.
        """
        from xdrop.resolve import get_resolve_bridge
        from xdrop.premiere import get_premiere_bridge
        from xdrop.aftereffects import get_aftereffects_bridge
        from xdrop.audition import get_audition_bridge

        if editor == "resolve":
            return get_resolve_bridge().is_running()
        if editor == "premiere":
            return get_premiere_bridge().has_live_panel()
        if editor == "aftereffects":
            return get_aftereffects_bridge().has_live_panel()
        if editor == "audition":
            return get_audition_bridge().has_live_panel()
        return False

    @staticmethod
    def _settings_bin(settings: AppSettingsModel, editor: str) -> str:
        if editor == "resolve":
            return settings.target_media_pool_bin or "000_Xdrop Assets"
        return getattr(settings, f"target_{editor}_bin", "") or "000_Xdrop Assets"

    def _bin_for_request(self, req: CreateDownloadRequest, settings: AppSettingsModel, editor: str) -> str:
        explicit = {
            "resolve": req.target_media_pool_bin,
            "premiere": req.target_premiere_bin,
            "aftereffects": req.target_aftereffects_bin,
            "audition": getattr(req, "target_audition_bin", None),
        }.get(editor)
        return explicit or self._settings_bin(settings, editor)

    @staticmethod
    def _stored_bin(job: Dict[str, Any], editor: str) -> Optional[str]:
        return {
            "resolve": job.get("resolveBin"),
            "premiere": job.get("premiereBin"),
            "aftereffects": job.get("aftereffectsBin"),
            "audition": job.get("auditionBin"),
        }.get(editor)

    async def attempt_import(
        self,
        job_id: str,
        editor: str,
        file_path: str,
        bin_name: str,
        insert_timeline: bool = False,
    ) -> Dict[str, Any]:
        """Imports one file into one editor and records the true outcome for that job.

        Resolve imports happen inline, so success is confirmed immediately. The Adobe
        hosts hand the work to the CEP panel and confirm later, so a delivered request is
        left 'pending' rather than reported as imported.
        """
        if editor == "resolve":
            from xdrop.resolve import get_resolve_bridge

            bridge = get_resolve_bridge()
            loop = asyncio.get_running_loop()
            res = await loop.run_in_executor(
                None, lambda: bridge.import_media([file_path], bin_name, insert_timeline=insert_timeline)
            )
            if res.get("success"):
                update_download_import_state(
                    job_id,
                    editor,
                    imported=True,
                    bin_name=bin_name,
                    clip_name=res.get("clipName"),
                )
                set_asset_import_flag(file_path, editor, True)
                return {"success": True, "confirmed": True, "clipName": res.get("clipName")}

            error = res.get("error") or "DaVinci Resolve import failed."
            update_download_import_state(
                job_id, editor, imported=False, pending=True, error=error, bin_name=bin_name
            )
            return {"success": False, "confirmed": False, "error": error}

        if editor == "premiere":
            from xdrop.premiere import get_premiere_bridge

            bridge = get_premiere_bridge()
        elif editor == "aftereffects":
            from xdrop.aftereffects import get_aftereffects_bridge

            bridge = get_aftereffects_bridge()
        elif editor == "audition":
            from xdrop.audition import get_audition_bridge

            bridge = get_audition_bridge()
        else:
            return {"success": False, "confirmed": False, "error": f"Unknown editor '{editor}'"}

        res = await bridge.import_media([file_path], bin_name, [job_id], insert_timeline=insert_timeline)
        if res.get("success"):
            update_download_import_state(
                job_id, editor, pending=True, error=None, bin_name=bin_name
            )
            return {
                "success": True,
                "confirmed": False,
                "requestId": res.get("requestId"),
            }

        error = res.get("error") or f"{editor} import failed."
        update_download_import_state(
            job_id, editor, imported=False, pending=True, error=error, bin_name=bin_name
        )
        return {"success": False, "confirmed": False, "error": error}

    async def run_editor_imports(
        self,
        job_id: str,
        file_path: str,
        req: CreateDownloadRequest,
        settings: AppSettingsModel,
        downloaded_bytes: int = 0,
    ) -> List[Dict[str, Any]]:
        """Imports a finished download into the editors it was requested for.

        Editors that are open receive the file immediately. When none of the requested
        editors can accept it, the import is recorded as pending against the preferred
        editor so the background flush finishes it once that editor is open, instead of
        the download silently landing nowhere.
        """
        requested = self.requested_editors(req, settings)
        if not requested:
            return []

        available = [e for e in requested if self.editor_available(e)]
        summary: List[Dict[str, Any]] = []

        if available:
            update_download_status(job_id, "importing")
            await self.broadcast_event("JOB_PROGRESS", {
                "progress": {
                    "id": job_id,
                    "status": "importing",
                    "progress": 95.0,
                    "downloadedBytes": downloaded_bytes,
                    "speed": None,
                    "eta": None,
                }
            })

        for editor in available:
            bin_name = self._bin_for_request(req, settings, editor)
            outcome = await self.attempt_import(
                job_id, editor, file_path, bin_name, insert_timeline=bool(req.insert_timeline)
            )
            summary.append({"editor": editor, "bin": bin_name, **outcome})
            if outcome.get("success"):
                state = "confirmed" if outcome.get("confirmed") else "requested, awaiting the editor"
                downloads_logger.info(
                    f"Import of {file_path} into {EDITOR_LABELS[editor]} bin '{bin_name}': {state}."
                )
            else:
                downloads_logger.warning(
                    f"Import of {file_path} into {EDITOR_LABELS[editor]} not delivered: "
                    f"{outcome.get('error')}"
                )

        if not available:
            editor = requested[0]
            bin_name = self._bin_for_request(req, settings, editor)
            reason = (
                f"{EDITOR_LABELS[editor]} was not available when the download finished. "
                f"Xdrop will import this file automatically once {EDITOR_LABELS[editor]} is open."
            )
            update_download_import_state(
                job_id, editor, imported=False, pending=True, error=reason, bin_name=bin_name
            )
            summary.append({
                "editor": editor,
                "bin": bin_name,
                "success": False,
                "confirmed": False,
                "deferred": True,
                "error": reason,
            })
            downloads_logger.info(
                f"Deferred import of {file_path} until {EDITOR_LABELS[editor]} is available."
            )

        return summary

    async def broadcast_import_state(self, job_id: str, editor: Optional[str] = None) -> None:
        """Pushes the refreshed job so panels show real, current import state."""
        job = get_download_by_id(job_id)
        if not job:
            return
        await self.broadcast_event("JOB_IMPORT_STATE", {
            "jobId": job_id,
            "editor": editor,
            "job": job,
        })

    async def flush_pending_imports(self, force: bool = False) -> List[Dict[str, Any]]:
        """Imports files that were deferred because their target editor was not open.

        Each (job, editor) pair is attempted at most once per service run unless `force`
        is set, so an import that keeps failing cannot retry forever in the background.
        """
        results: List[Dict[str, Any]] = []
        for editor in self.EDITOR_ORDER:
            if not self.editor_available(editor):
                continue
            for job in get_jobs_pending_import(editor):
                job_id = job["id"]
                key = (job_id, editor)
                if not force and key in self._flush_attempted:
                    continue
                self._flush_attempted.add(key)

                file_path = job.get("output_file_path")
                if not file_path or not os.path.isfile(file_path):
                    continue

                settings = self._get_settings()
                bin_name = self._stored_bin(job, editor) or self._settings_bin(settings, editor)
                outcome = await self.attempt_import(job_id, editor, file_path, bin_name)
                results.append({"jobId": job_id, "editor": editor, "bin": bin_name, **outcome})
                await self.broadcast_import_state(job_id, editor)
        return results

    async def _flush_pending_loop(self) -> None:
        """Retries deferred imports periodically so they land once the editor opens."""
        while self._running:
            try:
                await asyncio.sleep(self.FLUSH_INTERVAL_SECONDS)
                flushed = await self.flush_pending_imports()
                if flushed:
                    downloads_logger.info(
                        f"Deferred import flush handled {len(flushed)} import(s)."
                    )
            except asyncio.CancelledError:
                break
            except Exception as e:
                errors_logger.error(f"Deferred import flush error: {e}", exc_info=True)

    async def add_download(self, req: CreateDownloadRequest, explicit_job_id: Optional[str] = None) -> Dict[str, Any]:
        """Creates a download job and places it in the processing queue."""
        clean_url = req.source_url.strip()
        if clean_url and not (clean_url.startswith("http://") or clean_url.startswith("https://")):
            clean_url = "https://" + clean_url
        req.source_url = clean_url

        job_id = explicit_job_id or f"dl_{uuid.uuid4().hex[:10]}"
        pm = get_provider_manager()
        provider = pm.find_provider_for_url(req.source_url)
        platform_id = provider.platform_id if provider else "generic"

        title = req.title or "Media Asset"
        now = datetime.now(timezone.utc).isoformat()

        is_auto_import = bool(
            req.auto_import_to_resolve or
            req.auto_import_to_premiere or
            req.auto_import_to_aftereffects or
            req.auto_import_to_audition
        )

        job_data = {
            "id": job_id,
            "source_url": req.source_url,
            "platform": platform_id,
            "title": title,
            "author": req.author,
            "media_type": req.media_type,
            "format": req.format,
            "quality_label": req.quality_label,
            "asset_id": req.asset_id,
            "status": "queued",
            "progress": 0.0,
            "speed": None,
            "eta": None,
            "downloaded_bytes": 0,
            "total_bytes": None,
            "output_file_path": None,
            "thumbnail_path": None,
            "error_message": None,
            "resolve_imported": False,
            "resolve_clip_name": None,
            "premiere_imported": False,
            "premiere_bin": None,
            "aftereffects_imported": False,
            "aftereffects_bin": None,
            "audition_imported": False,
            "audition_bin": None,
            "target_editor": req.target_editor,
            "auto_import": 1 if is_auto_import else 0,
            "created_at": now,
            "completed_at": None,
        }

        # Save to database
        insert_download(job_data)

        # Notify subscribers
        await self.broadcast_event("JOB_CREATED", {"job": job_data})

        # Add to async queue
        await self._queue.put((job_id, req))
        downloads_logger.info(f"Queued job {job_id} for {req.source_url} ({req.quality_label})")

        return job_data

    async def cancel_job(self, job_id: str) -> bool:
        """Cancels a queued or active download."""
        self._cancelled_jobs.add(job_id)
        if job_id in self._active_tasks:
            self._active_tasks[job_id].cancel()

        update_download_status(job_id, "cancelled", "Cancelled by user.")
        await self.broadcast_event("JOB_UPDATED", {
            "jobId": job_id,
            "progress": {
                "id": job_id,
                "status": "cancelled",
                "progress": 0.0,
                "downloadedBytes": 0,
                "errorMessage": "Cancelled by user."
            }
        })
        downloads_logger.info(f"Cancelled job: {job_id}")
        return True

    async def retry_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Retries a failed or cancelled download job."""
        job = get_download_by_id(job_id)
        if not job:
            return None

        # Wait for any lingering active worker task to complete/cancel before re-queueing
        task = self._active_tasks.get(job_id)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass

        self._cancelled_jobs.discard(job_id)
        update_download_status(job_id, "queued", None)
        update_download_progress(job_id, "queued", 0.0, 0)

        req = CreateDownloadRequest(
            source_url=job["source_url"],
            asset_id=job.get("asset_id") or "best_video",
            format=job["format"],
            quality_label=job["quality_label"],
            media_type=job["media_type"],
            title=job["title"],
            author=job.get("author")
        )

        await self._queue.put((job_id, req))
        await self.broadcast_event("JOB_UPDATED", {
            "jobId": job_id,
            "progress": {
                "id": job_id,
                "status": "queued",
                "progress": 0.0,
                "downloadedBytes": 0,
            }
        })
        downloads_logger.info(f"Retrying job {job_id}")
        return get_download_by_id(job_id)

    async def remove_job(self, job_id: str) -> bool:
        """Removes job from queue and database."""
        await self.cancel_job(job_id)
        delete_download(job_id)
        await self.broadcast_event("JOB_REMOVED", {"jobId": job_id})
        return True

    async def _worker_loop(self, worker_name: str) -> None:
        """Background worker that continuously pulls and processes jobs."""
        while self._running:
            try:
                job_id, req = await self._queue.get()
                if job_id in self._cancelled_jobs:
                    self._queue.task_done()
                    continue

                task = asyncio.create_task(self._process_download(job_id, req))
                self._active_tasks[job_id] = task

                try:
                    await task
                except asyncio.CancelledError:
                    downloads_logger.info(f"Task {job_id} cancelled.")
                except Exception as e:
                    errors_logger.error(f"Worker {worker_name} error on job {job_id}: {e}", exc_info=True)
                    update_download_status(job_id, "failed", str(e))
                    await self.broadcast_event("JOB_FAILED", {"jobId": job_id, "message": str(e)})
                    await self.broadcast_event("JOB_PROGRESS", {
                        "progress": {
                            "id": job_id,
                            "status": "failed",
                            "progress": 0.0,
                            "errorMessage": str(e)
                        }
                    })
                finally:
                    self._active_tasks.pop(job_id, None)
                    self._queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception as e:
                errors_logger.error(f"Worker {worker_name} exception: {e}", exc_info=True)
                await asyncio.sleep(1.0)

    async def _process_download(self, job_id: str, req: CreateDownloadRequest) -> None:
        """Executes full download -> process -> resolve import pipeline."""
        try:
            settings = self._get_settings()
            bridge = get_resolve_bridge()
            ffmpeg = get_ffmpeg_processor(settings.ffmpeg_path)
            organizer = MediaOrganizer(settings.download_dir)

            # 1. Update status to downloading
            update_download_status(job_id, "downloading")
            await self.broadcast_event("JOB_PROGRESS", {
                "progress": {
                    "id": job_id,
                    "status": "downloading",
                    "progress": 1.0,
                    "downloadedBytes": 0,
                }
            })

            pm = get_provider_manager()
            provider = pm.find_provider_for_url(req.source_url)
            if not provider:
                err = f"No provider available for {req.source_url}"
                update_download_status(job_id, "failed", err)
                await self.broadcast_event("JOB_FAILED", {"jobId": job_id, "message": err})
                return

            # Query active Resolve project name for template path
            resolve_status = bridge.get_status()
            current_project_name = resolve_status.get("currentProject") or "Xdrop"

            # Determine target file path using organizer
            target_ext = req.format or "mp4"
            dest_file = organizer.resolve_destination(
                naming_pattern=settings.naming_pattern,
                project_name=current_project_name,
                platform=provider.platform_id,
                media_type=req.media_type,
                title=req.title or "asset",
                quality_label=req.quality_label,
                extension=target_ext,
                overwrite_existing=settings.overwrite_existing
            )
        except Exception as e:
            errors_logger.error(f"Error initializing download for job {job_id}: {e}", exc_info=True)
            update_download_status(job_id, "failed", str(e))
            await self.broadcast_event("JOB_FAILED", {"jobId": job_id, "message": str(e)})
            await self.broadcast_event("JOB_PROGRESS", {
                "progress": {
                    "id": job_id,
                    "status": "failed",
                    "progress": 0.0,
                    "errorMessage": str(e)
                }
            })
            return

        loop = asyncio.get_running_loop()
        import time
        last_broadcast_time = 0.0

        # Thread-safe progress hook for provider
        def on_progress(p_dict: Dict[str, Any]):
            nonlocal last_broadcast_time
            if job_id in self._cancelled_jobs:
                raise asyncio.CancelledError("Download cancelled by user.")

            now_t = time.time()
            progress_val = float(p_dict.get("progress", 0.0) or 0.0)
            down_bytes = int(p_dict.get("downloaded_bytes", 0) or 0)
            tot_bytes = p_dict.get("total_bytes")
            spd = p_dict.get("speed")
            eta_val = p_dict.get("eta")

            # Throttle progress updates to at most once per 250ms unless near completion
            if progress_val < 99.0 and (now_t - last_broadcast_time) < 0.25:
                return

            last_broadcast_time = now_t

            update_download_progress(
                job_id=job_id,
                status="downloading",
                progress=progress_val,
                downloaded_bytes=down_bytes,
                total_bytes=tot_bytes,
                speed=spd,
                eta=eta_val
            )

            # Schedule broadcast in event loop
            asyncio.run_coroutine_threadsafe(
                self.broadcast_event("JOB_PROGRESS", {
                    "progress": {
                        "id": job_id,
                        "status": "downloading",
                        "progress": progress_val,
                        "downloadedBytes": down_bytes,
                        "totalBytes": tot_bytes,
                        "speed": spd,
                        "eta": eta_val,
                    }
                }),
                loop
            )

        # 2. Perform Download
        downloads_logger.info(f"Starting provider download for job {job_id} -> {dest_file}")
        try:
            download_result = await loop.run_in_executor(
                None,
                lambda: provider.download(
                    url=req.source_url,
                    asset_id=req.asset_id,
                    output_template=str(dest_file),
                    progress_callback=on_progress
                )
            )
        except Exception as e:
            errors_logger.error(f"Download exception in job {job_id}: {e}")
            update_download_status(job_id, "failed", str(e))
            await self.broadcast_event("JOB_FAILED", {"jobId": job_id, "message": str(e)})
            return

        if not download_result.success or not download_result.output_file_path:
            err = download_result.error_message or "Download failed."
            update_download_status(job_id, "failed", err)
            await self.broadcast_event("JOB_FAILED", {"jobId": job_id, "message": err})
            return

        final_file = download_result.output_file_path

        # 3. Post-Processing (FFmpeg)
        update_download_status(job_id, "processing")
        await self.broadcast_event("JOB_PROGRESS", {
            "progress": {
                "id": job_id,
                "status": "processing",
                "progress": 85.0,
                "downloadedBytes": download_result.downloaded_bytes,
                "speed": None,
                "eta": None,
            }
        })

        # Audio extraction if requested
        if req.extract_audio_only or "audio" in req.asset_id.lower() or req.media_type == "audio":
            target_afmt = req.format or ("wav" if "wav" in req.asset_id.lower() else "mp3")
            audio_out = Path(final_file).with_suffix(f".{target_afmt}")
            if final_file != str(audio_out) or Path(final_file).suffix.lower() not in (".wav", ".mp3", ".m4a", ".aac", ".flac"):
                success, audio_err = await loop.run_in_executor(
                    None,
                    lambda: ffmpeg.extract_audio(final_file, str(audio_out), target_afmt)
                )
                if success and audio_out.exists():
                    orig_raw = final_file
                    final_file = str(audio_out)
                    if orig_raw != final_file and Path(orig_raw).exists():
                        try:
                            Path(orig_raw).unlink()
                        except Exception:
                            pass

        # Video format transcoding if requested (e.g. ProRes MOV or Universal MP4)
        target_vfmt = req.transcode_video_format or (req.format if req.format and req.format.lower() in ("mov", "mp4") else None) or (settings.preferred_video_format if settings.preferred_video_format != "original" else None)
        if target_vfmt and req.media_type == "video" and not req.extract_audio_only and not ("audio" in req.asset_id.lower()):
            current_ext = Path(final_file).suffix.lower().lstrip(".")
            if target_vfmt.lower() != current_ext:
                trans_out = Path(final_file).with_suffix(f".{target_vfmt.lower()}")
                if str(trans_out) != str(final_file):
                    success, v_err = await loop.run_in_executor(
                        None,
                        lambda: ffmpeg.convert_video_format(final_file, str(trans_out), target_vfmt.lower())
                    )
                    if success and trans_out.exists():
                        orig_raw = final_file
                        final_file = str(trans_out)
                        if orig_raw != final_file and Path(orig_raw).exists():
                            try:
                                Path(orig_raw).unlink()
                            except Exception:
                                pass

        # Always ensure NLE codec compatibility for video assets
        # (transcodes AV1/VP9 video to H.264 and Opus audio to AAC so Premiere Pro and Resolve never fail on import)
        if req.media_type == "video" and not req.extract_audio_only:
            compat_ok, compat_path, compat_err = await loop.run_in_executor(
                None,
                lambda: ffmpeg.ensure_nle_compatible(final_file, target_vfmt or "mp4")
            )
            if compat_ok and compat_path:
                final_file = compat_path

        # Generate thumbnail if video
        thumb_path = None
        if req.media_type == "video" or Path(final_file).suffix.lower() in (".mp4", ".mov", ".mkv", ".webm"):
            thumb_path = await loop.run_in_executor(
                None,
                lambda: ffmpeg.extract_thumbnail(final_file)
            )

        # Generate optional proxy
        if req.generate_proxy or settings.generate_proxy:
            proxy_out = PROXIES_DIR / f"proxy_{Path(final_file).stem}.mp4"
            await loop.run_in_executor(
                None,
                lambda: ffmpeg.generate_proxy(final_file, str(proxy_out), settings.proxy_resolution)
            )

        # 4. Probe metadata & insert into Library Assets
        probe_info = await loop.run_in_executor(
            None,
            lambda: ffmpeg.probe_media_info(final_file)
        )

        res_str = f"{probe_info['width']}x{probe_info['height']}" if probe_info.get("width") else None
        library_item = {
            "id": f"ast_{uuid.uuid4().hex[:10]}",
            "download_id": job_id,
            "source_url": req.source_url,
            "platform": provider.platform_id,
            "title": req.title or Path(final_file).stem,
            "author": req.author,
            "media_type": req.media_type,
            "format": Path(final_file).suffix.lstrip("."),
            "resolution": res_str,
            "duration": probe_info.get("duration"),
            "file_size_bytes": probe_info.get("filesize", 0),
            "file_path": str(Path(final_file).resolve()),
            "thumbnail_path": thumb_path,
            "resolve_imported": False,
        }
        insert_library_item(library_item)

        # Generate universal FCPXML sidecar for instant timeline drag-and-drop across any NLE
        try:
            from xdrop.processor.fcpxml import write_fcpxml_sidecar
            await loop.run_in_executor(
                None,
                lambda: write_fcpxml_sidecar(
                    file_path=final_file,
                    title=req.title or Path(final_file).stem,
                    duration_sec=probe_info.get("duration"),
                    width=probe_info.get("width") or 1920,
                    height=probe_info.get("height") or 1080,
                    fps=30.0,
                )
            )
        except Exception as fc_err:
            downloads_logger.debug(f"FCPXML sidecar generation note: {fc_err}")

        # 5. Editor import automation (DaVinci Resolve, Premiere Pro, After Effects).
        import_summary = await self.run_editor_imports(
            job_id,
            final_file,
            req,
            settings,
            download_result.downloaded_bytes or 0,
        )

        # 6. Complete Job
        update_download_progress(
            job_id=job_id,
            status="completed",
            progress=100.0,
            downloaded_bytes=download_result.downloaded_bytes,
            output_file_path=final_file,
            thumbnail_path=thumb_path,
        )

        completed_job = get_download_by_id(job_id) or {"id": job_id, "status": "completed"}
        await self.broadcast_event("JOB_PROGRESS", {
            "progress": {
                "id": job_id,
                "status": "completed",
                "progress": 100.0,
                "downloadedBytes": download_result.downloaded_bytes,
                "speed": None,
                "eta": None,
                "resolveImported": bool(completed_job.get("resolve_imported")),
                "premiereImported": bool(completed_job.get("premiere_imported")),
                "aftereffectsImported": bool(completed_job.get("aftereffects_imported")),
                "auditionImported": bool(completed_job.get("audition_imported")),
            }
        })
        await self.broadcast_event("JOB_COMPLETED", {
            "job": completed_job,
            "imports": import_summary,
        })
        downloads_logger.info(f"Job {job_id} successfully completed. File: {final_file}")

    async def import_existing_to_editor(
        self, job_id: str, editor: str, bin_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """User-triggered import of an already downloaded file into one editor.

        Refuses up front, with an explanation, when the editor cannot receive imports
        instead of pretending the import happened.
        """
        job = get_download_by_id(job_id)
        if not job or not job.get("output_file_path"):
            return {"success": False, "error": "Job file does not exist.", "editor": editor}

        file_path = job["output_file_path"]
        if not os.path.isfile(file_path):
            return {
                "success": False,
                "error": f"File no longer exists at: {file_path}",
                "editor": editor,
            }

        settings = self._get_settings()
        target_bin = bin_name or self._stored_bin(job, editor) or self._settings_bin(settings, editor)

        if not self.editor_available(editor):
            hint = (
                "Start DaVinci Resolve and try again."
                if editor == "resolve"
                else f"Open Window > Extensions > Xdrop in {EDITOR_LABELS[editor]} and try again."
            )
            return {
                "success": False,
                "error": f"{EDITOR_LABELS[editor]} is not ready to receive imports. {hint}",
                "editor": editor,
            }

        outcome = await self.attempt_import(job_id, editor, file_path, target_bin)
        await self.broadcast_import_state(job_id, editor)

        if not outcome.get("success"):
            return {
                "success": False,
                "error": outcome.get("error"),
                "editor": editor,
                "targetBin": target_bin,
            }

        return {
            "success": True,
            "confirmed": bool(outcome.get("confirmed")),
            "editor": editor,
            "targetBin": target_bin,
            "clipName": outcome.get("clipName"),
            "requestId": outcome.get("requestId"),
        }

    async def import_existing_to_resolve(self, job_id: str) -> Dict[str, Any]:
        """Manually triggers DaVinci Resolve import for a previously downloaded job."""
        return await self.import_existing_to_editor(job_id, "resolve")

    async def import_existing_to_premiere(self, job_id: str, bin_name: Optional[str] = None) -> Dict[str, Any]:
        """Manually triggers Adobe Premiere Pro import for a previously downloaded job."""
        return await self.import_existing_to_editor(job_id, "premiere", bin_name)

    async def import_existing_to_aftereffects(self, job_id: str, bin_name: Optional[str] = None) -> Dict[str, Any]:
        """Manually triggers Adobe After Effects import for a previously downloaded job."""
        return await self.import_existing_to_editor(job_id, "aftereffects", bin_name)

    async def import_existing_to_audition(self, job_id: str, bin_name: Optional[str] = None) -> Dict[str, Any]:
        """Manually triggers Adobe Audition import for a previously downloaded job."""
        return await self.import_existing_to_editor(job_id, "audition", bin_name)

_queue_manager_instance: Optional[DownloadQueueManager] = None

def get_queue_manager() -> DownloadQueueManager:
    global _queue_manager_instance
    if _queue_manager_instance is None:
        _queue_manager_instance = DownloadQueueManager()
    return _queue_manager_instance
