"""
Back-compatibility shim.

The Resolve install moved to `xdrop/integrations/resolve.py` so that Resolve, Premiere Pro and
After Effects share one install path, one status report and one set of per-user locations.

These four names are kept because `xdrop/setup.py` and older callers import them. The
behaviour changed in one important way: `install_resolve_script()` now installs into
Resolve's **per-user** folder, which needs no administrator rights, instead of the all-users
folder under `C:\\ProgramData`.

New code should import from `xdrop.integrations` directly.
"""

from pathlib import Path
from typing import Tuple

from xdrop.integrations.paths import SYSTEM_SCOPE, detect, resolve_script_dir
from xdrop.integrations.resolve import build_resolve_script_content  # noqa: F401  (re-export)
from xdrop.integrations.resolve import install_resolve_script as _install_resolve_script
from xdrop.integrations.resolve import resolve_script_status

__all__ = [
    "build_resolve_script_content",
    "get_resolve_utility_scripts_dir",
    "install_resolve_script",
    "is_resolve_script_installed",
]


def get_resolve_utility_scripts_dir() -> Path:
    """The all-users `Scripts/Utility` directory.

    Kept for callers that want to inspect or clean up a legacy system-wide install. New
    installs go to the per-user directory instead — see `install_resolve_script`.
    """
    return resolve_script_dir(detect(), SYSTEM_SCOPE)


def is_resolve_script_installed() -> bool:
    """True when the launcher exists in any folder Resolve scans (per-user or all-users)."""
    return bool(resolve_script_status()["installed"])


def install_resolve_script() -> Tuple[bool, str]:
    """Legacy tuple-returning wrapper around the per-user install."""
    result = _install_resolve_script()
    return result.ok, result.message
