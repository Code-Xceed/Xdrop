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

                # If entry list present (e.g. carousels or playlists), inspect first entry
                if "entries" in info and info.get("entries"):
                    entries = list(info.get("entries") or [])
                    if entries and entries[0]:
                        first_entry = entries[0]
                        if not thumb:
                            thumb = first_entry.get("thumbnail")
                        if not title or title == "Unknown Title":
                            title = first_entry.get("title") or title
                        if not duration:
                            duration = first_entry.get("duration")

                # If thumbnail still missing, check thumbnails list (last or highest resolution)
                if not thumb and info.get("thumbnails"):
                    thumbs = info.get("thumbnails")
                    if isinstance(thumbs, list):
                        for t in reversed(thumbs):
                            if isinstance(t, dict) and t.get("url"):
                                thumb = t["url"]
                                break

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

        # 1. Best Combined / Standard video qualities sorted descending by resolution
        valid_video_formats = [
            f for f in raw_formats
            if f.get("vcodec", "none") != "none" and (f.get("height") or f.get("width"))
        ]
        valid_video_formats.sort(
            key=lambda f: (f.get("height") or 0, f.get("width") or 0, f.get("fps") or 0),
            reverse=True
        )

        for f in valid_video_formats:
            vcodec = f.get("vcodec", "none")
            acodec = f.get("acodec", "none")
            height = f.get("height") or 0
            width = f.get("width") or 0
            fps = f.get("fps")

            eff_res = min(width, height) if (width > 0 and height > 0) else (height or width)
            if eff_res < 360 and height < 360:
                continue

            fps_suffix = f"{int(fps)}" if fps and fps >= 50 else ""
            if eff_res >= 2160 or height >= 2160:
                tier = "4K Ultra HD"
                res_key = f"2160p{fps_suffix}"
            elif eff_res >= 1440 or height >= 1440:
                tier = "2K Quad HD"
                res_key = f"1440p{fps_suffix}"
            elif eff_res >= 1080 or height >= 1080:
                tier = "Full HD"
                res_key = f"1080p{fps_suffix}"
            elif eff_res >= 720 or height >= 720:
                tier = "HD"
                res_key = f"720p{fps_suffix}"
            elif eff_res >= 480 or height >= 480:
                tier = "SD"
                res_key = f"480p{fps_suffix}"
            else:
                tier = "Basic"
                res_key = f"360p{fps_suffix}"

            if res_key not in seen_qualities:
                seen_qualities.add(res_key)
                is_default_candidate = (res_key.startswith("1080p") or res_key.startswith("720p")) and "default_video" not in seen_qualities
                assets.append(MediaAssetModel(
                    id=f"video_{res_key}_{f.get('format_id')}",
                    media_type="video",
                    format=f.get("ext", "mp4"),
                    quality_label=f"{tier} ({height or eff_res}p{fps_suffix})",
                    resolution=f"{width}x{height}" if width and height else None,
                    fps=int(fps) if fps else None,
                    vcodec=vcodec,
                    acodec=acodec if acodec != "none" else "aac",
                    filesize_approx=f.get("filesize") or f.get("filesize_approx"),
                    is_default=is_default_candidate
                ))
                if is_default_candidate:
                    seen_qualities.add("default_video")

        # Ensure at least one standard video asset if none above
        if not assets:
            assets.append(MediaAssetModel(
                id="best_video",
                media_type="video",
                format="mp4",
                quality_label="Best Available Video (MP4)",
                is_default=True
            ))
        elif "default_video" not in seen_qualities and assets:
            assets[0].is_default = True

        # Master editing video (ProRes 422 MOV)
        assets.append(MediaAssetModel(
            id="video_prores_mov",
            media_type="video",
            format="mov",
            quality_label="ProRes 422 (MOV Master)",
            is_default=False
        ))

        # 2. Comprehensive Audio Extraction formats
        assets.append(MediaAssetModel(
            id="audio_wav",
            media_type="audio",
            format="wav",
            quality_label="Broadcast WAV (48kHz)",
            is_default=False
        ))
        assets.append(MediaAssetModel(
            id="audio_mp3",
            media_type="audio",
            format="mp3",
            quality_label="MP3 (320kbps)",
            is_default=False
        ))
        assets.append(MediaAssetModel(
            id="audio_aac",
            media_type="audio",
            format="m4a",
            quality_label="AAC / M4A (320kbps)",
            is_default=False
        ))

        # 3. Add Thumbnail asset if available
        if info.get("thumbnail"):
            assets.append(MediaAssetModel(
                id="thumbnail_image",
                media_type="image",
                format="jpg",
                quality_label="Thumbnail Image (JPG)",
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
            if "wav" in asset_id.lower() or dest_path.suffix.lower() == ".wav":
                fmt = "wav"
                qual = "0"
            elif "aac" in asset_id.lower() or "m4a" in asset_id.lower() or dest_path.suffix.lower() in (".aac", ".m4a"):
                fmt = "m4a"
                qual = "0"
            else:
                fmt = "mp3"
                qual = "320"

            ydl_opts.update({
                "format": "bestaudio/best",
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": fmt,
                    "preferredquality": qual,
                }]
            })
        else:
            # Format selection: extract format_id from asset_id if available.
            # Prioritize native H.264 (avc1) video and AAC (mp4a) audio for 100% native NLE compatibility
            # in Adobe Premiere Pro and DaVinci Resolve, with fallback to best available.
            format_spec = "bestvideo[vcodec^=avc1]+bestaudio[acodec^=mp4a]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"
            parts = asset_id.split("_", 2)
            if len(parts) >= 3 and parts[2] and not parts[2].startswith("mov"):
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
