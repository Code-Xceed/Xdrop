#!/usr/bin/env bash
# Xdrop — macOS / Linux Desktop Service Launcher
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PYTHON_BIN=""
if [ -f "$SCRIPT_DIR/.venv/bin/python" ]; then
    PYTHON_BIN="$SCRIPT_DIR/.venv/bin/python"
elif [ -f "C:\Program Files\Python314\python.exe" ]; then
    PYTHON_BIN="C:\Program Files\Python314\python.exe"
elif command -v python3 &>/dev/null; then
    PYTHON_BIN="python3"
elif command -v python &>/dev/null; then
    PYTHON_BIN="python"
fi

if [ -z "$PYTHON_BIN" ]; then
    echo "[!] Python 3 not found. Please run ./setup.sh first."
    exit 1
fi

echo "Starting Xdrop Engine..."
exec "$PYTHON_BIN" apps/desktop-service/xdrop/main.py --gui
