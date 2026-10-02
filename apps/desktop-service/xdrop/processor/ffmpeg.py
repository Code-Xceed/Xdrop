import os
import subprocess
import json
import re
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from xdrop.config import discover_ffmpeg, THUMBNAILS_DIR
from xdrop.logger import app_logger, errors_logger

class FFmpegProcessor:
    """Safe wrapper around FFmpeg and FFprobe with structured error handling."""

    def __init__(self, ffmpeg_path: Optional[str] = None):
        self.ffmpeg_path = ffmpeg_path or discover_ffmpeg()

    def is_available(self) -> Tuple[bool, str]:
        """Checks if FFmpeg binary is operable and returns its version."""
        try:
            cmd = [self.ffmpeg_path, "-version"]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                timeout=5.0,
                shell=False
            )
            if result.returncode == 0:
                first_line = result.stdout.splitlines()[0] if result.stdout else "FFmpeg ready"
                return True, first_line
            return False, f"FFmpeg returned code {result.returncode}: {result.stderr.strip()}"
        except Exception as e:
            return False, f"FFmpeg not found or failed to execute: {str(e)}"

    def extract_thumbnail(
        self,
        input_video_path: str,
        output_image_path: Optional[str] = None,
        timestamp_sec: float = 1.0
    ) -> Optional[str]:
        """Extracts a frame thumbnail from video file."""
        inp = Path(input_video_path).resolve()
        if not inp.is_file():
            app_logger.warning(f"Input file for thumbnail does not exist: {inp}")
            return None

        if not output_image_path:
            out_name = f"thumb_{inp.stem}_{int(timestamp_sec)}.jpg"
            out_file = THUMBNAILS_DIR / out_name
        else:
            out_file = Path(output_image_path).resolve()

        out_file.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            self.ffmpeg_path,
            "-y",
            "-ss", str(max(0.0, timestamp_sec)),
            "-i", str(inp),
            "-vframes", "1",
            "-q:v", "2",
            "-vf", "scale=640:-1",
            str(out_file)
        ]

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=15.0, shell=False)
            if res.returncode == 0 and out_file.is_file():
                return str(out_file)
            else:
                errors_logger.error(f"FFmpeg thumbnail error: {res.stderr}")
                return None
        except Exception as e:
            errors_logger.error(f"Failed to generate thumbnail for {inp}: {e}")
            return None

    def extract_audio(
        self,
        input_file: str,
        output_file: str,
        audio_format: str = "wav"
    ) -> Tuple[bool, Optional[str]]:
        """Extracts audio track from media to WAV, MP3, or AAC."""
        inp = Path(input_file).resolve()
        outp = Path(output_file).resolve()
        outp.parent.mkdir(parents=True, exist_ok=True)

        fmt = audio_format.lower().replace(".", "")
        cmd = [self.ffmpeg_path, "-y", "-i", str(inp), "-vn"]

        if fmt == "wav":
            cmd.extend(["-c:a", "pcm_s16le", "-ar", "48000"])
        elif fmt == "mp3":
            cmd.extend(["-c:a", "libmp3lame", "-q:a", "0"])
        elif fmt == "aac" or fmt == "m4a":
            cmd.extend(["-c:a", "aac", "-b:a", "320k"])
        else:
            cmd.extend(["-c:a", "copy"])

        cmd.append(str(outp))

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=120.0, shell=False)
            if res.returncode == 0 and outp.is_file():
                return True, None
            return False, f"FFmpeg audio extraction failed: {res.stderr}"
        except Exception as e:
            return False, f"Audio extraction exception: {str(e)}"

    def convert_video_format(
        self,
        input_file: str,
        output_file: str,
        target_format: str = "mp4"
    ) -> Tuple[bool, Optional[str]]:
        """
        Converts video to editing-friendly format for DaVinci Resolve (H.264/AAC MP4 or ProRes MOV).
        If input is already compatible, remuxes without quality loss.
        """
        inp = Path(input_file).resolve()
        outp = Path(output_file).resolve()
        outp.parent.mkdir(parents=True, exist_ok=True)

        fmt = target_format.lower().replace(".", "")
        cmd = [self.ffmpeg_path, "-y", "-i", str(inp)]

        if fmt == "mov":
            # High compatibility ProRes for Resolve
            cmd.extend([
                "-c:v", "prores_ks",
                "-profile:v", "2", # ProRes Standard (422)
                "-c:a", "pcm_s16le",
                "-ar", "48000"
            ])
        else:
            # Universal MP4 (H.264 + AAC + faststart for instant playback in Resolve)
            cmd.extend([
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "18",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "192k",
                "-movflags", "+faststart"
            ])

        cmd.append(str(outp))

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=300.0, shell=False)
            if res.returncode == 0 and outp.is_file():
                return True, None
            return False, f"FFmpeg video conversion failed: {res.stderr}"
        except Exception as e:
            return False, f"Video conversion exception: {str(e)}"

    def generate_proxy(
        self,
        input_file: str,
        output_file: str,
        resolution: str = "720p"
    ) -> Tuple[bool, Optional[str]]:
        """Generates a low-overhead proxy file for smooth timeline editing."""
        inp = Path(input_file).resolve()
        outp = Path(output_file).resolve()
        outp.parent.mkdir(parents=True, exist_ok=True)

        scale_filter = "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2"
        if resolution == "540p":
            scale_filter = "scale=960:540:force_original_aspect_ratio=decrease,pad=960:540:(ow-iw)/2:(oh-ih)/2"

        cmd = [
            self.ffmpeg_path,
            "-y",
            "-i", str(inp),
            "-vf", scale_filter,
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "24",
            "-c:a", "aac",
            "-b:a", "128k",
            str(outp)
        ]

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=180.0, shell=False)
            if res.returncode == 0 and outp.is_file():
                return True, None
            return False, f"Proxy generation failed: {res.stderr}"
        except Exception as e:
            return False, f"Proxy generation exception: {str(e)}"

    def ensure_nle_compatible(
        self,
        file_path: str,
        target_format: str = "mp4"
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Ensures a media file's video and audio codecs are natively supported by
        professional NLEs (Adobe Premiere Pro & DaVinci Resolve).

        - Detects unsupported video codecs (AV1, VP9, VP8, Theora).
        - Detects unsupported audio codecs in MP4/MOV (Opus, Vorbis, FLAC).
        - If only audio is unsupported, stream-copies video (-c:v copy) and encodes audio to AAC in ~1s.
        - If video is unsupported, transcodes to standard H.264 (or ProRes MOV) + AAC.
        - If already compatible, returns immediately without processing.

        Returns: (success: bool, final_path: str, error: Optional[str])
        """
        inp = Path(file_path).resolve()
        if not inp.is_file():
            return False, file_path, f"File does not exist: {file_path}"

        ext = inp.suffix.lower()
        if ext not in (".mp4", ".mov", ".m4v", ".mkv", ".webm"):
            return True, str(inp), None

        info = self.probe_media_info(str(inp))
        vcodec = (info.get("vcodec") or "").lower()
        acodec = (info.get("acodec") or "").lower()

        unsupported_vcodecs = {"av1", "av01", "vp9", "vp09", "vp8", "theora"}
        unsupported_acodecs = {"opus", "vorbis", "flac"}

        needs_video = any(uv in vcodec for uv in unsupported_vcodecs)
        needs_audio = any(ua in acodec for ua in unsupported_acodecs) or (acodec and acodec not in ("aac", "mp3", "pcm_s16le", "pcm_s24le", "alac"))
        needs_container = ext in (".webm", ".mkv")

        if not needs_video and not needs_audio and not needs_container:
            return True, str(inp), None

        app_logger.info(
            f"Ensuring NLE compatibility for '{inp.name}' (vcodec={vcodec}, acodec={acodec}): "
            f"transcode_video={needs_video}, transcode_audio={needs_audio}"
        )

        out_ext = ".mp4" if target_format.lower() != "mov" else ".mov"
        temp_out = inp.parent / f"{inp.stem}_nle_compat{out_ext}"

        # Try hardware acceleration first if video transcode needed, with graceful software fallback
        encoders_to_try = []
        if needs_video:
            if out_ext == ".mov":
                encoders_to_try.append([
                    "-c:v", "prores_ks", "-profile:v", "2",
                    "-c:a", "pcm_s16le", "-ar", "48000"
                ])
            else:
                # 1. Intel QuickSync (fast hardware)
                encoders_to_try.append([
                    "-c:v", "h264_qsv",
                    "-c:a", "aac", "-b:a", "192k",
                    "-movflags", "+faststart"
                ])
                # 2. Universal libx264 fallback
                encoders_to_try.append([
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "192k",
                    "-movflags", "+faststart"
                ])
        else:
            # Video is already H.264/ProRes! Only re-encode audio track to AAC (takes ~1 sec)
            encoders_to_try.append([
                "-c:v", "copy",
                "-c:a", "aac", "-b:a", "192k",
                "-movflags", "+faststart"
            ])

        success = False
        last_err = None

        for enc_args in encoders_to_try:
            if temp_out.exists():
                try:
                    temp_out.unlink()
                except Exception:
                    pass

            cmd = [self.ffmpeg_path, "-y", "-i", str(inp)] + enc_args + [str(temp_out)]
            try:
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=600.0, shell=False)
                if res.returncode == 0 and temp_out.is_file() and temp_out.stat().st_size > 0:
                    success = True
                    break
                else:
                    last_err = res.stderr or "FFmpeg encoding failed"
            except Exception as e:
                last_err = str(e)

        if not success or not temp_out.is_file():
            return False, str(inp), last_err or "Failed to transcode into NLE compatible format."

        # Replace file safely
        final_target = inp.with_suffix(out_ext)
        try:
            if final_target == inp:
                backup = inp.with_suffix(".orig_pre_compat")
                if backup.exists():
                    backup.unlink(missing_ok=True)
                inp.rename(backup)
                temp_out.rename(final_target)
                try:
                    backup.unlink(missing_ok=True)
                except Exception:
                    pass
            else:
                temp_out.rename(final_target)
                try:
                    inp.unlink(missing_ok=True)
                except Exception:
                    pass
            app_logger.info(f"NLE compatibility successfully ensured: {final_target}")
            return True, str(final_target), None
        except Exception as e:
            errors_logger.error(f"Failed to replace original file with compatible version: {e}")
            return True, str(temp_out), None

    def probe_media_info(self, file_path: str) -> Dict[str, Any]:
        """Probes media metadata using ffmpeg output parsing."""
        inp = Path(file_path).resolve()
        info: Dict[str, Any] = {
            "duration": None,
            "width": None,
            "height": None,
            "vcodec": None,
            "acodec": None,
            "filesize": inp.stat().st_size if inp.is_file() else 0
        }

        if not inp.is_file():
            return info

        cmd = [self.ffmpeg_path, "-i", str(inp)]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=8.0, shell=False)
            output = res.stderr or res.stdout
            
            # Duration: 00:01:23.45
            dur_match = re.search(r"Duration:\s*(\d{2}):(\d{2}):(\d{2}\.\d+)", output)
            if dur_match:
                hours, mins, secs = float(dur_match.group(1)), float(dur_match.group(2)), float(dur_match.group(3))
                info["duration"] = hours * 3600 + mins * 60 + secs

            # Video stream resolution: Stream #0:0... Video: h264 ..., 1920x1080
            res_match = re.search(r"Video:.*?(\d{3,4})x(\d{3,4})", output)
            if res_match:
                info["width"] = int(res_match.group(1))
                info["height"] = int(res_match.group(2))

            # Video codec
            vcodec_match = re.search(r"Video:\s*([a-zA-Z0-9_\-]+)", output)
            if vcodec_match:
                info["vcodec"] = vcodec_match.group(1)

            # Audio codec
            acodec_match = re.search(r"Audio:\s*([a-zA-Z0-9_\-]+)", output)
            if acodec_match:
                info["acodec"] = acodec_match.group(1)

        except Exception as e:
            errors_logger.error(f"Error probing media info for {inp}: {e}")

        return info

_processor_instance: Optional[FFmpegProcessor] = None

def get_ffmpeg_processor(custom_path: Optional[str] = None) -> FFmpegProcessor:
    global _processor_instance
    if _processor_instance is None or custom_path:
        _processor_instance = FFmpegProcessor(custom_path)
    return _processor_instance
