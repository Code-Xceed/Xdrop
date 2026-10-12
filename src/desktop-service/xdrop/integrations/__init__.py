"""
One place that installs and reports every Xdrop host integration, headlessly.

The product promise this module implements: a user opens Xdrop, clicks *Install
integrations*, and every host they own is wired up — with no administrator prompt, no console
window, and nothing to type. That promise is only keepable if the install is:

- **per-user** by default (no elevation) — see `paths.resolve_script_dir` and
  `paths.cep_extensions_dir`;
- **silent** — every child process goes through `headless.run_silent`;
- **verifiable** — each install reads back what it wrote;
- **re-runnable** — running it twice is a no-op, not an error.

Hosts and what "installed" means for each:

| Host | Artifact | Reaches the host via |
| --- | --- | --- |
| DaVinci Resolve | `Xdrop.py` in a `Scripts/Utility` folder | Workspace → Scripts → Utility |
| Premiere Pro | CEP panel folder + `PlayerDebugMode` | Window → Extensions → Xdrop |
| After Effects | same CEP panel folder (one manifest serves both) | Window → Extensions → Xdrop |

Adobe's two hosts share a single panel, which is why `premiere` and `aftereffects` map to one
install step instead of two.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Sequence

from .cep import (
    apply_player_debug_mode,
    cep_panel_status,
    install_cep_panel,
    player_debug_mode_commands,
    read_player_debug_mode,
)
from .headless import run_silent
from .paths import (
    CEP_SUPPORTED,
    SERVICE_URL,
    SYSTEM_SCOPE,
    USER_SCOPE,
    HostPlatformPaths,
    cep_extension_dirs,
    cep_extensions_dir,
    detect,
    resolve_script_dir,
)
from .resolve import (
    build_resolve_script_content,
    install_resolve_script,
    resolve_script_status,
)
from .results import InstallResult, summarise

__all__ = [
    "ADOBE_HOSTS",
    "SUPPORTED_HOSTS",
    "apply_player_debug_mode",
    "build_resolve_script_content",
    "cep_panel_status",
    "install_all_integrations",
    "install_integrations",
    "integrations_status",
    "player_debug_mode_commands",
    "read_player_debug_mode",
    "resolve_script_status",
    "SERVICE_URL",
]

#: Adobe's two hosts both live in the single CEP panel.
ADOBE_HOSTS = ("premiere", "aftereffects")

#: Everything installable, in the order the UI lists it.
SUPPORTED_HOSTS = ("resolve", "premiere", "aftereffects")

_IMPLIED_HOSTS = {"adobe": ADOBE_HOSTS, "cep": ADOBE_HOSTS, "ae": ("aftereffects",)}
_LABELS = {
    "resolve": "DaVinci Resolve",
    "premiere": "Adobe Premiere Pro",
    "aftereffects": "Adobe After Effects",
}


def _normalise_hosts(hosts: Optional[Iterable[str]]) -> List[str]:
    """Expands aliases and drops anything unknown, preserving a stable order."""
    if hosts is None:
        return list(SUPPORTED_HOSTS)

    requested: List[str] = []
    for raw in hosts:
        key = str(raw).strip().lower()
        for expanded in _IMPLIED_HOSTS.get(key, (key,)):
            if expanded in SUPPORTED_HOSTS and expanded not in requested:
                requested.append(expanded)

    return [host for host in SUPPORTED_HOSTS if host in requested]


def install_integrations(
    hosts: Optional[Sequence[str]] = None,
    scope: str = USER_SCOPE,
    paths: Optional[HostPlatformPaths] = None,
    runner=None,
) -> Dict[str, object]:
    """Installs the requested hosts and returns a result per host, plus a fresh status.

    The Adobe panel is installed at most once even when both Adobe hosts are requested. A
    failure in one host never prevents the others: each result stands on its own, and
    `success` is true only when every requested host succeeded.
    """
    resolved_paths = paths or detect()
    requested = _normalise_hosts(hosts)
    results: List[InstallResult] = []

    if "resolve" in requested:
        results.append(
            install_resolve_script(paths=resolved_paths, scope=scope)
        )

    if any(host in requested for host in ADOBE_HOSTS):
        results.append(
            install_cep_panel(
                paths=resolved_paths,
                scope=scope,
                apply_debug_mode=True,
                runner=runner or run_silent,
            )
        )

    if not results:
        return {
            "success": False,
            "message": "No installable hosts were requested.",
            "results": [],
            "status": integrations_status(paths=resolved_paths, scope=scope, runner=runner),
        }

    status = integrations_status(paths=resolved_paths, scope=scope, runner=runner or run_silent)
    return {
        "success": all(result.ok for result in results),
        "message": summarise(results),
        "results": [result.to_dict() for result in results],
        "status": status,
    }


def install_all_integrations(
    scope: str = USER_SCOPE,
    paths: Optional[HostPlatformPaths] = None,
    runner=None,
) -> Dict[str, object]:
    """The one-click path: resolve + Premiere Pro + After Effects, per-user, no admin."""
    return install_integrations(hosts=None, scope=scope, paths=paths, runner=runner)


def integrations_status(
    paths: Optional[HostPlatformPaths] = None,
    scope: str = USER_SCOPE,
    runner=None,
) -> Dict[str, object]:
    """Full, read-only picture of every integration: what is installed, where, and what is not.

    Used by the panel's Diagnostics section, so it reports the boring truth — including the
    paths that were checked and found empty — rather than a single boolean.
    """
    resolved_paths = paths or detect()
    resolve_status = resolve_script_status(resolved_paths)
    adobe_status = cep_panel_status(resolved_paths, scope=scope, runner=runner)

    hosts: List[Dict[str, object]] = [
        {
            "host": "resolve",
            "label": _LABELS["resolve"],
            "installed": bool(resolve_status["installed"]),
            "path": resolve_status["path"],
            "scope": resolve_status["scope"] or scope,
            "requiresAdmin": False,
            "restartRequired": bool(resolve_status["installed"]),
            "notes": resolve_status["notes"],
            "checkedPaths": [loc["path"] for loc in resolve_status["locations"]],
        }
    ]

    for host in ADOBE_HOSTS:
        hosts.append(
            {
                "host": host,
                "label": _LABELS[host],
                "installed": bool(adobe_status["installed"]),
                "path": adobe_status["path"],
                "scope": scope,
                "requiresAdmin": False,
                "restartRequired": bool(adobe_status["installed"]),
                "notes": adobe_status["notes"],
                "checkedPaths": [str(p) for p in cep_extension_dirs(resolved_paths, scope)],
            }
        )

    debug = adobe_status.get("playerDebugMode", {})

    return {
        "platform": resolved_paths.system,
        "scope": scope,
        "requiresAdmin": False,
        "hosts": hosts,
        "playerDebugMode": debug,
        "installationPaths": {
            "resolveUser": str(resolve_script_dir(resolved_paths, USER_SCOPE)),
            "resolveSystem": str(resolve_script_dir(resolved_paths, SYSTEM_SCOPE)),
            "adobeUser": (
                None
                if cep_extensions_dir(resolved_paths, USER_SCOPE) is None
                else str(cep_extensions_dir(resolved_paths, USER_SCOPE))
            ),
        },
        "cepSupported": resolved_paths.system in CEP_SUPPORTED,
        "details": {"resolve": resolve_status, "adobe": adobe_status},
    }
