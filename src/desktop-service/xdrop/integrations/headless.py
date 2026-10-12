"""
Every child process Xdrop starts during an install is started through here.

"Headless" is a product requirement here, not a detail. A user who clicks *Install
integrations* in the panel must not see a console window flash on Windows, must not be
asked for administrator rights, and must not be told to open a terminal. So:

- Windows children get `CREATE_NO_WINDOW`, which allocates no console at all, so `reg`
  and any other helper runs invisibly.
- POSIX children start in their own session (`start_new_session=True`) so they ignore the
  parent's terminal signals.
- stdin is always `DEVNULL`, so nothing can block waiting for input.
- A non-zero exit status is returned, never raised: a failed registry write is reported in
  the install result, it does not abort the rest of the install or crash the request.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional, Sequence

from xdrop.logger import app_logger

#: Windows `CREATE_NO_WINDOW`; absent from non-Windows `subprocess`.
_CREATE_NO_WINDOW = 0x08000000

#: Exit status used when a command could not be started at all (missing binary).
START_FAILED = 127


def silent_kwargs() -> Dict[str, object]:
    """Keyword arguments that make a child process invisible and non-interactive."""
    kwargs: Dict[str, object] = {
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
    }
    if sys.platform == "win32":
        kwargs["creationflags"] = _CREATE_NO_WINDOW
    else:
        kwargs["start_new_session"] = True
    return kwargs


def run_silent(
    argv: Sequence[str],
    timeout: float = 20.0,
    cwd: Optional[Path] = None,
) -> subprocess.CompletedProcess:
    """Runs `argv` with no visible window and never raises for a non-zero exit.

    A command that cannot be started (binary missing) comes back as `START_FAILED` with the
    underlying error text in `stderr`, so callers can report a useful message instead of a
    traceback.
    """
    kwargs = silent_kwargs()
    if cwd is not None:
        kwargs["cwd"] = str(cwd)

    try:
        return subprocess.run(list(argv), timeout=timeout, check=False, **kwargs)  # type: ignore[arg-type]
    except FileNotFoundError as exc:
        app_logger.warning("Integration helper not found: %s (%s)", argv[0], exc)
        return subprocess.CompletedProcess(list(argv), START_FAILED, "", str(exc))
    except subprocess.TimeoutExpired as exc:
        app_logger.warning("Integration helper timed out: %s", " ".join(map(str, argv)))
        return subprocess.CompletedProcess(list(argv), START_FAILED, "", f"timed out after {timeout}s: {exc}")
    except OSError as exc:  # pragma: no cover - depends on host permissions
        app_logger.warning("Integration helper failed to start: %s (%s)", argv[0], exc)
        return subprocess.CompletedProcess(list(argv), START_FAILED, "", str(exc))


def decode(stream: object) -> str:
    """Normalises a captured stdout/stderr value into text."""
    if stream is None:
        return ""
    if isinstance(stream, bytes):
        return stream.decode("utf-8", errors="replace")
    return str(stream)


def run_silent_argv(argv: Sequence[str], timeout: float = 20.0) -> Dict[str, object]:
    """Convenience wrapper returning a plain dict, handy for JSON results."""
    proc = run_silent(argv, timeout=timeout)
    return {
        "argv": list(argv),
        "returncode": proc.returncode,
        "ok": proc.returncode == 0,
        "stdout": decode(proc.stdout).strip(),
        "stderr": decode(proc.stderr).strip(),
    }
