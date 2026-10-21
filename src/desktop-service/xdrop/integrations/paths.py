"""
Filesystem locations for every host Xdrop integrates with.

Two rules drive this module:

1. **Per-user first.** Resolve reads scripts from a per-user folder and Adobe reads CEP
   extensions from a per-user folder. Writing there needs no administrator rights, so the
   default install never shows a UAC prompt. The all-users folders still exist here because
   a shared machine may want them, but they are opt-in (`scope="system"`).
2. **One source of truth.** The paths used by the installer, the status endpoint and the
   setup script all come from here, so they cannot drift apart.

Path references:
- Resolve script folders — Blackmagic's *Scripting API Introduction*
  (https://resolvedevdoc.readthedocs.io/en/latest/API_intro.html)
- CEP extensions folder — Adobe's *Package, Distribute, Install Guide*
  (https://github.com/Adobe-CEP/Getting-Started-guides)
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

# --- Constants -----------------------------------------------------------------------

WINDOWS = "windows"
MACOS = "macos"
LINUX = "linux"

USER_SCOPE = "user"
SYSTEM_SCOPE = "system"

#: Bundle id of the shipped Adobe CEP panel (`apps/premiere-plugin/CSXS/manifest.xml`).
CEP_EXTENSION_ID = "com.xdrop.panel"

#: Bundle ids this project used before the rename. Kept in sync so an existing docked
#: panel in someone's workspace keeps working after an upgrade.
LEGACY_CEP_EXTENSION_IDS: Tuple[str, ...] = ("com.xdrop.premiere", "com.resolvefetch.premiere")

#: CSXS major versions seen in the field. Premiere Pro 2020+ is CSXS 9+; newer hosts prefer
#: higher numbers. Enabling debug mode on versions a host does not use is harmless (one
#: HKCU value, no admin), and missing the right one makes the panel invisible, so the whole
#: range is written.
CSXS_VERSIONS: Tuple[str, ...] = ("9", "10", "11", "12", "13", "14", "15", "16")

#: The companion service both the Resolve launcher script and the CEP panel talk to.
SERVICE_URL = "http://127.0.0.1:8484"

#: The script/panel name a user sees in each host's menu.
LAUNCHER_NAME = "Xdrop"

LEGACY_LAUNCHER_NAME = "ResolveFetch"


@dataclass(frozen=True)
class HostPlatformPaths:
    """Resolved root directories for one user on one machine.

    Built by `detect()` from the real environment, or by `for_system()` in tests.
    """

    system: str
    home: Path
    #: Windows `%APPDATA%`; macOS `~/Library/Application Support`. Used for Adobe CEP.
    appdata: Path
    #: Windows `%PROGRAMDATA%`. Only relevant for the all-users Resolve install.
    program_data: Path

    @property
    def is_windows(self) -> bool:
        return self.system == WINDOWS

    @property
    def is_macos(self) -> bool:
        return self.system == MACOS

    @property
    def is_linux(self) -> bool:
        return self.system == LINUX


def current_system() -> str:
    """Maps `sys.platform` onto one of the three supported platform names."""
    if sys.platform.startswith("win"):
        return WINDOWS
    if sys.platform.startswith("darwin"):
        return MACOS
    return LINUX


def for_system(
    system: str,
    home: Path,
    appdata: Optional[Path] = None,
    program_data: Optional[Path] = None,
) -> HostPlatformPaths:
    """Builds a `HostPlatformPaths` without reading the environment.

    This is what makes path selection testable: a test can ask for "Windows, home at
    /tmp/me" and assert the exact directory the installer would write to.
    """
    home = Path(home)
    if appdata is None:
        if system == WINDOWS:
            appdata = home / "AppData" / "Roaming"
        elif system == MACOS:
            appdata = home / "Library" / "Application Support"
        else:
            appdata = home / ".config"
    if program_data is None:
        program_data = Path("/var/lib") if system != WINDOWS else Path("C:/ProgramData")
    return HostPlatformPaths(
        system=system,
        home=home,
        appdata=Path(appdata),
        program_data=Path(program_data),
    )


def detect() -> HostPlatformPaths:
    """Reads the live environment and returns this user's platform paths.

    Set `XDROP_PATH_ROOT` to resolve every target inside one sandbox directory instead of the
    real profile:

    ```
    XDROP_PATH_ROOT=/tmp/xdrop-sandbox
    # -> home=/tmp/xdrop-sandbox/home, appdata=/tmp/xdrop-sandbox/appdata, ...
    ```

    That exists so an install can be exercised end-to-end — including automated runs — without
    touching a real editor installation, and so a deployment can target a different profile.
    """
    system = current_system()
    root_override = os.getenv("XDROP_PATH_ROOT")
    if root_override:
        root = Path(root_override)
        return for_system(
            system,
            home=root / "home",
            appdata=root / ("appdata" if system != LINUX else "config"),
            program_data=root / "programdata",
        )

    home = Path.home()

    if system == WINDOWS:
        appdata = os.getenv("APPDATA") or str(home / "AppData" / "Roaming")
        program_data = os.getenv("PROGRAMDATA") or "C:\\ProgramData"
    elif system == MACOS:
        appdata = str(home / "Library" / "Application Support")
        program_data = "/Library/Application Support"
    else:
        appdata = os.getenv("XDG_CONFIG_HOME") or str(home / ".config")
        program_data = "/opt"

    return for_system(
        system,
        home=home,
        appdata=Path(appdata),
        program_data=Path(program_data),
    )


# --- DaVinci Resolve ----------------------------------------------------------------


def resolve_script_dirs(paths: HostPlatformPaths) -> Tuple[Path, Path]:
    """Returns `(per_user_dir, all_users_dir)` for Resolve's Utility scripts.

    Resolve scans both on startup and lists everything under
    **Workspace → Scripts → Utility**. The per-user folder requires no elevation; the
    all-users folder does on Windows and macOS.
    """
    if paths.is_windows:
        per_user = (
            paths.appdata
            / "Blackmagic Design"
            / "DaVinci Resolve"
            / "Support"
            / "Fusion"
            / "Scripts"
            / "Utility"
        )
        all_users = (
            paths.program_data
            / "Blackmagic Design"
            / "DaVinci Resolve"
            / "Fusion"
            / "Scripts"
            / "Utility"
        )
    elif paths.is_macos:
        per_user = (
            paths.home
            / "Library"
            / "Application Support"
            / "Blackmagic Design"
            / "DaVinci Resolve"
            / "Fusion"
            / "Scripts"
            / "Utility"
        )
        all_users = (
            paths.program_data
            / "Blackmagic Design"
            / "DaVinci Resolve"
            / "Fusion"
            / "Scripts"
            / "Utility"
        )
    else:
        per_user = (
            paths.home / ".local" / "share" / "DaVinciResolve" / "Fusion" / "Scripts" / "Utility"
        )
        # Blackmagic's Linux layout is flat under /opt/resolve.
        all_users = Path("/opt/resolve/Fusion/Scripts/Utility")

    return per_user, all_users


def resolve_script_dir(paths: HostPlatformPaths, scope: str = USER_SCOPE) -> Path:
    """The single directory `scope` installs into. Defaults to the admin-free one."""
    per_user, all_users = resolve_script_dirs(paths)
    return all_users if scope == SYSTEM_SCOPE else per_user


def resolve_script_files(paths: HostPlatformPaths, scope: str = USER_SCOPE) -> Tuple[Path, ...]:
    """Both the current and the legacy launcher filenames Resolve will list."""
    directory = resolve_script_dir(paths, scope)
    return (
        directory / f"{LAUNCHER_NAME}.py",
        directory / f"{LEGACY_LAUNCHER_NAME}.py",
    )


# --- Adobe CEP ----------------------------------------------------------------------

#: CEP does not exist on Linux, so these stay Windows/macOS only.
CEP_SUPPORTED = (WINDOWS, MACOS)


def cep_extensions_dir(paths: HostPlatformPaths, scope: str = USER_SCOPE) -> Optional[Path]:
    """Adobe's CEP `extensions` folder, or `None` where CEP does not exist (Linux).

    `scope="user"` is the normal case: every user of the machine gets their own panel and
    no administrator rights are involved. The system folder exists for managed deployments
    and is deliberately not the default.
    """
    if paths.system not in CEP_SUPPORTED:
        return None

    if scope == SYSTEM_SCOPE and paths.is_windows:
        return Path("C:/Program Files (x86)/Common Files/Adobe/CEP/extensions")

    return paths.appdata / "Adobe" / "CEP" / "extensions"


def cep_extension_dir(
    paths: HostPlatformPaths,
    extension_id: str = CEP_EXTENSION_ID,
    scope: str = USER_SCOPE,
) -> Optional[Path]:
    """The install destination for one CEP extension id."""
    root = cep_extensions_dir(paths, scope)
    return None if root is None else root / extension_id


def cep_extension_dirs(
    paths: HostPlatformPaths,
    scope: str = USER_SCOPE,
) -> Tuple[Path, ...]:
    """Every destination an install writes: the current bundle id plus the legacy ones."""
    ids = (CEP_EXTENSION_ID,) + LEGACY_CEP_EXTENSION_IDS
    dirs = [cep_extension_dir(paths, ext_id, scope) for ext_id in ids]
    return tuple(d for d in dirs if d is not None)


# --- Repo layout --------------------------------------------------------------------


def desktop_service_root() -> Path:
    """`apps/desktop-service` — the directory holding the `xdrop` package."""
    return Path(__file__).resolve().parents[2]


def repo_root() -> Path:
    """Repository root, derived from this file's location."""
    return Path(__file__).resolve().parents[4]


def find_cep_source() -> Optional[Path]:
    """Locates the CEP panel source that gets copied into Adobe's folder.

    Works from a source checkout and from a PyInstaller bundle, which is why several
    candidate roots are checked instead of one computed path.
    """
    here = Path(__file__).resolve()

    candidates = [
        repo_root() / "src" / "premiere-plugin",
        repo_root() / "apps" / "premiere-plugin",
        here.parents[3] / "premiere-plugin",
        Path.cwd() / "src" / "premiere-plugin",
        Path.cwd() / "apps" / "premiere-plugin",
        Path.cwd() / "premiere-plugin",
    ]

    # Frozen builds unpack into sys._MEIPASS.
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.insert(0, Path(meipass) / "apps" / "premiere-plugin")
        candidates.insert(0, Path(meipass) / "premiere-plugin")

    for candidate in candidates:
        if (candidate / "CSXS" / "manifest.xml").is_file():
            return candidate
    return None
