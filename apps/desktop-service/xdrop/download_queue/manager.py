import asyncio
import os
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable, Set
from datetime import datetime, timezone

from xdrop.download_queue.models import CreateDownloadRequest
from xdrop.database import (
    insert_download,
    update_download_progress,
    update_download_status,
    get_download_by_id,
    get_all_downloads,
    delete_download,
    insert_library_item,
    get_settings_from_db,
)
from xdrop.providers import get_provider_manager
from xdrop.processor import get_ffmpeg_processor, MediaOrganizer, sanitize_filename_py
from xdrop.resolve import get_resolve_bridge
from xdrop.config import AppSettingsModel, DATA_DIR, PROXIES_DIR
from xdrop.logger import downloads_logger, errors_logger

class DownloadQueueManager:
    """Orchestrates asynchronous download queue, processing, and DaVinci Resolve imports."""

    def __init__(self):
        self._queue: asyncio.Queue = asyncio.Queue()
        self._active_tasks: Dict[str, asyncio.Task] = {}
        self._cancelled_jobs: Set[str] = set()
        self._subscribers: List[Callable[[Dict[str, Any]], Any]] = []
        self._workers: List[asyncio.Task] = []
        self._running = False

    def subscribe(self, callback: Callable[[Dict[str, Any]], Any]) -> None:
        """Subscribes a listener (e.g. WebSocket broadcaster) to queue events."""
        if callback not in self._subscribers:
            self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[Dict[str, Any]], Any]) -> None:
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    async def broadcast_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Broadcasts event to all active WebSocket listeners."""
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
        downloads_logger.info(f"DownloadQueueManager started with {worker_count} workers.")

    async def stop(self) -> None:
        self._running = False
        for task in self._workers:
            task.cancel()
        self._workers.clear()

    def _get_settings(self) -> AppSettingsModel:
        db_settings = get_settings_from_db()
        return AppSettingsModel(**db_settings)

    async def add_download(self, req: CreateDownloadRequest) -> Dict[str, Any]:
        """Creates a download job and places it in the processing queue."""
        job_id = f"dl_{uuid.uuid4().hex[:10]}"
        pm = get_provider_manager()
        provider = pm.find_provider_for_url(req.source_url)
        platform_id = provider.platform_id if provider else "generic"

        title = req.title or "Media Asset"
        now = datetime.now(timezone.utc).isoformat()

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
            }
        })

        # Audio extraction if requested
        if req.extract_audio_only or "audio" in req.asset_id.lower():
            audio_out = Path(final_file).with_suffix(f".{req.format or 'wav'}")
            if final_file != str(audio_out):
                success, audio_err = await loop.run_in_executor(
                    None,
                    lambda: ffmpeg.extract_audio(final_file, str(audio_out), req.format or "wav")
                )
                if success:
                    final_file = str(audio_out)

        # Video format transcoding if requested (e.g. ProRes MOV or Universal MP4)
        target_vfmt = req.transcode_video_format or (settings.preferred_video_format if settings.preferred_video_format != "original" else None)
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
                        final_file = str(trans_out)

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

        # 5. Multi-Editor Import Automation (DaVinci Resolve, Adobe Premiere Pro & Adobe After Effects)
        from xdrop.premiere import get_premiere_bridge
        from xdrop.aftereffects import get_aftereffects_bridge
        prem_bridge = get_premiere_bridge()
        ae_bridge = get_aftereffects_bridge()

        target_ed = req.target_editor or getattr(settings, "default_editor", "auto")
        resolve_imported = False
        premiere_imported = False
        aftereffects_imported = False
        clip_name = None

        # Check if should import to Premiere Pro
        should_import_premiere = (
            target_ed in ("premiere", "auto")
            and (req.auto_import_to_premiere if req.auto_import_to_premiere is not None else True)
            and prem_bridge.is_running()
        )

        # Check if should import to DaVinci Resolve
        should_import_resolve = (
            target_ed in ("resolve", "auto")
            and (req.auto_import_to_resolve if req.auto_import_to_resolve is not None else settings.auto_import_to_resolve)
            and bridge.is_running()
        )

        # Check if should import to Adobe After Effects
        should_import_aftereffects = (
            target_ed in ("aftereffects", "auto")
            and (req.auto_import_to_aftereffects if req.auto_import_to_aftereffects is not None else getattr(settings, "auto_import_to_aftereffects", True))
            and ae_bridge.is_running()
        )

        if should_import_premiere or should_import_resolve or should_import_aftereffects:
            update_download_status(job_id, "importing")
            await self.broadcast_event("JOB_PROGRESS", {
                "progress": {
                    "id": job_id,
                    "status": "importing",
                    "progress": 95.0,
                    "downloadedBytes": download_result.downloaded_bytes,
                }
            })

            # Premiere Pro Import
            if should_import_premiere:
                prem_bin = req.target_premiere_bin or "Xdrop"
                p_res = await prem_bridge.import_media([final_file], prem_bin)
                if p_res.get("success"):
                    premiere_imported = True
                    clip_name = Path(final_file).name
                    downloads_logger.info(f"Broadcasted import of {final_file} to Premiere bin '{prem_bin}'")

            # After Effects Import
            if should_import_aftereffects:
                ae_bin = req.target_aftereffects_bin or getattr(settings, "target_aftereffects_bin", "Xdrop")
                ae_res = await ae_bridge.import_media([final_file], ae_bin)
                if ae_res.get("success"):
                    aftereffects_imported = True
                    clip_name = Path(final_file).name
                    downloads_logger.info(f"Broadcasted import of {final_file} to After Effects bin '{ae_bin}'")

            # DaVinci Resolve Import
            if should_import_resolve:
                target_bin = req.target_media_pool_bin or settings.target_media_pool_bin or "Xdrop"
                import_res = await loop.run_in_executor(
                    None,
                    lambda: bridge.import_media([final_file], target_bin)
                )
                if import_res.get("success"):
                    resolve_imported = True
                    clip_name = import_res.get("clipName") or Path(final_file).name
                    downloads_logger.info(f"Successfully imported {final_file} to Resolve bin '{target_bin}'")
                else:
                    downloads_logger.warning(
                        f"Resolve import deferred for {final_file}: {import_res.get('error')}"
                    )

        # 6. Complete Job
        update_download_progress(
            job_id=job_id,
            status="completed",
            progress=100.0,
            downloaded_bytes=download_result.downloaded_bytes,
            output_file_path=final_file,
            thumbnail_path=thumb_path,
            resolve_imported=resolve_imported,
            resolve_clip_name=clip_name,
            premiere_imported=premiere_imported,
            premiere_bin=req.target_premiere_bin or "Xdrop" if premiere_imported else None,
            aftereffects_imported=aftereffects_imported,
            aftereffects_bin=req.target_aftereffects_bin or "Xdrop" if aftereffects_imported else None,
        )

        completed_job = get_download_by_id(job_id)
        await self.broadcast_event("JOB_COMPLETED", {
            "job": completed_job or {"id": job_id, "status": "completed"}
        })
        downloads_logger.info(f"Job {job_id} successfully completed. File: {final_file}")

    async def import_existing_to_resolve(self, job_id: str) -> Dict[str, Any]:
        """Manually triggers DaVinci Resolve import for a previously downloaded job."""
        job = get_download_by_id(job_id)
        if not job or not job.get("output_file_path"):
            return {"success": False, "error": "Job file does not exist."}

        file_path = job["output_file_path"]
        if not os.path.isfile(file_path):
            return {"success": False, "error": f"File no longer exists at: {file_path}"}

        settings = self._get_settings()
        bridge = get_resolve_bridge()
        target_bin = settings.target_media_pool_bin or "Xdrop"

        loop = asyncio.get_running_loop()
        res = await loop.run_in_executor(
            None,
            lambda: bridge.import_media([file_path], target_bin)
        )

        if res.get("success"):
            update_download_progress(
                job_id=job_id,
                status=job["status"],
                progress=job.get("progress", 100.0),
                downloaded_bytes=job.get("downloaded_bytes", 0),
                resolve_imported=True,
                resolve_clip_name=res.get("clipName")
            )
            await self.broadcast_event("JOB_UPDATED", {
                "jobId": job_id,
                "progress": {
                    "id": job_id,
                    "status": job["status"],
                    "progress": 100.0,
                    "downloadedBytes": job.get("downloaded_bytes", 0),
                    "resolveImported": True,
                }
            })

        return res

    async def import_existing_to_premiere(self, job_id: str, bin_name: Optional[str] = None) -> Dict[str, Any]:
        """Manually triggers Adobe Premiere Pro import for a previously downloaded job."""
        job = get_download_by_id(job_id)
        if not job or not job.get("output_file_path"):
            return {"success": False, "error": "Job file does not exist."}

        file_path = job["output_file_path"]
        if not os.path.isfile(file_path):
            return {"success": False, "error": f"File no longer exists at: {file_path}"}

        from xdrop.premiere import get_premiere_bridge
        prem_bridge = get_premiere_bridge()
        target_bin = bin_name or "Xdrop"
        res = await prem_bridge.import_media([file_path], target_bin)

        if res.get("success"):
            final_p = (res.get("filePaths") or [file_path])[0]
            update_download_progress(
                job_id=job_id,
                status=job["status"],
                progress=job.get("progress", 100.0),
                downloaded_bytes=job.get("downloaded_bytes", 0),
                output_file_path=final_p,
                premiere_imported=True,
                premiere_bin=target_bin
            )
            await self.broadcast_event("JOB_UPDATED", {
                "jobId": job_id,
                "progress": {
                    "id": job_id,
                    "status": job["status"],
                    "progress": 100.0,
                    "downloadedBytes": job.get("downloaded_bytes", 0),
                    "premiereImported": True,
                }
            })

        return res

    async def import_existing_to_aftereffects(self, job_id: str, bin_name: Optional[str] = None) -> Dict[str, Any]:
        """Manually triggers Adobe After Effects import for a previously downloaded job."""
        job = get_download_by_id(job_id)
        if not job or not job.get("output_file_path"):
            return {"success": False, "error": "Job file does not exist."}

        file_path = job["output_file_path"]
        if not os.path.isfile(file_path):
            return {"success": False, "error": f"File no longer exists at: {file_path}"}

        from xdrop.aftereffects import get_aftereffects_bridge
        ae_bridge = get_aftereffects_bridge()
        target_bin = bin_name or "Xdrop"
        res = await ae_bridge.import_media([file_path], target_bin)

        if res.get("success"):
            final_p = (res.get("filePaths") or [file_path])[0]
            update_download_progress(
                job_id=job_id,
                status=job["status"],
                progress=job.get("progress", 100.0),
                downloaded_bytes=job.get("downloaded_bytes", 0),
                output_file_path=final_p,
                aftereffects_imported=True,
                aftereffects_bin=target_bin
            )
            await self.broadcast_event("JOB_UPDATED", {
                "jobId": job_id,
                "progress": {
                    "id": job_id,
                    "status": job["status"],
                    "progress": 100.0,
                    "downloadedBytes": job.get("downloaded_bytes", 0),
                    "aftereffectsImported": True,
                }
            })

        return res

_queue_manager_instance: Optional[DownloadQueueManager] = None

def get_queue_manager() -> DownloadQueueManager:
    global _queue_manager_instance
    if _queue_manager_instance is None:
        _queue_manager_instance = DownloadQueueManager()
    return _queue_manager_instance
