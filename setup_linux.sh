#!/usr/bin/env bash
# ==============================================================================
# Xdrop — Linux Dedicated Setup & Extension Installer
# ==============================================================================
# Configures DaVinci Resolve or Blender VSE and the background desktop service
# without requiring root/sudo privileges.
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

echo -e "${CYAN}${BOLD}=== Xdrop Linux Dedicated Setup ===${RESET}"

# 1. Locate Python 3
PYTHON_BIN=""
for cand in python3 python /usr/bin/python3 /usr/local/bin/python3; do
    if command -v "$cand" >/dev/null 2>&1; then
        PYTHON_BIN="$cand"
        break
    fi
done

if [ -z "$PYTHON_BIN" ]; then
    echo -e "${RED}[X] Python 3 was not found on your system.${RESET}"
    echo -e "    Please install Python 3 via your package manager:"
    echo -e "    Ubuntu/Debian: sudo apt update && sudo apt install -y python3 python3-pip"
    echo -e "    Fedora/RHEL:   sudo dnf install -y python3 python3-pip"
    echo -e "    Arch Linux:    sudo pacman -S python python-pip"
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

# 4. Launch Appropriate Installer (Dedicated Adobe or Resolve)
export PYTHONPATH="$SCRIPT_DIR/src:$SCRIPT_DIR/src/desktop-service:$PYTHONPATH"

INSTALLER_SCRIPT=""
ARGS=()

for arg in "$@"; do
    case "$arg" in
        --adobe|--premiere)
            INSTALLER_SCRIPT="$SCRIPT_DIR/src/tools/installer_premiere.py"
            ;;
        --resolve|--davinci)
            INSTALLER_SCRIPT="$SCRIPT_DIR/src/tools/installer_resolve.py"
            ;;
        *)
            ARGS+=("$arg")
            ;;
    esac
done

if [ -z "$INSTALLER_SCRIPT" ]; then
    echo -e "\n${BOLD}${CYAN}Select your target editor to configure:${RESET}"
    echo "  1) DaVinci Resolve Setup"
    echo "  2) Adobe Premiere Pro Setup"
    read -p "Enter choice [1 or 2]: " choice
    case "$choice" in
        2)
            INSTALLER_SCRIPT="$SCRIPT_DIR/src/tools/installer_premiere.py"
            ;;
        *)
            INSTALLER_SCRIPT="$SCRIPT_DIR/src/tools/installer_resolve.py"
            ;;
    esac
fi

"$PYTHON_BIN" "$INSTALLER_SCRIPT" "${ARGS[@]}"

echo -e "\n${GREEN}${BOLD}✓ Setup complete! You can close this terminal window.${RESET}\n"
