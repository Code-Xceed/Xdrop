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

@router.get("/thumbnail-proxy")
async def proxy_thumbnail(url: str):
    """Proxies an external thumbnail image to bypass strict CDN Referer or CORS restrictions."""
    url_clean = url.strip()
    if not (url_clean.startswith("http://") or url_clean.startswith("https://")):
        raise HTTPException(status_code=400, detail="Invalid thumbnail URL.")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
    }
    try:
        import httpx
        from fastapi.responses import Response
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(url_clean, headers=headers)
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail="Failed to fetch upstream thumbnail.")
            content_type = resp.headers.get("content-type", "image/jpeg")
            return Response(
                content=resp.content,
                media_type=content_type,
                headers={"Cache-Control": "public, max-age=86400"}
            )
    except HTTPException:
        raise
    except Exception as e:
        app_logger.warning(f"Failed to proxy thumbnail {url_clean}: {e}")
        raise HTTPException(status_code=502, detail=f"Proxy error: {str(e)}")
