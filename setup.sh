#!/usr/bin/env bash
# Xdrop — macOS / Linux Automated Setup
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================================================"
echo "  Xdrop — Automated Setup for macOS / Linux"
echo "========================================================================"
echo ""

# 1. Detect or auto-install Python 3
PYTHON_BIN=""
if command -v python3 &>/dev/null; then
    PYTHON_BIN="python3"
elif command -v python &>/dev/null; then
    PYTHON_BIN="python"
fi

if [ -z "$PYTHON_BIN" ]; then
    echo "[!] Python 3 not detected on this machine."
    echo "[*] Attempting automatic installation..."

    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &>/dev/null; then
            echo "[*] Installing Python 3 via Homebrew..."
            brew install python3
            PYTHON_BIN="python3"
        else
            echo "[!] Homebrew not found. Please install Homebrew or Python 3 from https://www.python.org/downloads/"
            exit 1
        fi
    elif command -v apt-get &>/dev/null; then
        # Debian / Ubuntu
        echo "[*] Installing Python 3 via apt..."
        sudo apt-get update && sudo apt-get install -y python3 python3-pip python3-venv
        PYTHON_BIN="python3"
    elif command -v dnf &>/dev/null; then
        # Fedora / RHEL
        echo "[*] Installing Python 3 via dnf..."
        sudo dnf install -y python3 python3-pip
        PYTHON_BIN="python3"
    elif command -v pacman &>/dev/null; then
        # Arch Linux
        echo "[*] Installing Python 3 via pacman..."
        sudo pacman -S --noconfirm python python-pip
        PYTHON_BIN="python3"
    else
        echo "[ERROR] Could not automatically install Python 3."
        echo "Please install Python 3.9+ using your distribution's package manager."
        exit 1
    fi
fi

echo "[OK] Using Python: $PYTHON_BIN"
echo ""

# 2. Run Python setup script
$PYTHON_BIN "$SCRIPT_DIR/scripts/setup.py"

echo ""
echo "Setup is complete! Launching Xdrop..."
exec $PYTHON_BIN apps/desktop-service/xdrop/main.py --gui
