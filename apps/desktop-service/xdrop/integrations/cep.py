"""
The Adobe CEP half of the install: copy the panel folder, then make the hosts load it.

Two things happen here, and both matter:

1. **The panel folder is copied** into Adobe's per-user `CEP/extensions` directory. That
   directory needs no administrator rights, which is the whole reason the default install
   is per-user.
2. **`PlayerDebugMode` is enabled.** An unsigned (folder-copied) CEP extension is only
   loaded when the host is in developer mode, and the flag lives per CSXS major version:
   Windows `HKCU\\Software\\Adobe\\CSXS.<n>\\PlayerDebugMode` as `REG_SZ` `"1"`, macOS
   `defaults write com.adobe.CSXS.<n> PlayerDebugMode 1`. Writing every version in
   `CSXS_VERSIONS` is deliberate — missing the version a given host uses leaves the panel
   invisible, and writing an unused one costs nothing.

Previously the Windows registry key was the only path implemented (in `xdrop/setup.py`),
so a macOS install silently produced a panel that never appeared. Both paths are now here,
behind one function, with the exact commands generated as plain data so they can be tested
without touching a real registry.

References: Adobe *Package, Distribute, Install Guide* (CEP).
"""

from __future__ import annotations

import json
import shutil
import stat
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from xdrop.logger import app_logger

from .headless import decode, run_silent
from .paths import (
    CEP_SUPPORTED,
    CSXS_VERSIONS,
    LAUNCHER_NAME,
    LEGACY_LAUNCHER_NAME,
    MACOS,
    SERVICE_URL,
    SYSTEM_SCOPE,
    USER_SCOPE,
    WINDOWS,
    HostPlatformPaths,
    cep_extension_dirs,
    desktop_service_root,
    detect,
    find_cep_source,
    repo_root,
)
from .results import InstallResult

#: Directories inside the panel source that must not be copied into Adobe's folder: the UXP
#: packaging sources are not part of the CEP panel, and VCS/cache folders are noise.
_IGNORED_PANEL_ENTRIES = (
    "uxp",
    ".git",
    ".github",
    "node_modules",
    "__pycache__",
    "*.pyc",
    "dist",
)

#: Files that live in the panel folder next to the manifest.
_CONFIG_FILENAME = "config.json"


# --- PlayerDebugMode -----------------------------------------------------------------


def player_debug_mode_commands(
    system: str,
    versions: Sequence[str] = CSXS_VERSIONS,
) -> List[List[str]]:
    """The exact commands that enable CEP developer mode, as plain argument lists.

    Returns `[]` on Linux, where CEP does not exist. Nothing here executes anything: the
    caller decides whether to run them, which keeps the command shape unit-testable.
    """
    commands: List[List[str]] = []
    for version in versions:
        if system == WINDOWS:
            commands.append(
                [
                    "reg",
                    "add",
                    f"HKCU\\Software\\Adobe\\CSXS.{version}",
                    "/v",
                    "PlayerDebugMode",
                    "/t",
                    "REG_SZ",
                    "/d",
                    "1",
                    "/f",
                ]
            )
        elif system == MACOS:
            commands.append(
                ["defaults", "write", f"com.adobe.CSXS.{version}", "PlayerDebugMode", "1"]
            )
    return commands


def read_player_debug_mode(
    system: str,
    versions: Sequence[str] = CSXS_VERSIONS,
    runner=None,
) -> Dict[str, Optional[bool]]:
    """Reads the current developer-mode flag per CSXS version.

    `True`/`False` are real answers, `None` means the version is not configured at all
    (which is what a fresh machine looks like). Never writes anything.
    """
    if system not in CEP_SUPPORTED:
        return {}

    runner = runner or run_silent
    state: Dict[str, Optional[bool]] = {}
    for version in versions:
        if system == WINDOWS:
            argv = ["reg", "query", f"HKCU\\Software\\Adobe\\CSXS.{version}", "/v", "PlayerDebugMode"]
        else:
            argv = ["defaults", "read", f"com.adobe.CSXS.{version}", "PlayerDebugMode"]

        proc = runner(argv)
        if proc.returncode != 0:
            state[version] = None
            continue

        text = decode(proc.stdout)
        value = text.strip().split()[-1] if text.strip() else ""
        if value == "1":
            state[version] = True
        elif value == "0":
            state[version] = False
        else:
            state[version] = None
    return state


