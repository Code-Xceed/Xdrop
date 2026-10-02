import os
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

WINDOWS_RESERVED = {"CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4",
                    "COM5", "COM6", "COM7", "COM8", "COM9", "LPT1", "LPT2",
                    "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"}

def sanitize_filename_py(name: str, fallback: str = "asset") -> str:
    """Sanitizes filename for all operating systems, especially Windows."""
    if not name or not name.strip():
        return fallback

    # Remove null bytes and invalid characters
    sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1F]', '_', name)
    sanitized = re.sub(r'\s+', ' ', sanitized).strip()
    # Strip trailing periods and spaces
    sanitized = sanitized.rstrip('. ')

    p = Path(sanitized)
    stem = p.stem.upper()
    if stem in WINDOWS_RESERVED:
        sanitized = f"{p.stem}_file{p.suffix}"

    if len(sanitized) > 120:
        sanitized = sanitized[:120].strip()

    return sanitized or fallback

class MediaOrganizer:
    """Handles directory path expansion and asset file naming."""

    def __init__(self, base_download_dir: str):
        try:
            cand = Path(base_download_dir).resolve()
            if cand.drive and not Path(cand.drive + "\\").exists():
                from xdrop.config import get_default_downloads_dir
                cand = get_default_downloads_dir()
            self.base_dir = cand
        except Exception:
            from xdrop.config import get_default_downloads_dir
            self.base_dir = get_default_downloads_dir()

    def resolve_destination(
        self,
        naming_pattern: str,
        project_name: Optional[str],
        platform: str,
        media_type: str,
        title: str,
        quality_label: str,
        extension: str,
        overwrite_existing: bool = False
    ) -> Path:
        """
        Resolves safe destination path based on template variables and prevents path traversal.
        """
        date_str = datetime.now().strftime("%Y-%m-%d")
        proj = project_name or "DefaultProject"
        
        clean_proj = sanitize_filename_py(proj, "DefaultProject")
        clean_platform = sanitize_filename_py(platform.capitalize(), "UnknownPlatform")
        clean_type = sanitize_filename_py(media_type.capitalize(), "Video")
        clean_title = sanitize_filename_py(title, "untitled")
        clean_quality = sanitize_filename_py(quality_label, "original")
        clean_ext = extension.lstrip(".") or "mp4"

        # Replace variables
        formatted = naming_pattern
        formatted = formatted.replace("{project}", clean_proj)
        formatted = formatted.replace("{platform}", clean_platform)
        formatted = formatted.replace("{mediaType}", clean_type)
        formatted = formatted.replace("{date}", date_str)
        formatted = formatted.replace("{title}", clean_title)
        formatted = formatted.replace("{quality}", clean_quality)

        # Normalize relative path components to prevent directory traversal
        rel_path = Path(formatted.replace("\\", "/"))
        safe_parts = []
        for part in rel_path.parts:
            if part in ("..", ".", ""):
                continue
            safe_parts.append(sanitize_filename_py(part))

        if not safe_parts:
            safe_parts = [clean_proj, clean_platform, clean_type, f"{clean_title}_{clean_quality}"]

        # Ensure the filename ends with the target extension
        file_stem = safe_parts[-1]
        if not file_stem.lower().endswith(f".{clean_ext.lower()}"):
            safe_parts[-1] = f"{file_stem}.{clean_ext}"

        dest_file = (self.base_dir / Path(*safe_parts)).resolve()

        # Security check: MUST be inside self.base_dir
        try:
            dest_file.relative_to(self.base_dir)
        except ValueError:
            # Traversal attempted; force inside base_dir
            dest_file = (self.base_dir / f"{clean_title}_{clean_quality}.{clean_ext}").resolve()

        try:
            dest_file.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            from xdrop.config import get_default_downloads_dir
            fallback_dir = get_default_downloads_dir() / clean_proj / clean_platform / clean_type
            fallback_dir.mkdir(parents=True, exist_ok=True)
            dest_file = (fallback_dir / safe_parts[-1]).resolve()
            dest_file.parent.mkdir(parents=True, exist_ok=True)

        if not overwrite_existing and dest_file.exists():
            counter = 1
            parent = dest_file.parent
            base_stem = dest_file.stem
            while dest_file.exists():
                dest_file = parent / f"{base_stem}_{counter}.{clean_ext}"
                counter += 1

        return dest_file
