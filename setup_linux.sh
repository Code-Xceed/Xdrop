#!/usr/bin/env bash
# ==============================================================================
# Xdrop — Linux 1-Click Setup & Extension Installer
# ==============================================================================
# Configures DaVinci Resolve, Blender VSE, and the background desktop service
# without requiring root / sudo rights.
# ==============================================================================

set -e

# Terminal colors
CYAN='\033[96m'
GREEN='\033[92m'
YELLOW='\033[93m'
RED='\033[91m'
BOLD='\033[1m'
RESET='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$SCRIPT_DIR"

echo -e "${CYAN}${BOLD}=== Xdrop Linux Universal Installer ===${RESET}"

# 1. Locate Python 3
PYTHON_BIN=""
for cand in python3 /usr/bin/python3 /usr/local/bin/python3; do
    if command -v "$cand" >/dev/null 2>&1; then
        PYTHON_BIN="$cand"
        break
    fi
done

if [ -z "$PYTHON_BIN" ]; then
    echo -e "${RED}[X] Python 3 was not found on your system.${RESET}"
    echo -e "    Please install Python 3 using your distribution's package manager:"
    echo -e "      Ubuntu/Debian: sudo apt update && sudo apt install python3 python3-pip"
    echo -e "      Fedora:        sudo dnf install python3 python3-pip"
    echo -e "      Arch:          sudo pacman -S python python-pip"
    exit 1
fi

PY_VER=$("$PYTHON_BIN" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo -e "${GREEN}[+] Detected Python ${PY_VER}: ${PYTHON_BIN}${RESET}"

# 2. Check / Install essential dependencies
echo -e "${CYAN}[i] Checking dependencies...${RESET}"
"$PYTHON_BIN" -c "import fastapi, uvicorn, yt_dlp, pydantic" 2>/dev/null || {
    echo -e "${YELLOW}[!] Installing required packages (user space)...${RESET}"
    "$PYTHON_BIN" -m pip install --quiet --user fastapi uvicorn "yt-dlp>=2025.1.0" pydantic httpx websockets pillow || {
        echo -e "${YELLOW}[!] Warning: Could not pip install all packages automatically. Proceeding...${RESET}"
    }
}

# 3. Ensure permissions
chmod +x "$SCRIPT_DIR/run.sh" 2>/dev/null || true

# 4. Launch Master Installer
export PYTHONPATH="$SCRIPT_DIR/src/desktop-service:$PYTHONPATH"
"$PYTHON_BIN" "$SCRIPT_DIR/src/tools/installer.py" "$@"

echo -e "\n${GREEN}${BOLD}✓ Setup complete! You can close this terminal window.${RESET}\n"