def apply_player_debug_mode(
    system: str,
    versions: Sequence[str] = CSXS_VERSIONS,
    runner=None,
) -> Dict[str, object]:
    """Runs the developer-mode commands, headless, collecting per-version outcomes."""
    runner = runner or run_silent
    applied: List[str] = []
    failed: List[Dict[str, object]] = []

    for version, argv in zip(versions, player_debug_mode_commands(system, versions)):
        proc = runner(argv)
        if proc.returncode == 0:
            applied.append(version)
        else:
            failed.append(
                {
                    "version": version,
                    "returncode": proc.returncode,
                    "stderr": decode(proc.stderr).strip(),
                }
            )

    if failed:
        app_logger.warning("PlayerDebugMode could not be set for CSXS %s", ", ".join(f["version"] for f in failed))

    return {
        "system": system,
        "versions": list(versions),
        "applied": applied,
        "failed": failed,
        "enabled": bool(applied) and system in CEP_SUPPORTED,
    }


# --- Panel install -------------------------------------------------------------------


def panel_config_payload() -> Dict[str, str]:
    """The `config.json` the panel reads to know how to start/reach the service."""
    root = repo_root()
    service_root = desktop_service_root()

    return {
        "runBat": str(root / "run.bat"),
        "runSh": str(root / "run.sh"),
        "pythonExe": sys.executable,
        "mainPy": str(service_root / "main.py"),
        "serviceUrl": SERVICE_URL,
        "launcherName": LAUNCHER_NAME,
        "legacyLauncherName": LEGACY_LAUNCHER_NAME,
        "ctrlKeys": f"Xdrop:{LAUNCHER_NAME}",
    }


#: Windows can hold a directory in "delete pending" for a moment after removal, and an
#: immediately following create then fails with access denied. Retrying is the fix; deleting
#: nothing is even better, which is why the panel is synced in place rather than replaced.
_COPY_ATTEMPTS = 3
_COPY_RETRY_DELAY = 0.2


def _clear_read_only(root: Path) -> None:
    """Clears the read-only attribute so an overlay copy can overwrite existing files."""
    for path in root.rglob("*"):
        try:
            if not path.is_symlink():
                path.chmod(path.stat().st_mode | stat.S_IWRITE)
        except OSError:
            continue


