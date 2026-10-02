import os
import sys
from pathlib import Path
from typing import Tuple
from xdrop.logger import resolve_logger, errors_logger

RESOLVE_SCRIPT_TEMPLATE = '''#!/usr/bin/env python
"""
Xdrop DaVinci Resolve Integration Launcher
Appears under Workspace -> Scripts -> Utility -> Xdrop
"""
import sys
import os
import webbrowser
import urllib.request
import subprocess

SERVICE_URL = "http://localhost:8484?host=resolve"

def is_service_running():
    try:
        req = urllib.request.urlopen(f"{SERVICE_URL}/api/health", timeout=1.5)
        return req.getcode() == 200
    except Exception:
        return False

def main():
    print("[Xdrop] Launching Xdrop from DaVinci Resolve...")
    if not is_service_running():
        print("[Xdrop] Local service is not running. Starting Xdrop service...")
        script_dir = os.path.dirname(os.path.abspath(__file__))
        service_entry = os.getenv("XDROP_EXE") or os.getenv("RESOLVEFETCH_EXE") or "xdrop"
        try:
            subprocess.Popen([service_entry], shell=True)
        except Exception as e:
            print(f"[Xdrop] Could not auto-start executable: {e}")

    # Open Xdrop Companion UI in default browser / WebView
    print(f"[Xdrop] Opening user interface at: {SERVICE_URL}")
    webbrowser.open(SERVICE_URL)

if __name__ == "__main__":
    main()
'''

def get_resolve_utility_scripts_dir() -> Path:
    """Gets the path to DaVinci Resolve's Utility Scripts directory."""
    if sys.platform.startswith("win"):
        programdata = os.getenv("PROGRAMDATA", "C:\\ProgramData")
        base = Path(programdata) / "Blackmagic Design" / "DaVinci Resolve" / "Fusion" / "Scripts" / "Utility"
    elif sys.platform.startswith("darwin"):
        base = Path("/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Utility")
    else:
        base = Path("/opt/resolve/Fusion/Scripts/Utility")
    return base

def is_resolve_script_installed() -> bool:
    scripts_dir = get_resolve_utility_scripts_dir()
    return (scripts_dir / "Xdrop.py").is_file() or (scripts_dir / "ResolveFetch.py").is_file()

def install_resolve_script() -> Tuple[bool, str]:
    """Installs the Xdrop launcher script into DaVinci Resolve (and updates legacy ResolveFetch.py for compatibility)."""
    target_dir = get_resolve_utility_scripts_dir()
    target_file = target_dir / "Xdrop.py"
    legacy_file = target_dir / "ResolveFetch.py"
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(RESOLVE_SCRIPT_TEMPLATE)
        # Keep legacy launcher updated as well so existing workspace shortcuts continue working
        try:
            with open(legacy_file, "w", encoding="utf-8") as f:
                f.write(RESOLVE_SCRIPT_TEMPLATE)
        except Exception:
            pass
        resolve_logger.info(f"Installed Xdrop Resolve script to: {target_file}")
        return True, f"Installed successfully to: {target_file}"
    except Exception as e:
        msg = f"Failed to install Resolve script: {e}"
        errors_logger.error(msg)
        return False, msg
