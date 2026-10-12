"""
Shared pytest configuration for the Xdrop test suite.

Runtime state (SQLite database, logs, thumbnails, proxies) is redirected to a
throwaway directory *before* any `xdrop` module is imported, because
`xdrop.config` and `xdrop.logger` resolve their paths at import time.
"""

import os
import shutil
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SERVICE_ROOT = REPO_ROOT / "apps" / "desktop-service"

# Redirect all runtime state away from the developer's real %LOCALAPPDATA%\Xdrop.
_TMP_DATA_DIR = tempfile.mkdtemp(prefix="xdrop-tests-")
os.environ["XDROP_DATA_DIR"] = _TMP_DATA_DIR
# Make the user's real legacy database unreachable during tests.
os.environ.pop("RESOLVEFETCH_DATA_DIR", None)

# Make `import xdrop...` work without installing the package.
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))


def pytest_sessionfinish(session, exitstatus):  # noqa: ARG001 - pytest hook signature
    """Remove the throwaway runtime directory once the session ends."""
    shutil.rmtree(_TMP_DATA_DIR, ignore_errors=True)
