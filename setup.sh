#!/usr/bin/env bash
# Xdrop — macOS / Linux Automated Setup
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================================================"
echo "  Xdrop — Automated Setup for macOS / Linux"
echo "========================================================================"
echo ""

# 1. Detect Python 3
PYTHON_BIN=""
if command -v python3 &>/dev/null; then
    PYTHON_BIN="python3"
elif command -v python &>/dev/null; then
    PYTHON_BIN="python"
else
    echo "Error: Python 3 is not installed or not in PATH."
    echo "Please install Python 3.9+ via your package manager (e.g. brew install python3 or apt install python3)"
    exit 1
fi

# 2. Run Python setup script
$PYTHON_BIN "$SCRIPT_DIR/scripts/setup.py"

echo ""
echo "Setup is complete!"
echo "To start Xdrop, run: $PYTHON_BIN apps/desktop-service/xdrop/main.py --gui"
