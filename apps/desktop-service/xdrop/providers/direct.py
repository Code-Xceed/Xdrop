import os
import re
from pathlib import Path
from typing import Dict, Any, Optional, Callable
import httpx
from xdrop.providers.base import PlatformProvider, MediaInfoModel, MediaAssetModel, DownloadResult
from xdrop.processor.organizer import sanitize_filename_py
from xdrop.logger import app_logger, errors_logger

DIRECT_EXTENSIONS = {
    ".mp4": ("video", "mp4"),
    ".mov": ("video", "mov"),
    ".mkv": ("video", "mkv"),
    ".webm": ("video", "webm"),
    ".mp3": ("audio", "mp3"),
    ".wav": ("audio", "wav"),
    ".aac": ("audio", "aac"),
    ".m4a": ("audio", "m4a"),
    ".jpg": ("image", "jpg"),
    ".jpeg": ("image", "jpeg"),
    ".png": ("image", "png"),
    ".webp": ("image", "webp"),
}

class DirectMediaProvider(PlatformProvider):
    """Provider for direct public HTTP/HTTPS media URLs (e.g. .mp4, .wav, .png)."""

    platform_id = "direct"
    platform_name = "Direct Media URL"

    def can_handle(self, url: str) -> bool:
        clean = url.split("?")[0].lower()
        return any(clean.endswith(ext) for ext in DIRECT_EXTENSIONS.keys())

    def inspect(self, url: str) -> MediaInfoModel:
        clean_url = url.split("?")[0]
        ext = Path(clean_url).suffix.lower()
        media_type, fmt = DIRECT_EXTENSIONS.get(ext, ("video", "mp4"))
        filename = Path(clean_url).name or "direct_media"
        title = sanitize_filename_py(Path(filename).stem, "direct_asset")

        approx_size = None
        try:
            with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                head = client.head(url)
                if head.status_code == 200:
                    cl = head.headers.get("content-length")
                    if cl and cl.isdigit():
                        approx_size = int(cl)
        except Exception:
            pass

        asset = MediaAssetModel(
            id="direct_original",
            media_type=media_type,
            format=fmt,
            quality_label="Original File",
            filesize_approx=approx_size,
            url=url,
            is_default=True
        )

        return MediaInfoModel(
            url=url,
            platform=self.platform_id,
            platform_name=self.platform_name,
            title=title,
            source_id=clean_url,
            thumbnail_url=url if media_type == "image" else None,
            assets=[asset]
        )

    def download(
        self,
        url: str,
        asset_id: str,
        output_template: str,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> DownloadResult:
        try:
            target_path = Path(output_template).resolve()
            target_path.parent.mkdir(parents=True, exist_ok=True)
            downloaded = 0

            with httpx.Client(timeout=60.0, follow_redirects=True) as client:
                with client.stream("GET", url) as response:
                    if response.status_code != 200:
                        return DownloadResult(
                            success=False,
                            error_message=f"HTTP download failed with status {response.status_code}"
                        )

                    total_bytes = int(response.headers.get("content-length", 0))
                    temp_file = target_path.with_suffix(f"{target_path.suffix}.tmp")

                    with open(temp_file, "wb") as f:
                        for chunk in response.iter_bytes(chunk_size=1024 * 128):
                            if not chunk:
                                continue
                            f.write(chunk)
                            downloaded += len(chunk)

                            if progress_callback:
                                percent = (downloaded / total_bytes * 100.0) if total_bytes > 0 else 50.0
                                progress_callback({
                                    "status": "downloading",
                                    "progress": round(percent, 1),
                                    "downloaded_bytes": downloaded,
                                    "total_bytes": total_bytes if total_bytes > 0 else None,
                                    "speed": None,
                                    "eta": None
                                })

                    if temp_file.exists():
                        if target_path.exists():
                            target_path.unlink()
                        temp_file.rename(target_path)

            return DownloadResult(
                success=True,
                output_file_path=str(target_path),
                downloaded_bytes=downloaded
            )
        except Exception as e:
            errors_logger.error(f"DirectMediaProvider download failed for {url}: {e}")
            return DownloadResult(
                success=False,
                error_message=f"Direct download error: {str(e)}"
            )
