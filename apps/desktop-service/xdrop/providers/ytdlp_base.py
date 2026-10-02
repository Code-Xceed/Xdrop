import os
import re
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
import yt_dlp
from xdrop.providers.base import PlatformProvider, MediaInfoModel, MediaAssetModel, DownloadResult
from xdrop.config import discover_ffmpeg, THUMBNAILS_DIR
from xdrop.processor.organizer import sanitize_filename_py
from xdrop.logger import app_logger, errors_logger

class YtDlpBaseProvider(PlatformProvider):
    """Base provider utilizing yt-dlp for permitted public platform media extraction."""

    def _get_ydl_opts(self, extra_opts: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        ffmpeg_bin = discover_ffmpeg()
        node_bin = shutil.which("node")
        opts: Dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "nocheckcertificate": False,
            "prefer_ffmpeg": True,
            "ffmpeg_location": str(Path(ffmpeg_bin).parent) if ffmpeg_bin and Path(ffmpeg_bin).is_file() else None,
            "socket_timeout": 30,
            # Strict safety & public content settings
            "geo_bypass": False,
            "extract_flat": False,
            "retries": 3,
        }
        if node_bin:
            opts["js_runtimes"] = {"node": {"path": node_bin}}
        if extra_opts:
            opts.update(extra_opts)
        return opts

    def inspect(self, url: str) -> MediaInfoModel:
        ydl_opts = self._get_ydl_opts()
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if not info:
                    raise ValueError("No metadata returned by extractor.")

                title = info.get("title") or "Unknown Title"
                uploader = info.get("uploader") or info.get("channel") or info.get("creator")
                duration = info.get("duration")
                thumb = info.get("thumbnail")
                source_id = info.get("id") or url

                assets = self._extract_assets(info)

                return MediaInfoModel(
                    url=url,
                    platform=self.platform_id,
                    platform_name=self.platform_name,
                    title=title,
                    author=uploader,
                    author_url=info.get("uploader_url") or info.get("channel_url"),
                    source_id=str(source_id),
                    duration=float(duration) if duration else None,
                    thumbnail_url=thumb,
                    description=info.get("description", "")[:300] if info.get("description") else None,
                    assets=assets
                )
        except Exception as e:
            msg = str(e)
            errors_logger.error(f"Failed to inspect media for {url}: {msg}")
            # Clean human-readable error
            if "private video" in msg.lower():
                raise ValueError("This media is private and cannot be imported.")
            elif "drm" in msg.lower() or "copyright" in msg.lower():
                raise ValueError("This media is protected and cannot be imported.")
            raise ValueError(f"Could not inspect media: {msg}")

    def _extract_assets(self, info: Dict[str, Any]) -> List[MediaAssetModel]:
        raw_formats = info.get("formats", [])
        assets: List[MediaAssetModel] = []
        seen_qualities = set()

        # 1. Best Combined / Standard video qualities
        # Look for video formats with height info (1080, 720, 480, etc.)
        for f in reversed(raw_formats):
            vcodec = f.get("vcodec", "none")
            acodec = f.get("acodec", "none")
            height = f.get("height")
            if vcodec != "none" and height and height >= 360:
                q_label = f"{height}p"
                fps = f.get("fps")
                if fps and fps >= 50:
                    q_label += f"{int(fps)}"

                if q_label not in seen_qualities:
                    seen_qualities.add(q_label)
                    assets.append(MediaAssetModel(
                        id=f"video_{q_label}_{f.get('format_id')}",
                        media_type="video",
                        format=f.get("ext", "mp4"),
                        quality_label=f"Video ({q_label})",
                        resolution=f"{f.get('width', '')}x{height}",
                        fps=int(fps) if fps else None,
                        vcodec=vcodec,
                        acodec=acodec if acodec != "none" else "aac",
                        filesize_approx=f.get("filesize") or f.get("filesize_approx"),
                        is_default=(height in (1080, 720) and "default_video" not in seen_qualities)
                    ))
                    if height in (1080, 720):
                        seen_qualities.add("default_video")

        # Ensure at least one standard video asset if none above
        if not assets:
            assets.append(MediaAssetModel(
                id="best_video",
                media_type="video",
                format="mp4",
                quality_label="Best Available Video",
                is_default=True
            ))

        # 2. Add Audio Extraction asset
        assets.append(MediaAssetModel(
            id="audio_best",
            media_type="audio",
            format="wav",
            quality_label="Audio Only (High Quality WAV)",
            is_default=False
        ))
        assets.append(MediaAssetModel(
            id="audio_mp3",
            media_type="audio",
            format="mp3",
            quality_label="Audio Only (MP3)",
            is_default=False
        ))

        # 3. Add Thumbnail asset if available
        if info.get("thumbnail"):
            assets.append(MediaAssetModel(
                id="thumbnail_image",
                media_type="image",
                format="jpg",
                quality_label="High-Res Thumbnail",
                url=info.get("thumbnail"),
                is_default=False
            ))

        return assets

    def download(
        self,
        url: str,
        asset_id: str,
        output_template: str,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> DownloadResult:
        """Downloads the selected asset using yt-dlp with real progress hook."""
        dest_path = Path(output_template).resolve()
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        ffmpeg_bin = discover_ffmpeg()

        is_audio = "audio" in asset_id.lower() or dest_path.suffix.lower() in (".wav", ".mp3", ".aac")
        is_thumb = "thumb" in asset_id.lower()

        # Handle direct thumbnail download
        if is_thumb:
            try:
                import httpx
                info = self.inspect(url)
                if info.thumbnail_url:
                    with httpx.Client(timeout=20.0, follow_redirects=True) as client:
                        resp = client.get(info.thumbnail_url)
                        if resp.status_code == 200:
                            dest_path.write_bytes(resp.content)
                            return DownloadResult(
                                success=True,
                                output_file_path=str(dest_path),
                                downloaded_bytes=len(resp.content)
                            )
            except Exception as e:
                return DownloadResult(success=False, error_message=f"Thumbnail download failed: {e}")

        def ydl_progress_hook(d: Dict[str, Any]):
            if not progress_callback:
                return
            status = d.get("status")
            if status == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                downloaded = d.get("downloaded_bytes") or 0
                percent = (downloaded / total * 100.0) if total > 0 else 0.0
                speed_raw = d.get("speed")
                speed_str = f"{(speed_raw / (1024 * 1024)):.1f} MB/s" if speed_raw else None
                eta_raw = d.get("eta")
                eta_str = f"{int(eta_raw // 60):02d}:{int(eta_raw % 60):02d}" if eta_raw is not None else None

                progress_callback({
                    "status": "downloading",
                    "progress": round(percent, 1),
                    "downloaded_bytes": downloaded,
                    "total_bytes": total if total > 0 else None,
                    "speed": speed_str,
                    "eta": eta_str
                })
            elif status == "finished":
                progress_callback({
                    "status": "processing",
                    "progress": 99.0,
                    "downloaded_bytes": d.get("downloaded_bytes", 0),
                    "speed": None,
                    "eta": None
                })

        ydl_opts = self._get_ydl_opts({
            "outtmpl": str(dest_path.with_suffix("").as_posix()) + ".%(ext)s",
            "progress_hooks": [ydl_progress_hook],
        })

        if is_audio:
            fmt = "wav" if "wav" in asset_id.lower() or dest_path.suffix == ".wav" else "mp3"
            ydl_opts.update({
                "format": "bestaudio/best",
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": fmt,
                    "preferredquality": "0",
                }]
            })
        else:
            # Format selection: extract format_id from asset_id if available.
            # Prioritize native H.264 (avc1) video and AAC (mp4a) audio for 100% native NLE compatibility
            # in Adobe Premiere Pro and DaVinci Resolve, with fallback to best available.
            format_spec = "bestvideo[vcodec^=avc1]+bestaudio[acodec^=mp4a]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"
            parts = asset_id.split("_", 2)
            if len(parts) >= 3 and parts[2]:
                fmt_id = parts[2]
                format_spec = f"{fmt_id}+bestaudio[acodec^=mp4a]/{fmt_id}+bestaudio/bestvideo+bestaudio/best"
            ydl_opts.update({
                "format": format_spec,
                "merge_output_format": "mp4"
            })

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            # Locate downloaded file (extension might be resolved by yt-dlp)
            actual_file = dest_path
            if not actual_file.exists():
                # Check for possible actual file with matching stem
                candidates = list(dest_path.parent.glob(f"{dest_path.stem}.*"))
                if candidates:
                    actual_file = candidates[0]

            if actual_file.exists() and actual_file.stat().st_size > 0:
                return DownloadResult(
                    success=True,
                    output_file_path=str(actual_file),
                    downloaded_bytes=actual_file.stat().st_size
                )
            else:
                return DownloadResult(
                    success=False,
                    error_message="Downloaded file was not created or has 0 bytes."
                )

        except Exception as e:
            errors_logger.error(f"Download exception for {url}: {e}", exc_info=True)
            return DownloadResult(
                success=False,
                error_message=f"Download failed: {str(e)}"
            )
