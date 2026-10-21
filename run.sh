#!/usr/bin/env bash
# Xdrop — macOS / Linux Desktop Service Launcher
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
export PYTHONPATH="$DIR/src/desktop-service:$PYTHONPATH"

PYTHON_BIN=""
if [ -f "$DIR/.venv/bin/python" ]; then
    PYTHON_BIN="$DIR/.venv/bin/python"
elif command -v python3 &>/dev/null; then
    PYTHON_BIN="python3"
elif [ -f "/opt/homebrew/bin/python3" ]; then
    PYTHON_BIN="/opt/homebrew/bin/python3"
elif [ -f "/usr/local/bin/python3" ]; then
    PYTHON_BIN="/usr/local/bin/python3"
elif [ -f "/usr/bin/python3" ]; then
    PYTHON_BIN="/usr/bin/python3"
elif command -v python &>/dev/null; then
    PYTHON_BIN="python"
fi

if [ -z "$PYTHON_BIN" ]; then
    echo "[!] Python 3 not found. Please install Python 3."
    exit 1
fi

echo "Starting Xdrop Engine..."
exec "$PYTHON_BIN" -m xdrop.main "$@"
