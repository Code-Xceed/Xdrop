import os
import re
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, Callable
import httpx
from xdrop.providers.base import PlatformProvider, MediaInfoModel, MediaAssetModel, DownloadResult
from xdrop.processor.organizer import sanitize_filename_py
from xdrop.logger import app_logger, errors_logger

DIRECT_EXTENSIONS = {
    # Video
    ".mp4": ("video", "mp4"),
    ".mov": ("video", "mov"),
    ".mkv": ("video", "mkv"),
    ".webm": ("video", "webm"),
    ".m4v": ("video", "m4v"),
    ".avi": ("video", "avi"),
    ".flv": ("video", "flv"),
    # Audio
    ".wav": ("audio", "wav"),
    ".mp3": ("audio", "mp3"),
    ".m4a": ("audio", "m4a"),
    ".aac": ("audio", "aac"),
    ".flac": ("audio", "flac"),
    ".ogg": ("audio", "ogg"),
    ".aiff": ("audio", "aiff"),
    ".wma": ("audio", "wma"),
    # Image
    ".jpg": ("image", "jpg"),
    ".jpeg": ("image", "jpeg"),
    ".png": ("image", "png"),
    ".webp": ("image", "webp"),
    ".gif": ("image", "gif"),
}

class DirectMediaProvider(PlatformProvider):
    """Provider for direct public HTTP/HTTPS media URLs (e.g. .mp4, .wav, .png)."""

    platform_id = "direct"
    platform_name = "Direct Media URL"

    def can_handle(self, url: str) -> bool:
        clean = url.split("?")[0].split("#")[0].lower()
        return any(clean.endswith(ext) for ext in DIRECT_EXTENSIONS.keys())

    def inspect(self, url: str) -> MediaInfoModel:
        clean_url = url.split("?")[0].split("#")[0]
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

        assets = []
        if media_type == "video":
            assets.append(MediaAssetModel(
                id="direct_original_video",
                media_type="video",
                format=fmt,
                quality_label=f"Original Video ({fmt.upper()})",
                filesize_approx=approx_size,
                url=url,
                is_default=True
            ))
            assets.append(MediaAssetModel(
                id="direct_prores_mov",
                media_type="video",
                format="mov",
                quality_label="ProRes 422 Master",
                filesize_approx=approx_size,
                is_default=False
            ))
            assets.append(MediaAssetModel(
                id="direct_audio_wav",
                media_type="audio",
                format="wav",
                quality_label="Broadcast WAV (48kHz)",
                is_default=False
            ))
            assets.append(MediaAssetModel(
                id="direct_audio_mp3",
                media_type="audio",
                format="mp3",
                quality_label="MP3 (320kbps)",
                is_default=False
            ))
            assets.append(MediaAssetModel(
                id="direct_audio_aac",
                media_type="audio",
                format="m4a",
                quality_label="AAC / M4A (320kbps)",
                is_default=False
            ))
            assets.append(MediaAssetModel(
                id="direct_audio_flac",
                media_type="audio",
                format="flac",
                quality_label="Lossless FLAC",
                is_default=False
            ))
        elif media_type == "audio":
            assets.append(MediaAssetModel(
                id="direct_original_audio",
                media_type="audio",
                format=fmt,
                quality_label=f"Original Audio ({fmt.upper()})",
                filesize_approx=approx_size,
                url=url,
                is_default=True
            ))
            if fmt != "wav":
                assets.append(MediaAssetModel(
                    id="direct_audio_wav",
                    media_type="audio",
                    format="wav",
                    quality_label="Studio WAV (48kHz Uncompressed)",
                    is_default=False
                ))
            if fmt != "mp3":
                assets.append(MediaAssetModel(
                    id="direct_audio_mp3",
                    media_type="audio",
                    format="mp3",
                    quality_label="MP3 (320kbps High Quality)",
                    is_default=False
                ))
            if fmt not in ("m4a", "aac"):
                assets.append(MediaAssetModel(
                    id="direct_audio_aac",
                    media_type="audio",
                    format="m4a",
                    quality_label="AAC / M4A (320kbps)",
                    is_default=False
                ))
            if fmt != "flac":
                assets.append(MediaAssetModel(
                    id="direct_audio_flac",
                    media_type="audio",
                    format="flac",
                    quality_label="Lossless FLAC",
                    is_default=False
                ))
        else: # image
            assets.append(MediaAssetModel(
                id="direct_image",
                media_type="image",
                format=fmt,
                quality_label=f"Image ({fmt.upper()})",
                filesize_approx=approx_size,
                url=url,
                is_default=True
            ))

        return MediaInfoModel(
            url=url,
            platform=self.platform_id,
            platform_name=self.platform_name,
            title=title,
            source_id=clean_url,
            thumbnail_url=url if media_type == "image" else None,
            assets=assets
        )

    def download(
        self,
        url: str,
        asset_id: str,
        output_template: str,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> DownloadResult:
        try:
            import time
            target_path = Path(output_template).resolve()
            target_path.parent.mkdir(parents=True, exist_ok=True)

            clean_url = url.split("?")[0].split("#")[0].lower()
            source_ext = Path(clean_url).suffix
            # If target has a different extension than source URL (e.g. user selected audio extraction
            # or ProRes MOV conversion from a direct video), download to the source extension first
            # so the subsequent FFmpeg audio extraction or transcoding pipeline can process it properly.
            if source_ext in DIRECT_EXTENSIONS and target_path.suffix.lower() != source_ext:
                download_target = target_path.with_suffix(source_ext)
            else:
                download_target = target_path

            downloaded = 0
            start_time = time.time()
            last_cb_time = 0.0

            limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
            with httpx.Client(timeout=60.0, follow_redirects=True, limits=limits) as client:
                with client.stream("GET", url) as response:
                    if response.status_code != 200:
                        return DownloadResult(
                            success=False,
                            error_message=f"HTTP download failed with status {response.status_code}"
                        )

                    total_bytes = int(response.headers.get("content-length", 0))
                    temp_file = download_target.with_suffix(f".{uuid.uuid4().hex[:8]}.tmp")

                    # High-throughput 1MB buffer write loop with graceful cleanup
                    try:
                        with open(temp_file, "wb", buffering=1024 * 1024) as f:
                            for chunk in response.iter_bytes(chunk_size=1024 * 1024):
                                if not chunk:
                                    continue
                                f.write(chunk)
                                downloaded += len(chunk)
                                now = time.time()

                                # Compute real-time transfer speed & ETA
                                elapsed = now - start_time
                                speed_bps = (downloaded / elapsed) if elapsed > 0.1 else 0.0
                                speed_str = f"{(speed_bps / (1024 * 1024)):.1f} MB/s" if speed_bps > 0 else None

                                eta_str = None
                                if total_bytes > downloaded and speed_bps > 0:
                                    rem_sec = int((total_bytes - downloaded) / speed_bps)
                                    eta_str = f"{rem_sec // 60:02d}:{rem_sec % 60:02d}"

                                # Throttle callbacks to at most once per 200ms to preserve peak network I/O
                                if progress_callback and (now - last_cb_time >= 0.2 or (total_bytes > 0 and downloaded >= total_bytes)):
                                    last_cb_time = now
                                    percent = (downloaded / total_bytes * 100.0) if total_bytes > 0 else 50.0
                                    progress_callback({
                                        "status": "downloading",
                                        "progress": round(percent, 1),
                                        "downloaded_bytes": downloaded,
                                        "total_bytes": total_bytes if total_bytes > 0 else None,
                                        "speed": speed_str,
                                        "eta": eta_str
                                    })

                        if temp_file.exists():
                            os.replace(str(temp_file), str(download_target))
                    finally:
                        if temp_file.exists():
                            try:
                                temp_file.unlink(missing_ok=True)
                            except Exception:
                                pass

            return DownloadResult(
                success=True,
                output_file_path=str(download_target),
                downloaded_bytes=downloaded
            )
        except Exception as e:
            errors_logger.error(f"DirectMediaProvider download failed for {url}: {e}")
            return DownloadResult(
                success=False,
                error_message=f"Direct download error: {str(e)}"
            )
