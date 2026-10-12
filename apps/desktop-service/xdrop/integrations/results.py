"""Shared result type for every integration install/status call."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .paths import USER_SCOPE


@dataclass
class InstallResult:
    """Outcome of installing one host integration.

    The API returns these verbatim, so every field is JSON-safe and human-readable. When
    something fails, `message` says what failed and `details` carries the raw evidence
    (return codes, stderr, attempted paths) rather than swallowing it.
    """

    host: str
    label: str
    ok: bool
    message: str
    path: Optional[str] = None
    scope: str = USER_SCOPE
    #: True when the only way forward is running as administrator. The default install is
    #: designed so this is never set.
    requires_admin: bool = False
    #: True when the host must be restarted before the new files are picked up.
    restart_required: bool = False
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "host": self.host,
            "label": self.label,
            "ok": self.ok,
            "message": self.message,
            "path": self.path,
            "scope": self.scope,
            "requiresAdmin": self.requires_admin,
            "restartRequired": self.restart_required,
            "details": self.details,
        }


def summarise(results: List[InstallResult]) -> str:
    """One line an operator can act on, without reading the whole result list."""
    if not results:
        return "Nothing to install."
    failed = [r for r in results if not r.ok]
    if not failed:
        return "All integrations installed for the current user (no administrator rights needed)."
    return "Installed with errors: " + "; ".join(f"{r.label}: {r.message}" for r in failed)
