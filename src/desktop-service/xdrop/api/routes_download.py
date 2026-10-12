from typing import List, Optional
from fastapi import APIRouter, HTTPException
from xdrop.download_queue import get_queue_manager, CreateDownloadRequest
from xdrop.database import get_all_downloads, get_download_by_id

router = APIRouter(tags=["Downloads"])


@router.post("/api/downloads", status_code=201)
@router.post("/api/download", status_code=201)
async def create_download_job(req: CreateDownloadRequest):
    """Enqueues a new media download job."""
    qm = get_queue_manager()
    job = await qm.add_download(req)
    return job


@router.get("/api/downloads")
@router.get("/api/queue")
async def list_download_jobs():
    """Lists all active, completed, or failed download jobs."""
    return get_all_downloads()


@router.get("/api/downloads/{job_id}")
@router.get("/api/queue/{job_id}")
async def get_download_job(job_id: str):
    """Retrieves status and details for a specific download job."""
    job = get_download_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Download job not found.")
    return job


@router.post("/api/downloads/{job_id}/cancel")
@router.post("/api/download/{job_id}/cancel")
async def cancel_download_job(job_id: str):
    """Cancels an active or queued download job."""
    qm = get_queue_manager()
    job = get_download_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Download job not found.")
    await qm.cancel_job(job_id)
    return {"success": True, "message": "Job cancelled."}


@router.post("/api/downloads/{job_id}/retry")
@router.post("/api/download/{job_id}/retry")
async def retry_download_job(job_id: str):
    """Retries a failed or cancelled download job."""
    qm = get_queue_manager()
    job = await qm.retry_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Download job not found.")
    return job


@router.delete("/api/downloads/{job_id}")
@router.delete("/api/download/{job_id}")
async def remove_download_job(job_id: str):
    """Removes a download job from queue history."""
    qm = get_queue_manager()
    await qm.remove_job(job_id)
    return {"success": True, "message": "Job removed."}


@router.post("/api/downloads/{job_id}/import")
@router.post("/api/download/{job_id}/import")
async def trigger_resolve_import(job_id: str):
    """Triggers import into DaVinci Resolve for a completed download."""
    qm = get_queue_manager()
    res = await qm.import_existing_to_resolve(job_id)
    return res


@router.post("/api/downloads/{job_id}/import-premiere")
@router.post("/api/download/{job_id}/import-premiere")
async def trigger_premiere_import(job_id: str):
    """Triggers import into Adobe Premiere Pro for a completed download."""
    qm = get_queue_manager()
    res = await qm.import_existing_to_premiere(job_id)
    return res


@router.post("/api/downloads/{job_id}/import-aftereffects")
@router.post("/api/download/{job_id}/import-aftereffects")
async def trigger_aftereffects_import(job_id: str):
    """Triggers import into Adobe After Effects for a completed download."""
    qm = get_queue_manager()
    res = await qm.import_existing_to_aftereffects(job_id)
    return res


@router.post("/api/downloads/{job_id}/import-audition")
@router.post("/api/download/{job_id}/import-audition")
async def trigger_audition_import(job_id: str):
    """Triggers import into Adobe Audition for a completed download."""
    qm = get_queue_manager()
    res = await qm.import_existing_to_audition(job_id)
    return res
