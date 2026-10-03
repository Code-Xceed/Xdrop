import os
import sys
from pathlib import Path
from typing import Tuple
from xdrop.logger import resolve_logger, errors_logger

def build_resolve_script_content() -> str:
    cur = Path(__file__).resolve()
    # installer.py -> resolve -> xdrop -> desktop-service -> apps -> repo root
    repo_root = cur.parents[4]
    run_bat = repo_root / "run.bat"
    run_sh = repo_root / "run.sh"
    main_py = cur.parents[1] / "main.py"
    py_exe = sys.executable

    return f'''#!/usr/bin/env python
"""
Xdrop DaVinci Resolve Integration Launcher
Appears under Workspace -> Scripts -> Utility -> Xdrop
"""
import sys
import os
import time
import webbrowser
import urllib.request
import subprocess

SERVICE_URL = "http://127.0.0.1:8484?host=resolve"
HEALTH_URL = "http://127.0.0.1:8484/api/health"

PYTHON_EXE = {py_exe!r}
MAIN_PY = {str(main_py)!r}
RUN_BAT = {str(run_bat)!r}
RUN_SH = {str(run_sh)!r}

def is_service_running():
    try:
        req = urllib.request.urlopen(HEALTH_URL, timeout=1.5)
        return req.getcode() == 200
    except Exception:
        return False

def main():
    print("[Xdrop] Connecting to Xdrop Engine...")
    if not is_service_running():
        print("[Xdrop] Engine is not currently running. Auto-starting background service...")
        started = False

        flags = 0
        if sys.platform == "win32":
            if hasattr(subprocess, "CREATE_NO_WINDOW"):
                flags |= subprocess.CREATE_NO_WINDOW
            if hasattr(subprocess, "DETACHED_PROCESS"):
                flags |= subprocess.DETACHED_PROCESS
            else:
                flags |= 0x00000008

        # 1. Direct python background launch
        if os.path.isfile(MAIN_PY):
            try:
                interpreter = PYTHON_EXE if os.path.isfile(PYTHON_EXE) else sys.executable
                kwargs = {{
                    "cwd": os.path.dirname(MAIN_PY),
                    "stdin": subprocess.DEVNULL,
                    "stdout": subprocess.DEVNULL,
                    "stderr": subprocess.DEVNULL
                }}
                if sys.platform == "win32":
                    kwargs["creationflags"] = flags
                else:
                    kwargs["start_new_session"] = True
                subprocess.Popen([interpreter, MAIN_PY, "--gui"], **kwargs)
                started = True
            except Exception as e:
                print(f"[Xdrop] Auto-start error: {{e}}")

        # 2. Try launching run.bat if on Windows
        if not started and sys.platform == "win32" and os.path.isfile(RUN_BAT):
            try:
                subprocess.Popen(
                    ["cmd.exe", "/c", RUN_BAT],
                    cwd=os.path.dirname(RUN_BAT),
                    creationflags=flags,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                started = True
            except Exception:
                pass
        elif not started and sys.platform != "win32" and os.path.isfile(RUN_SH):
            try:
                subprocess.Popen(
                    ["bash", RUN_SH],
                    cwd=os.path.dirname(RUN_SH),
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True
                )
                started = True
            except Exception:
                pass

        # Wait up to 6 seconds for engine to come online
        for _ in range(12):
            if is_service_running():
                print("[Xdrop] Background engine is online!")
                break
            time.sleep(0.5)

    # Open Companion UI
    print(f"[Xdrop] Opening user interface at: {{SERVICE_URL}}")
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
    """Installs the self-starting Xdrop launcher script into DaVinci Resolve."""
    target_dir = get_resolve_utility_scripts_dir()
    target_file = target_dir / "Xdrop.py"
    legacy_file = target_dir / "ResolveFetch.py"
    script_content = build_resolve_script_content()
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(script_content)
        # Keep legacy launcher updated as well so existing workspace shortcuts continue working
        try:
            with open(legacy_file, "w", encoding="utf-8") as f:
                f.write(script_content)
        except Exception:
            pass
        resolve_logger.info(f"Installed Xdrop Resolve script to: {target_file}")
        return True, f"Installed successfully to: {target_file}"
    except Exception as e:
        msg = f"Failed to install Resolve script: {e}"
        errors_logger.error(msg)
        return False, msg
