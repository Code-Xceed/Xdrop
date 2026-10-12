"""
Installer for DaVinci Resolve Studio Workflow Integration plugin.

DaVinci Resolve Studio discovers Workflow Integration plugins on startup from:
- Windows (System): %PROGRAMDATA%\\Blackmagic Design\\DaVinci Resolve\\Support\\Workflow Integration Plugins\\
- Windows (User): %APPDATA%\\Blackmagic Design\\DaVinci Resolve\\Support\\Workflow Integration Plugins\\
- macOS (User): ~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Workflow Integration Plugins/
- macOS (System): /Library/Application Support/Blackmagic Design/DaVinci Resolve/Workflow Integration Plugins/

When installed, Xdrop docks natively inside DaVinci Resolve Studio under:
Workspace -> Workflow Integrations -> Xdrop.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple

from xdrop.logger import resolve_logger
from .paths import (
    SYSTEM_SCOPE,
    USER_SCOPE,
    HostPlatformPaths,
    detect,
    repo_root,
)
from .results import InstallResult

RESOLVE_STUDIO_PLUGIN_ID = "com.xdrop.resolve.workflowintegration"


def resolve_studio_plugin_dirs(paths: HostPlatformPaths) -> Tuple[Path, Path]:
    """Returns (per_user_dir, all_users_dir) for Resolve Studio Workflow Integration plugins."""
    if paths.is_windows:
        per_user = (
            paths.appdata
            / "Blackmagic Design"
            / "DaVinci Resolve"
            / "Support"
            / "Workflow Integration Plugins"
        )
        all_users = (
            paths.program_data
            / "Blackmagic Design"
            / "DaVinci Resolve"
            / "Support"
            / "Workflow Integration Plugins"
        )
    elif paths.is_macos:
        per_user = (
            paths.home
            / "Library"
            / "Application Support"
            / "Blackmagic Design"
            / "DaVinci Resolve"
            / "Workflow Integration Plugins"
        )
        all_users = (
            paths.program_data
            / "Blackmagic Design"
            / "DaVinci Resolve"
            / "Workflow Integration Plugins"
        )
    else:
        per_user = paths.home / ".local" / "share" / "DaVinciResolve" / "Workflow Integration Plugins"
        all_users = Path("/opt/resolve/Workflow Integration Plugins")

    return per_user, all_users


def find_resolve_studio_source() -> Optional[Path]:
    """Locates the `apps/resolve-workflow-integration` plugin directory."""
    here = Path(__file__).resolve()
    candidates = [
        repo_root() / "apps" / "resolve-workflow-integration",
        here.parents[3] / "resolve-workflow-integration",
        Path.cwd() / "apps" / "resolve-workflow-integration",
        Path.cwd() / "resolve-workflow-integration",
    ]

    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.insert(0, Path(meipass) / "apps" / "resolve-workflow-integration")
        candidates.insert(0, Path(meipass) / "resolve-workflow-integration")

    for c in candidates:
        if (c / "manifest.xml").is_file():
            return c
    return None


def install_resolve_studio_plugin(
    paths: Optional[HostPlatformPaths] = None,
    scope: str = USER_SCOPE,
) -> InstallResult:
    """Installs the Xdrop Workflow Integration plugin for DaVinci Resolve Studio."""
    host_paths = paths or detect()
    per_user, all_users = resolve_studio_plugin_dirs(host_paths)
    target_root = all_users if scope == SYSTEM_SCOPE else per_user
    plugin_target = target_root / RESOLVE_STUDIO_PLUGIN_ID

    source = find_resolve_studio_source()
    if not source:
        return InstallResult(
            host="resolve_studio",
            label="DaVinci Resolve Studio",
            ok=False,
            message="Source directory `apps/resolve-workflow-integration` not found.",
            path=str(plugin_target),
            scope=scope,
        )

    try:
        target_root.mkdir(parents=True, exist_ok=True)
        if plugin_target.exists():
            shutil.rmtree(plugin_target, ignore_errors=True)

        shutil.copytree(source, plugin_target, dirs_exist_ok=True)

        # Verify installation
        manifest = plugin_target / "manifest.xml"
        if not manifest.is_file():
            return InstallResult(
                host="resolve_studio",
                label="DaVinci Resolve Studio",
                ok=False,
                message=f"Plugin copied to {plugin_target} but manifest.xml is missing.",
                path=str(plugin_target),
                scope=scope,
            )

        resolve_logger.info(f"Installed Resolve Studio Workflow Integration at {plugin_target}")
        return InstallResult(
            host="resolve_studio",
            label="DaVinci Resolve Studio",
            ok=True,
            message=(
                f"Installed DaVinci Resolve Studio Workflow Integration plugin to {plugin_target}. "
                "Open inside Resolve Studio via Workspace -> Workflow Integrations -> Xdrop."
            ),
            path=str(plugin_target),
            scope=scope,
        )

    except PermissionError:
        return InstallResult(
            host="resolve_studio",
            label="DaVinci Resolve Studio",
            ok=False,
            message=(
                f"Writing to {plugin_target} requires administrator privileges. "
                "Try installing with per-user scope instead."
            ),
            path=str(plugin_target),
            scope=scope,
            requires_admin=True,
        )
    except Exception as exc:
        return InstallResult(
            host="resolve_studio",
            label="DaVinci Resolve Studio",
            ok=False,
            message=f"Failed to install Resolve Studio plugin: {exc}",
            path=str(plugin_target),
            scope=scope,
        )


def resolve_studio_plugin_status(paths: Optional[HostPlatformPaths] = None) -> Dict[str, object]:
    """Returns whether the Workflow Integration plugin is installed."""
    host_paths = paths or detect()
    per_user, all_users = resolve_studio_plugin_dirs(host_paths)

    user_manifest = per_user / RESOLVE_STUDIO_PLUGIN_ID / "manifest.xml"
    system_manifest = all_users / RESOLVE_STUDIO_PLUGIN_ID / "manifest.xml"

    installed = user_manifest.is_file() or system_manifest.is_file()
    active_path = str(user_manifest.parent) if user_manifest.is_file() else (str(system_manifest.parent) if system_manifest.is_file() else None)

    return {
        "installed": installed,
        "path": active_path,
        "user_path": str(per_user / RESOLVE_STUDIO_PLUGIN_ID),
        "system_path": str(all_users / RESOLVE_STUDIO_PLUGIN_ID),
    }