def _prune_stale_files(source: Path, dest: Path) -> None:
    """Removes files in `dest` that no longer exist in `source` (old panel builds)."""
    keep = {_CONFIG_FILENAME}
    for existing in sorted(dest.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        if existing.is_dir():
            continue
        relative = existing.relative_to(dest).as_posix()
        if relative in keep:
            continue
        if not (source / relative).is_file():
            try:
                existing.unlink()
            except OSError:
                continue

    for existing in sorted(dest.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        if not existing.is_dir() or existing.is_symlink():
            continue
        try:
            if not any(existing.iterdir()):
                existing.rmdir()
        except OSError:
            continue


def _copy_panel(source: Path, dest: Path) -> Optional[str]:
    """Syncs `dest` to match `source` in place. Returns an error string on failure.

    An overlay rather than delete-and-recreate: it cannot leave a half-removed panel behind,
    it does not fight Windows' delete-pending state, and it is what makes a second install a
    no-op instead of an error.
    """
    last_error: Optional[str] = None

    for attempt in range(_COPY_ATTEMPTS):
        try:
            if dest.is_symlink():
                dest.unlink()
            dest.mkdir(parents=True, exist_ok=True)
            _clear_read_only(dest)
            shutil.copytree(
                source,
                dest,
                dirs_exist_ok=True,
                ignore=shutil.ignore_patterns(*_IGNORED_PANEL_ENTRIES),
            )
            _prune_stale_files(source, dest)
            return None
        except PermissionError as exc:
            last_error = f"permission denied writing {dest}: {exc}"
        except OSError as exc:
            last_error = f"could not write {dest}: {exc}"

        # A transient lock (Windows delete-pending, an editor holding a file) is worth
        # retrying; a real permission problem is not, so the last error is reported as-is.
        if attempt < _COPY_ATTEMPTS - 1:
            time.sleep(_COPY_RETRY_DELAY * (attempt + 1))

    return last_error


def install_cep_panel(
    paths: Optional[HostPlatformPaths] = None,
    scope: str = USER_SCOPE,
    apply_debug_mode: bool = True,
    runner=None,
) -> InstallResult:
    """Installs the Adobe panel for Premiere Pro and After Effects, headless.

    One panel serves both hosts (`PPRO` and `AEFT` are declared in the same manifest), so a
    single copy is the correct behaviour rather than two installs.
    """
    paths = paths or detect()
    label = "Premiere Pro & After Effects"

    if paths.system not in CEP_SUPPORTED:
        return InstallResult(
            host="adobe",
            label=label,
            ok=False,
            message=(
                "Adobe CEP extensions are only supported on Windows and macOS. "
                "On Linux, use DaVinci Resolve — the Resolve script works everywhere."
            ),
            scope=scope,
            details={"system": paths.system},
        )

    source = find_cep_source()
    if source is None:
        return InstallResult(
            host="adobe",
            label=label,
            ok=False,
            message=(
                "Could not find the Adobe panel source (apps/premiere-plugin with "
                "CSXS/manifest.xml). If you are running from a frozen build, reinstall Xdrop."
            ),
            scope=scope,
            details={"searched_from": str(Path(__file__).resolve())},
        )

    destinations = cep_extension_dirs(paths, scope)
    if not destinations:
        return InstallResult(
            host="adobe",
            label=label,
            ok=False,
            message="No CEP extensions directory is available on this system.",
            scope=scope,
        )

    failures: List[Dict[str, str]] = []
    written: List[str] = []
    config = panel_config_payload()

    for dest in destinations:
        error = _copy_panel(source, dest)
        if error:
            failures.append({"path": str(dest), "error": error})
            continue
        try:
            (dest / _CONFIG_FILENAME).write_text(
                json.dumps(config, indent=2), encoding="utf-8"
            )
        except OSError as exc:
            failures.append({"path": str(dest / _CONFIG_FILENAME), "error": str(exc)})
            continue
        written.append(str(dest))

    if not written:
        requires_admin = scope == SYSTEM_SCOPE
        first = failures[0] if failures else {"path": str(destinations[0]), "error": "unknown error"}
        return InstallResult(
            host="adobe",
            label=label,
            ok=False,
            message=(
                f"Could not install the Adobe panel ({first['error']})."
                + (
                    " The all-users CEP folder needs administrator rights — install to the "
                    "current user instead."
                    if requires_admin
                    else ""
                )
            ),
            path=first["path"],
            scope=scope,
            requires_admin=requires_admin,
            details={"failures": failures},
        )

    debug: Dict[str, object] = {}
    if apply_debug_mode:
        debug = apply_player_debug_mode(paths.system, runner=runner)

    primary = written[0]
    next_step = (
        "Restart Premiere Pro / After Effects, then open Window → Extensions → Xdrop."
    )

    if apply_debug_mode and not debug.get("enabled"):
        message = (
            f"Panel files installed to {primary}, but developer mode could not be enabled "
            f"for this user, so the hosts may not list the panel. {next_step}"
        )
        return InstallResult(
            host="adobe",
            label=label,
            ok=False,
            message=message,
            path=primary,
            scope=scope,
            restart_required=True,
            details={"paths": written, "failures": failures, "playerDebugMode": debug},
        )

    return InstallResult(
        host="adobe",
        label=label,
        ok=True,
        message=(
            f"Installed for the current user at {primary} and enabled developer mode. "
            f"{next_step}"
        ),
        path=primary,
        scope=scope,
        restart_required=True,
        details={"paths": written, "failures": failures, "playerDebugMode": debug},
    )


def cep_panel_status(
    paths: Optional[HostPlatformPaths] = None,
    scope: str = USER_SCOPE,
    runner=None,
) -> Dict[str, object]:
    """Reports whether the panel is installed and whether the hosts can currently load it."""
    paths = paths or detect()

    if paths.system not in CEP_SUPPORTED:
        return {
            "supported": False,
            "installed": False,
            "path": None,
            "scope": scope,
            "playerDebugMode": {"enabled": False, "versions": {}, "missing": []},
            "notes": ["Adobe CEP extensions are only supported on Windows and macOS."],
        }

    candidates = cep_extension_dirs(paths, scope)
    installed_at: Optional[str] = None
    for candidate in candidates:
        if (candidate / "CSXS" / "manifest.xml").is_file():
            installed_at = str(candidate)
            break

    versions = read_player_debug_mode(paths.system, runner=runner)
    missing = [version for version, state in versions.items() if state is not True]

    notes: List[str] = []
    if installed_at and missing:
        notes.append(
            "Developer mode is off for CSXS "
            + ", ".join(missing)
            + " — the hosts will not list the panel until it is enabled."
        )
    if installed_at:
        notes.append("Restart Premiere Pro / After Effects after installing.")

    return {
        "supported": True,
        "installed": installed_at is not None,
        "path": installed_at,
        "scope": scope,
        "playerDebugMode": {
            "enabled": bool(versions) and not missing,
            "versions": {k: v for k, v in versions.items()},
            "missing": missing,
        },
        "notes": notes,
    }
