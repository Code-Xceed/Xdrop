#!/usr/bin/env bash
# Xdrop — Automated Updater
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================================================"
echo "  Xdrop — Automated Updater"
echo "========================================================================"
echo ""

PYTHON_BIN=""
if command -v python3 &>/dev/null; then
    PYTHON_BIN="python3"
elif command -v python &>/dev/null; then
    PYTHON_BIN="python"
else
    echo "Python 3 not found. Running setup.sh..."
    exec ./setup.sh
fi

if [ -d ".git" ] && command -v git &>/dev/null; then
    echo "[1/4] Pulling latest updates from GitHub..."
    git pull origin master || true
fi

echo "[2/4] Updating social media extractors (yt-dlp)..."
$PYTHON_BIN -m pip install --upgrade yt-dlp

echo "[3/4] Updating dependencies..."
$PYTHON_BIN -m pip install --upgrade -r requirements.txt

echo "[4/4] Synchronizing editor scripts and settings..."
$PYTHON_BIN "$SCRIPT_DIR/scripts/setup.py"

echo ""
echo "Xdrop is up to date!"
