import os
import shutil
from pathlib import Path
from typing import Optional, List, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict

def to_camel(string: str) -> str:
    components = string.split("_")
    return components[0] + "".join(x.title() for x in components[1:])

def get_base_data_dir() -> Path:
    if os.getenv("XDROP_DATA_DIR"):
        p = Path(os.getenv("XDROP_DATA_DIR"))
    elif os.getenv("RESOLVEFETCH_DATA_DIR"):
        p = Path(os.getenv("RESOLVEFETCH_DATA_DIR"))
    else:
        appdata = os.getenv("LOCALAPPDATA")
        if appdata:
            p = Path(appdata) / "Xdrop"
        else:
            p = Path.home() / ".xdrop"
    p.mkdir(parents=True, exist_ok=True)
    return p

def get_default_downloads_dir() -> Path:
    # Default to user's Videos / Xdrop Assets
    videos_dir = Path.home() / "Videos" / "Xdrop Assets"
    try:
        videos_dir.mkdir(parents=True, exist_ok=True)
        return videos_dir
    except Exception:
        fallback = get_base_data_dir() / "downloads"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback

def discover_ffmpeg() -> str:
    """Discovers FFmpeg executable on the system."""
    import sys

    # 1. Environment variable override
    env_path = os.getenv("FFMPEG_PATH")
    if env_path and Path(env_path).is_file():
        return str(Path(env_path).resolve())

    # 2. Local portable bin directory inside Xdrop or AppData
    exe_name = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
    local_bins = [
        Path(__file__).resolve().parent.parent / "bin" / exe_name,
        Path(__file__).resolve().parent.parent.parent.parent / "bin" / exe_name,
        get_base_data_dir() / "bin" / exe_name,
    ]
    for lb in local_bins:
        if lb.is_file():
            return str(lb.resolve())

    # 3. System PATH
    which_ffmpeg = shutil.which("ffmpeg")
    if which_ffmpeg:
        return str(Path(which_ffmpeg).resolve())

    # 4. Known common locations on Windows
    candidate_paths = [
        Path("C:/Program Files/ShareX/ffmpeg.exe"),
        Path("C:/Program Files/ffmpeg/bin/ffmpeg.exe"),
        Path("C:/ffmpeg/bin/ffmpeg.exe"),
        Path(os.getenv("LOCALAPPDATA", "")) / "Programs/ffmpeg/bin/ffmpeg.exe",
        Path("C:/ProgramData/chocolatey/bin/ffmpeg.exe"),
        Path(os.getenv("USERPROFILE", "")) / "scoop/shims/ffmpeg.exe",
        Path("C:/Program Files/Softdeluxe/Free Download Manager/ffmpeg.exe"),
        # macOS Homebrew & MacPorts
        Path("/opt/homebrew/bin/ffmpeg"),
        Path("/usr/local/bin/ffmpeg"),
        Path("/opt/local/bin/ffmpeg"),
        # Linux standard paths
        Path("/usr/bin/ffmpeg"),
        Path("/usr/local/bin/ffmpeg"),
    ]

    for cand in candidate_paths:
        if cand.is_file():
            return str(cand.resolve())

    return "ffmpeg"

def validate_and_sanitize_download_dir(dir_path: str) -> str:
    """Validates that download_dir points to an accessible drive and path, otherwise falls back to default."""
    if not dir_path or not dir_path.strip():
        return str(get_default_downloads_dir())
    try:
        p = Path(dir_path)
        # Check if the root drive exists (e.g. D:\ on a machine without D: drive)
        if p.drive:
            drive_root = Path(p.drive + "\\")
            if not drive_root.exists():
                return str(get_default_downloads_dir())
        return str(p)
    except Exception:
        return str(get_default_downloads_dir())

class AppSettingsModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
    )

    download_dir: str = Field(default_factory=lambda: str(get_default_downloads_dir()))

    @field_validator("download_dir", mode="before")
    @classmethod
    def check_download_dir(cls, v: Any) -> str:
        if isinstance(v, str):
            return validate_and_sanitize_download_dir(v)
        return str(get_default_downloads_dir())

    naming_pattern: str = "{project}/{platform}/{mediaType}/{title}_{quality}"
    concurrent_downloads: int = 3
    default_editor: str = "auto" # 'auto', 'resolve', 'premiere', 'aftereffects'
    auto_import_to_resolve: bool = True
    target_media_pool_bin: str = "Xdrop"
    auto_import_to_premiere: bool = True
    target_premiere_bin: str = "Xdrop"
    auto_import_to_aftereffects: bool = True
    target_aftereffects_bin: str = "Xdrop"
    overwrite_existing: bool = False
    ffmpeg_path: str = Field(default_factory=discover_ffmpeg)
    preferred_video_format: str = "mp4" # mp4, mov, original
    preferred_audio_format: str = "wav" # wav, mp3, aac, original
    generate_proxy: bool = False
    proxy_resolution: str = "720p" # 720p, 540p
    connection_timeout: int = 30 # seconds
    retry_count: int = 3
    local_only: bool = True
    telemetry_enabled: bool = False

DATA_DIR = get_base_data_dir()
DB_PATH = DATA_DIR / "xdrop.db"

# Automatic migration from legacy resolvefetch.db if present
if not DB_PATH.exists():
    legacy_db = DATA_DIR / "resolvefetch.db"
    if legacy_db.exists():
        try:
            shutil.copy2(legacy_db, DB_PATH)
        except Exception:
            pass
    elif os.getenv("LOCALAPPDATA"):
        old_appdata_db = Path(os.getenv("LOCALAPPDATA")) / "ResolveFetch" / "resolvefetch.db"
        if old_appdata_db.exists():
            try:
                shutil.copy2(old_appdata_db, DB_PATH)
            except Exception:
                pass

THUMBNAILS_DIR = DATA_DIR / "thumbnails"
THUMBNAILS_DIR.mkdir(parents=True, exist_ok=True)
PROXIES_DIR = DATA_DIR / "proxies"
PROXIES_DIR.mkdir(parents=True, exist_ok=True)
