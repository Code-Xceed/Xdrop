"""
Xdrop Universal Auto-Updater Engine
Handles background update checking from GitHub, real-time WebSocket notifications,
silent archive downloading & extraction, and automatic re-provisioning of extensions
across DaVinci Resolve, Adobe Creative Cloud (Premiere, AE, Audition), and Blender.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import urllib.error
import zipfile
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

from xdrop import __version__ as CURRENT_VERSION
from xdrop.logger import app_logger, errors_logger
from xdrop.database import get_settings_from_db, save_settings_to_db

GITHUB_REPO = "Code-Xceed/Xdrop"
GITHUB_API_RELEASES = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
GITHUB_RAW_VERSION = f"https://raw.githubusercontent.com/{GITHUB_REPO}/master/version.json"
GITHUB_DEFAULT_ARCHIVE = f"https://github.com/{GITHUB_REPO}/archive/refs/heads/master.zip"


def parse_version(v: str) -> Tuple[int, ...]:
    """Extracts numeric components from a semver string (e.g. 'v1.2.0' -> (1, 2, 0))."""
    if not v:
        return (0, 0, 0)
    cleaned = v.strip().lstrip("vV")
    # Take the base version before any hyphen / pre-release tag
    base = cleaned.split("-")[0]
    nums = re.findall(r"\d+", base)
    if not nums:
        return (0, 0, 0)
    return tuple(int(x) for x in nums)


def compare_versions(v1: str, v2: str) -> int:
    """
    Compares two version strings.
    Returns:
      1 if v1 > v2
      0 if v1 == v2
     -1 if v1 < v2
    """
    p1 = parse_version(v1)
    p2 = parse_version(v2)
    # Pad to equal length
    max_len = max(len(p1), len(p2))
    p1 += (0,) * (max_len - len(p1))
    p2 += (0,) * (max_len - len(p2))
    if p1 > p2:
        return 1
    elif p1 < p2:
        return -1
    return 0


class UpdateInfo:
    def __init__(
        self,
        update_available: bool = False,
        current_version: str = CURRENT_VERSION,
        latest_version: str = CURRENT_VERSION,
        release_name: str = "",
        changelog: str = "",
        published_at: str = "",
        download_url: str = GITHUB_DEFAULT_ARCHIVE,
        is_dismissed: bool = False,
    ):
        self.update_available = update_available
        self.current_version = current_version
        self.latest_version = latest_version
        self.release_name = release_name or f"Xdrop v{latest_version}"
        self.changelog = changelog
        self.published_at = published_at
        self.download_url = download_url
        self.is_dismissed = is_dismissed

    def to_dict(self) -> Dict[str, Any]:
        return {
            "updateAvailable": self.update_available,
            "currentVersion": self.current_version,
            "latestVersion": self.latest_version,
            "releaseName": self.release_name,
            "changelog": self.changelog,
            "publishedAt": self.published_at,
            "downloadUrl": self.download_url,
            "isDismissed": self.is_dismissed,
        }


class UpdateManager:
    """Manages update checking, progress broadcasting, and silent installation."""

    _instance: Optional[UpdateManager] = None

    def __init__(self):
        self._last_check_time: float = 0.0
        self._cached_info: Optional[UpdateInfo] = None
        self._cache_ttl: float = 600.0  # 10 minutes cache
        self._status: str = "idle"  # idle, checking, downloading, extracting, installing, completed, failed
        self._progress: int = 0  # 0 to 100
        self._message: str = ""
        self._error: Optional[str] = None
        self._lock = asyncio.Lock()

    @classmethod
    def get_instance(cls) -> UpdateManager:
        if cls._instance is None:
            cls._instance = UpdateManager()
        return cls._instance

    @property
    def current_status(self) -> Dict[str, Any]:
        return {
            "stage": self._status,
            "percent": self._progress,
            "message": self._message,
            "error": self._error,
            "currentVersion": CURRENT_VERSION,
            "latestVersion": self._cached_info.latest_version if self._cached_info else CURRENT_VERSION,
        }

    async def broadcast_status(self):
        """Emits real-time progress update to all active WebSocket connections."""
        try:
            from xdrop.api.websocket import manager

            await manager.broadcast({
                "type": "UPDATE_PROGRESS",
                "payload": self.current_status,
            })
        except Exception as e:
            app_logger.debug(f"[Updater] WebSocket broadcast skipped: {e}")

    async def broadcast_available(self, info: UpdateInfo):
        """Broadcasts UPDATE_AVAILABLE event to connected panels."""
        try:
            from xdrop.api.websocket import manager

            await manager.broadcast({
                "type": "UPDATE_AVAILABLE",
                "payload": info.to_dict(),
            })
        except Exception as e:
            app_logger.debug(f"[Updater] WebSocket update announcement skipped: {e}")

    async def check_for_updates(self, force: bool = False) -> UpdateInfo:
        """
        Queries GitHub for newer releases or version.json commits.
        Returns an UpdateInfo object.
        """
        now = time.time()
        if not force and self._cached_info is not None and (now - self._last_check_time) < self._cache_ttl:
            return self._cached_info

        app_logger.info("[Updater] Checking GitHub for updates...")
        self._last_check_time = now

        settings = get_settings_from_db()
        dismissed_ver = settings.get("dismissed_update_version", "")

        latest_ver = CURRENT_VERSION
        release_name = f"Xdrop v{CURRENT_VERSION}"
        changelog = ""
        published_at = ""
        download_url = GITHUB_DEFAULT_ARCHIVE

        fetched = False

        # 1. Try GitHub Releases API
        try:
            req = urllib.request.Request(
                GITHUB_API_RELEASES,
                headers={
                    "User-Agent": "Xdrop-AutoUpdater",
                    "Accept": "application/vnd.github.v3+json",
                },
            )
            # Run in thread executor to not block async loop
            loop = asyncio.get_running_loop()
            resp_bytes = await loop.run_in_executor(None, lambda: urllib.request.urlopen(req, timeout=6).read())
            data = json.loads(resp_bytes.decode("utf-8"))

            tag_name = data.get("tag_name", "").strip()
            if tag_name:
                latest_ver = tag_name.lstrip("vV")
                release_name = data.get("name") or f"Xdrop v{latest_ver}"
                changelog = data.get("body") or ""
                published_at = data.get("published_at") or ""
                # Check for zipball assets or zipball_url
                assets = data.get("assets", [])
                zip_assets = [a for a in assets if a.get("name", "").endswith(".zip")]
                if zip_assets:
                    download_url = zip_assets[0].get("browser_download_url") or data.get("zipball_url", download_url)
                else:
                    download_url = data.get("zipball_url") or download_url
                fetched = True
        except Exception as e:
            app_logger.debug(f"[Updater] GitHub Releases API unavailable or no release yet ({e}); trying raw version.json")

        # 2. Fallback to raw version.json on master branch
        if not fetched:
            try:
                req = urllib.request.Request(
                    GITHUB_RAW_VERSION,
                    headers={
                        "User-Agent": "Xdrop-AutoUpdater",
                        "Accept": "application/json",
                    },
                )
                loop = asyncio.get_running_loop()
                resp_bytes = await loop.run_in_executor(None, lambda: urllib.request.urlopen(req, timeout=6).read())
                v_data = json.loads(resp_bytes.decode("utf-8"))

                latest_ver = str(v_data.get("version", CURRENT_VERSION)).strip().lstrip("vV")
                release_name = v_data.get("name") or f"Xdrop v{latest_ver}"
                changelog = v_data.get("changelog") or ""
                published_at = v_data.get("releaseDate") or ""
                download_url = v_data.get("archiveUrl") or GITHUB_DEFAULT_ARCHIVE
                fetched = True
            except Exception as e:
                app_logger.debug(f"[Updater] Could not fetch raw version.json ({e}).")

        # Determine if new version is strictly newer
        is_newer = compare_versions(latest_ver, CURRENT_VERSION) > 0
        is_dismissed = (latest_ver == dismissed_ver)

        info = UpdateInfo(
            update_available=is_newer,
            current_version=CURRENT_VERSION,
            latest_version=latest_ver,
            release_name=release_name,
            changelog=changelog,
            published_at=published_at,
            download_url=download_url,
            is_dismissed=is_dismissed,
        )

        self._cached_info = info
        if is_newer and not is_dismissed:
            app_logger.info(f"[Updater] New update available: v{latest_ver} (current: v{CURRENT_VERSION})")
            await self.broadcast_available(info)

        return info

    def dismiss_version(self, version: str):
        """Records a version as dismissed by the user."""
        db_settings = get_settings_from_db()
        db_settings["dismissed_update_version"] = version
        save_settings_to_db(db_settings)
        if self._cached_info and self._cached_info.latest_version == version:
            self._cached_info.is_dismissed = True

    async def install_update(self, download_url: Optional[str] = None) -> bool:
        """
        Executes the update workflow:
        1. Downloads release archive.
        2. Unpacks files safely into temporary directory.
        3. Updates engine and web distribution assets.
        4. Re-provisions extensions in DaVinci Resolve, Premiere Pro, After Effects, Audition.
        5. Reports progress in real time via WebSockets.
        """
        async with self._lock:
            if self._status in ("downloading", "extracting", "installing"):
                return False

            url = download_url or (self._cached_info.download_url if self._cached_info else GITHUB_DEFAULT_ARCHIVE)
            self._status = "downloading"
            self._progress = 10
            self._message = "Downloading update from GitHub..."
            self._error = None
            await self.broadcast_status()

            temp_dir = Path(tempfile.mkdtemp(prefix="xdrop_update_"))
            archive_path = temp_dir / "update.zip"

            try:
                # 1. Download archive in thread
                loop = asyncio.get_running_loop()

                def _download():
                    req = urllib.request.Request(
                        url,
                        headers={"User-Agent": "Xdrop-AutoUpdater"},
                    )
                    with urllib.request.urlopen(req, timeout=45) as resp, open(archive_path, "wb") as out_f:
                        shutil.copyfileobj(resp, out_f)

                await loop.run_in_executor(None, _download)

                self._progress = 45
                self._status = "extracting"
                self._message = "Unpacking update archive..."
                await self.broadcast_status()

                # 2. Extract archive
                extract_dir = temp_dir / "extracted"
                extract_dir.mkdir(parents=True, exist_ok=True)

                def _extract():
                    with zipfile.ZipFile(archive_path, "r") as zip_ref:
                        zip_ref.extractall(extract_dir)

                await loop.run_in_executor(None, _extract)

                # Find root inside extracted zip (e.g. Xdrop-master or Code-Xceed-Xdrop-xxx)
                subdirs = [d for d in extract_dir.iterdir() if d.is_dir()]
                repo_root = subdirs[0] if subdirs else extract_dir

                self._progress = 70
                self._status = "installing"
                self._message = "Deploying updated extensions to video editors..."
                await self.broadcast_status()

                # 3. Deploy update to system
                def _deploy_files():
                    # Identify target installed directory
                    if sys.platform == "win32":
                        engine_dir = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "Xdrop"
                    else:
                        engine_dir = Path.home() / ".xdrop"

                    # A. Update desktop engine core files
                    src_pkg = repo_root / "src" / "desktop-service" / "xdrop"
                    if src_pkg.is_dir():
                        target_pkg = engine_dir / "xdrop"
                        target_pkg.mkdir(parents=True, exist_ok=True)
                        shutil.copytree(src_pkg, target_pkg, dirs_exist_ok=True)

                    # B. Update dist web assets
                    src_dist = repo_root / "src" / "resolve-plugin" / "dist"
                    if not src_dist.is_dir():
                        src_dist = repo_root / "dist"
                    if src_dist.is_dir():
                        target_dist = engine_dir / "dist"
                        target_dist.mkdir(parents=True, exist_ok=True)
                        shutil.copytree(src_dist, target_dist, dirs_exist_ok=True)

                    # C. Update DaVinci Resolve Extension
                    resolve_script_src = repo_root / "src" / "resolve-plugin" / "Xdrop.lua"
                    resolve_bin_src = repo_root / "src" / "resolve-plugin" / "Xdrop - Starter Bin.drb"

                    resolve_comp_dirs = []
                    if sys.platform == "win32":
                        appdata = os.environ.get("APPDATA")
                        if appdata:
                            resolve_comp_dirs.append(
                                Path(appdata) / "Blackmagic Design" / "DaVinci Resolve" / "Support" / "Fusion" / "Scripts" / "Comp"
                            )
                    elif sys.platform == "darwin":
                        resolve_comp_dirs.append(
                            Path.home() / "Library" / "Application Support" / "Blackmagic Design" / "DaVinci Resolve" / "Fusion" / "Scripts" / "Comp"
                        )
                    else:
                        resolve_comp_dirs.append(
                            Path.home() / ".local" / "share" / "DaVinciResolve" / "Fusion" / "Scripts" / "Comp"
                        )

                    for cdir in resolve_comp_dirs:
                        if cdir.parent.is_dir():
                            cdir.mkdir(parents=True, exist_ok=True)
                            if resolve_script_src.is_file():
                                shutil.copy2(resolve_script_src, cdir / "Xdrop.lua")
                            if resolve_bin_src.is_file():
                                shutil.copy2(resolve_bin_src, cdir / "Xdrop - Starter Bin.drb")

                    # D. Update Adobe Creative Cloud (Premiere, AE, Audition) CEP
                    adobe_src = repo_root / "src" / "premiere-plugin"
                    if adobe_src.is_dir():
                        if sys.platform == "win32":
                            cep_dir = Path(os.environ.get("APPDATA", "")) / "Adobe" / "CEP" / "extensions"
                        elif sys.platform == "darwin":
                            cep_dir = Path.home() / "Library" / "Application Support" / "Adobe" / "CEP" / "extensions"
                        else:
                            cep_dir = None

                        if cep_dir:
                            target_cep = cep_dir / "com.xdrop.panel"
                            target_cep.mkdir(parents=True, exist_ok=True)
                            shutil.copytree(adobe_src, target_cep, dirs_exist_ok=True)

                await loop.run_in_executor(None, _deploy_files)

                # Read updated version if available
                updated_v = self._cached_info.latest_version if self._cached_info else "latest"

                self._progress = 100
                self._status = "completed"
                self._message = f"Xdrop successfully updated to v{updated_v}!"
                app_logger.info(f"[Updater] Update complete: installed version {updated_v}")
                await self.broadcast_status()

                # Clean up temp
                shutil.rmtree(temp_dir, ignore_errors=True)
                return True

            except Exception as e:
                errors_logger.exception(f"[Updater] Installation failed: {e}")
                self._status = "failed"
                self._progress = 0
                self._error = str(e)
                self._message = f"Update failed: {e}"
                await self.broadcast_status()
                shutil.rmtree(temp_dir, ignore_errors=True)
                return False


def get_update_manager() -> UpdateManager:
    return UpdateManager.get_instance()
