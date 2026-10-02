from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from xdrop.providers import get_provider_manager, MediaInfoModel
from xdrop.logger import app_logger

router = APIRouter(prefix="/api/analyze", tags=["Analyze"])

class AnalyzeRequest(BaseModel):
    url: str

class BatchAnalyzeRequest(BaseModel):
    urls: List[str]

@router.post("", response_model=MediaInfoModel)
async def analyze_url(req: AnalyzeRequest):
    """Analyzes a public media URL and retrieves platform metadata and available assets."""
    url = req.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL must not be empty.")

    pm = get_provider_manager()
    provider = pm.find_provider_for_url(url)
    if not provider:
        raise HTTPException(
            status_code=400,
            detail="Unsupported URL: No platform provider can handle this URL format."
        )

    try:
        # Provider inspection
        import asyncio
        loop = asyncio.get_running_loop()
        media_info = await loop.run_in_executor(None, lambda: pm.inspect_url(url))
        return media_info
    except ValueError as ve:
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception as e:
        app_logger.error(f"Error inspecting URL {url}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to inspect media from {provider.platform_name}: {str(e)}"
        )

@router.post("/batch")
async def analyze_batch_urls(req: BatchAnalyzeRequest):
    """Detects platforms for a batch of URLs without performing heavy stream queries."""
    pm = get_provider_manager()
    results = []

    for u in req.urls:
        url_clean = u.strip()
        if not url_clean:
            continue
        provider = pm.find_provider_for_url(url_clean)
        results.append({
            "url": url_clean,
            "supported": provider is not None,
            "platform": provider.platform_id if provider else "unknown",
            "platformName": provider.platform_name if provider else "Unsupported"
        })

    return {"detected": results, "total": len(results)}
