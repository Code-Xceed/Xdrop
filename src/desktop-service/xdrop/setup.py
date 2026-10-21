#!/usr/bin/env python3
"""
Xdrop — Universal One-Click Automated Setup & Hardware Configuration
Detects installed NLE video editors (DaVinci Resolve, Adobe Premiere Pro, After Effects),
configures plugins and registry settings, auto-probes GPU hardware encoders,
discovers/downloads FFmpeg, and tailors all settings specifically for this PC.
"""

import os
import sys
import shutil
import platform
import subprocess
import urllib.request
import json
from pathlib import Path

# Fix Windows terminal encoding to avoid UnicodeEncodeError on cp1252
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
DESKTOP_SERVICE_DIR = (
    ROOT_DIR / "src" / "desktop-service"
    if (ROOT_DIR / "src" / "desktop-service").exists()
    else ROOT_DIR / "apps" / "desktop-service"
)
sys.path.insert(0, str(DESKTOP_SERVICE_DIR))

# ANSI Color Codes
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"

# Safe status marks
CHECK = "[+]"
CROSS = "[X]"
INFO = "[i]"

def print_banner():
    banner = f"""
{CYAN}{BOLD}========================================================================
   __   __      _                 
   \\ \\ / /     | |                
    \\ V /  ____| | _ __  ___  _ __  
    /   \\ / _  | |/ / _ \\/ _ \\| '_ \\ 
   / /^\\ \\ (_| | | < (_) | (_) | |_) |
  /_/   \\_\\__,_|_|\\_\\___/ \\___/| .__/ 
                               | |    
  Universal Media Importer     |_|    
========================================================================{RESET}
{BOLD}Automated Hardware, Editor & Environment Setup{RESET}
"""
    print(banner)

def check_python_version() -> bool:
    print(f"\n{BOLD}[1/7] Checking Python Environment...{RESET}")
    major, minor = sys.version_info.major, sys.version_info.minor
    print(f"      Python version: {major}.{minor}.{sys.version_info.micro} ({platform.architecture()[0]})")
    if major < 3 or (major == 3 and minor < 9):
        print(f"      {RED}[ERROR] Python 3.9 or higher is required. Please update Python.{RESET}")
        return False
    print(f"      {GREEN}{CHECK} Python version is compatible.{RESET}")
    return True

def install_python_dependencies() -> bool:
    print(f"\n{BOLD}[2/7] Installing Python Dependencies...{RESET}")
    req_file = ROOT_DIR / "requirements.txt"
    if not req_file.exists():
        req_file = DESKTOP_SERVICE_DIR / "requirements.txt"

    if not req_file.exists():
        print(f"      {YELLOW}[!] requirements.txt not found, skipping pip install.{RESET}")
        return True

    print(f"      Running: {sys.executable} -m pip install -r {req_file.name}")
    try:
        res = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(req_file)],
            capture_output=True,
            text=True,
            check=False
        )
        if res.returncode == 0:
            print(f"      {GREEN}[+] Python dependencies verified & installed.{RESET}")
            return True
        else:
            print(f"      {YELLOW}[!] Warning during pip install:{RESET}\n{res.stderr.strip()}")
            return True
    except Exception as e:
        print(f"      {RED}[!] Could not run pip: {e}{RESET}")
        return False

def verify_ui_bundle() -> bool:
    print(f"\n{BOLD}[3/7] Verifying Web User Interface...{RESET}")
    candidates = [
        ROOT_DIR / "dist",
        ROOT_DIR / "src" / "resolve-plugin" / "dist",
        ROOT_DIR / "apps" / "resolve-plugin" / "dist",
    ]
    for c in candidates:
        if (c / "index.html").is_file():
            print(f"      {GREEN}[+] Pre-built UI bundle detected and ready ({c.name}).{RESET}")
            return True

    print(f"      {YELLOW}[!] UI bundle not found. Attempting to build with npm...{RESET}")
    node_bin = shutil.which("node")
    npm_bin = shutil.which("npm") or shutil.which("npm.cmd")

    if not node_bin or not npm_bin:
        print(f"      {YELLOW}[!] Node.js not detected on system.{RESET}")
        print(f"      {YELLOW}    If downloading from GitHub, pre-built dist should be present.{RESET}")
        return False

    try:
        ui_src = ROOT_DIR / "src" / "resolve-plugin"
        if ui_src.is_dir():
            print(f"      Running: cd {ui_src.name} && npm install && npm run build")
            subprocess.run([npm_bin, "install"], cwd=str(ui_src), check=True)
            subprocess.run([npm_bin, "run", "build"], cwd=str(ui_src), check=True)
        else:
            print("      Running: npm install && npm run build:ui")
            subprocess.run([npm_bin, "install"], cwd=str(ROOT_DIR), check=True)
            subprocess.run([npm_bin, "run", "build:ui"], cwd=str(ROOT_DIR), check=True)

        for c in candidates:
            if (c / "index.html").is_file():
                print(f"      {GREEN}[+] UI bundle compiled successfully!{RESET}")
                return True
    except Exception as e:
        print(f"      {RED}[!] UI build failed: {e}{RESET}")

    return False

def check_and_setup_ffmpeg() -> str:
    print(f"\n{BOLD}[4/7] Detecting FFmpeg & Acceleration Engines...{RESET}")
    from xdrop.config import discover_ffmpeg
    ffmpeg_path = discover_ffmpeg()

    def test_ffmpeg(path: str) -> bool:
        try:
            r = subprocess.run([path, "-version"], capture_output=True, text=True, timeout=3.0)
            return r.returncode == 0
        except Exception:
            return False

    if test_ffmpeg(ffmpeg_path):
        try:
            r = subprocess.run([ffmpeg_path, "-version"], capture_output=True, text=True)
            first_line = r.stdout.splitlines()[0] if r.stdout else "FFmpeg active"
            print(f"      {GREEN}[+] Found FFmpeg: {ffmpeg_path}{RESET}")
            print(f"          {first_line}")
            return ffmpeg_path
        except Exception:
            pass

    # If not found, attempt auto-download of portable standalone FFmpeg
    print(f"      {YELLOW}[!] FFmpeg not found on system PATH.{RESET}")
    if platform.system() == "Windows":
        # Check if winget is available
        winget_bin = shutil.which("winget")
        if winget_bin:
            print(f"      Attempting automatic install via Windows Package Manager (winget)...")
            try:
                w_res = subprocess.run(
                    ["winget", "install", "Gyan.FFmpeg", "--accept-source-agreements", "--accept-package-agreements", "--silent"],
                    capture_output=True,
                    text=True,
                    timeout=180.0
                )
                new_ffmpeg = discover_ffmpeg()
                if test_ffmpeg(new_ffmpeg):
                    print(f"      {GREEN}[+] Successfully installed FFmpeg via winget: {new_ffmpeg}{RESET}")
                    return new_ffmpeg
            except Exception:
                pass

        # Portable binary download fallback
        bin_dir = DESKTOP_SERVICE_DIR / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        target_ffmpeg = bin_dir / "ffmpeg.exe"
        if not target_ffmpeg.exists():
            print(f"      {CYAN}Downloading official portable FFmpeg binary...{RESET}")
            # Official Gyan.dev essentials build URL
            dl_url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
            zip_dest = bin_dir / "ffmpeg-temp.zip"
            try:
                urllib.request.urlretrieve(dl_url, zip_dest)
                import zipfile
                with zipfile.ZipFile(zip_dest, "r") as zf:
                    for member in zf.namelist():
                        if member.endswith("ffmpeg.exe"):
                            with zf.open(member) as src, open(target_ffmpeg, "wb") as dst:
                                shutil.copyfileobj(src, dst)
                                break
                if zip_dest.exists():
                    zip_dest.unlink()
                if target_ffmpeg.exists():
                    print(f"      {GREEN}[+] Portable FFmpeg extracted to: {target_ffmpeg}{RESET}")
                    return str(target_ffmpeg)
            except Exception as e:
                print(f"      {YELLOW}[!] Portable download skipped: {e}{RESET}")

    print(f"      {YELLOW}[!] Please ensure FFmpeg is installed or add it to PATH.{RESET}")
    return "ffmpeg"

def detect_hardware_acceleration(ffmpeg_path: str):
    print(f"\n{BOLD}[5/7] Probing GPU Hardware Video Encoders...{RESET}")
    try:
        res = subprocess.run([ffmpeg_path, "-encoders"], capture_output=True, text=True, timeout=5.0)
        out = res.stdout or ""
        has_nvenc = "h264_nvenc" in out
        has_qsv = "h264_qsv" in out
        has_amf = "h264_amf" in out
        has_prores = "prores_ks" in out

        if has_nvenc:
            print(f"      {GREEN}[+] NVIDIA NVENC Hardware Acceleration: Available (Fastest){RESET}")
        elif has_qsv:
            print(f"      {GREEN}[+] Intel QuickSync Hardware Acceleration: Available{RESET}")
        elif has_amf:
            print(f"      {GREEN}[+] AMD AMF Hardware Acceleration: Available{RESET}")
        else:
            print(f"      {CYAN}[i] Software H.264 Encoder (libx264 multi-threaded): Active{RESET}")

        if has_prores:
            print(f"      {GREEN}[+] Apple ProRes 422 High-Precision Encoder: Available{RESET}")
    except Exception as e:
        print(f"      {YELLOW}[!] Could not probe encoders: {e}{RESET}")

def detect_and_configure_editors() -> dict:
    print(f"\n{BOLD}[6/7] Detecting Installed Video Editors...{RESET}")
    detected = {
        "resolve": False,
        "premiere": False,
        "aftereffects": False,
    }

    # 1. DaVinci Resolve Detection & Script Installation
    resolve_paths = [
        Path("C:/Program Files/Blackmagic Design/DaVinci Resolve/Resolve.exe"),
        Path("/Applications/DaVinci Resolve/DaVinci Resolve.app"),
        Path("/opt/resolve/bin/resolve"),
    ]
    resolve_installed = any(p.exists() for p in resolve_paths)
    if resolve_installed or platform.system() == "Windows":
        try:
            # Installs into Resolve's per-user Scripts folder, so no administrator
            # rights are needed. `xdrop.resolve.installer` is a shim over
            # `xdrop.integrations.resolve`.
            from xdrop.resolve.installer import install_resolve_script
            success, msg = install_resolve_script()
            if success:
                detected["resolve"] = True
                print(f"      {GREEN}[+] DaVinci Resolve: Integration script installed (App Window mode)!{RESET}")
                print(f"          Appears inside Resolve: Workspace -> Scripts -> Utility -> Xdrop")
            else:
                print(f"      {YELLOW}[i] DaVinci Resolve: {msg}{RESET}")

            # Also install DaVinci Resolve Studio Workflow Integration plugin
            try:
                from xdrop.integrations.resolve_studio import install_resolve_studio_plugin
                studio_res = install_resolve_studio_plugin()
                if studio_res.ok:
                    print(f"      {GREEN}[+] DaVinci Resolve Studio: Workflow Integration docked panel installed!{RESET}")
                    print(f"          Appears inside Studio: Workspace -> Workflow Integrations -> Xdrop")
            except Exception as e:
                pass
        except Exception as e:
            print(f"      {YELLOW}[!] DaVinci Resolve integration check: {e}{RESET}")
    else:
        print(f"      {CYAN}[i] DaVinci Resolve: Not installed on this system.{RESET}")

    # 2. Adobe Premiere Pro, After Effects & Audition Detection & CEP Extension Installation
    if platform.system() == "Windows":
        prem_paths = list(Path("C:/Program Files/Adobe").glob("Adobe Premiere Pro*")) if Path("C:/Program Files/Adobe").exists() else []
        ae_paths = list(Path("C:/Program Files/Adobe").glob("Adobe After Effects*")) if Path("C:/Program Files/Adobe").exists() else []
        aud_paths = list(Path("C:/Program Files/Adobe").glob("Adobe Audition*")) if Path("C:/Program Files/Adobe").exists() else []
        prem_found = len(prem_paths) > 0
        ae_found = len(ae_paths) > 0
        aud_found = len(aud_paths) > 0
    elif platform.system() == "Darwin":
        prem_found = Path("/Applications/Adobe Premiere Pro").exists() or len(list(Path("/Applications").glob("Adobe Premiere Pro*"))) > 0
        ae_found = Path("/Applications/Adobe After Effects").exists() or len(list(Path("/Applications").glob("Adobe After Effects*"))) > 0
        aud_found = Path("/Applications/Adobe Audition").exists() or len(list(Path("/Applications").glob("Adobe Audition*"))) > 0
    else:
        prem_found = False
        ae_found = False
        aud_found = False

    # Always install CEP panel if Adobe folder exists or on Windows/Mac
    try:
        source_dir = (
            ROOT_DIR / "src" / "premiere-plugin"
            if (ROOT_DIR / "src" / "premiere-plugin").exists()
            else ROOT_DIR / "apps" / "premiere-plugin"
        )
        if platform.system() == "Windows":
            cep_dir = Path(os.environ.get("APPDATA", "")) / "Adobe" / "CEP" / "extensions"
        else:
            cep_dir = Path.home() / "Library" / "Application Support" / "Adobe" / "CEP" / "extensions"

        target_dir = cep_dir / "com.xdrop.panel"
        legacy_dir = cep_dir / "com.resolvefetch.premiere"

        if source_dir.exists():
            cep_dir.mkdir(parents=True, exist_ok=True)
            if target_dir.exists():
                try:
                    if target_dir.is_symlink() or os.path.islink(target_dir):
                        target_dir.unlink()
                    else:
                        shutil.rmtree(target_dir, ignore_errors=True)
                except Exception:
                    pass
            shutil.copytree(source_dir, target_dir, dirs_exist_ok=True)

            if legacy_dir.exists():
                try:
                    if legacy_dir.is_symlink() or os.path.islink(legacy_dir):
                        legacy_dir.unlink()
                    else:
                        shutil.rmtree(legacy_dir, ignore_errors=True)
                except Exception:
                    pass
            shutil.copytree(source_dir, legacy_dir, dirs_exist_ok=True)

            # Write dynamic config.json for CEP panel auto-starting
            engine_vbs = (
                Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "Xdrop" / "start_engine.vbs"
                if platform.system() == "Windows"
                else Path.home() / ".xdrop" / "run.sh"
            )
            pythonw_candidate = Path(sys.executable).parent / ("pythonw.exe" if platform.system() == "Windows" else "python3")
            config_payload = {
                "runBat": str(ROOT_DIR / "run.bat"),
                "runSh": str(ROOT_DIR / "run.sh"),
                "pythonExe": sys.executable,
                "pythonwExe": str(pythonw_candidate if pythonw_candidate.exists() else ""),
                "startEngineVbs": str(engine_vbs),
                "mainPy": str(DESKTOP_SERVICE_DIR / "xdrop" / "main.py"),
                "serviceUrl": "http://127.0.0.1:8484"
            }
            try:
                with open(target_dir / "config.json", "w", encoding="utf-8") as f:
                    json.dump(config_payload, f, indent=2)
                with open(legacy_dir / "config.json", "w", encoding="utf-8") as f:
                    json.dump(config_payload, f, indent=2)
            except Exception:
                pass

            # Enable CEP developer mode for this user, on every CSXS version. Windows uses
            # HKCU and macOS uses `defaults write`; both paths live in one shared
            # implementation so this script cannot drift from the in-app installer. Every
            # child process is started headlessly, so nothing flashes on screen.
            from xdrop.integrations import apply_player_debug_mode
            from xdrop.integrations.paths import current_system

            debug_state = apply_player_debug_mode(current_system())
            if debug_state["failed"]:
                versions_failed = ", ".join(str(f["version"]) for f in debug_state["failed"])
                print(f"      {YELLOW}[i] CEP developer mode could not be enabled for CSXS {versions_failed}{RESET}")
            elif debug_state["enabled"]:
                print(f"      {GREEN}[+] CEP developer mode enabled for this user (no admin needed){RESET}")
            else:
                print(f"      {CYAN}[i] CEP developer mode is not applicable on this platform.{RESET}")

            if prem_found:
                detected["premiere"] = True
                print(f"      {GREEN}[+] Adobe Premiere Pro: Extension installed!{RESET}")
                print(f"          Appears inside Premiere: Window -> Extensions -> Xdrop")
            else:
                print(f"      {CYAN}[i] Adobe Premiere Pro: Extension ready at {target_dir.name}{RESET}")

            if ae_found:
                detected["aftereffects"] = True
                print(f"      {GREEN}[+] Adobe After Effects: Extension installed!{RESET}")
                print(f"          Appears inside After Effects: Window -> Extensions -> Xdrop")
            else:
                print(f"      {CYAN}[i] Adobe After Effects: Extension ready{RESET}")

            if aud_found:
                detected["audition"] = True
                print(f"      {GREEN}[+] Adobe Audition: Extension installed!{RESET}")
                print(f"          Appears inside Audition: Window -> Extensions -> Xdrop")
            else:
                print(f"      {CYAN}[i] Adobe Audition: Extension ready{RESET}")

    except Exception as e:
        print(f"      {YELLOW}[!] Adobe CEP installation check: {e}{RESET}")

    # 3. Blender Addon Packaging & Installation
    try:
        from tools.package_blender import build_blender_addon_zip, install_blender_addon
        zip_path = build_blender_addon_zip()
        installed_addons = install_blender_addon()
        if installed_addons:
            detected["blender"] = True
            print(f"      {GREEN}[+] Blender: VSE Addon installed into {len(installed_addons)} version(s)!{RESET}")
            print(f"          Appears inside Blender: Sequencer -> Sidebar (N-Panel) -> Xdrop")
        else:
            print(f"      {CYAN}[i] Blender: Addon package ready in {zip_path.name}{RESET}")
    except Exception as e:
        pass

    return detected

def configure_user_settings(detected_editors: dict):
    print(f"\n{BOLD}[7/7] Tailoring Default Settings for This Machine...{RESET}")
    from xdrop.database import init_db, get_settings_from_db, save_settings_to_db
    from xdrop.config import get_default_downloads_dir

    init_db()
    current_settings = get_settings_from_db()

    # Determine optimal default editor based on what's installed
    active_count = sum(1 for v in detected_editors.values() if v)
    if active_count > 1:
        recommended_editor = "auto"
    elif detected_editors.get("resolve"):
        recommended_editor = "resolve"
    elif detected_editors.get("premiere"):
        recommended_editor = "premiere"
    elif detected_editors.get("aftereffects"):
        recommended_editor = "aftereffects"
    else:
        recommended_editor = "auto"

    default_download_dir = str(get_default_downloads_dir())

    update_payload = {
        "default_editor": recommended_editor,
        "download_dir": current_settings.get("download_dir") or default_download_dir,
        "concurrent_downloads": current_settings.get("concurrent_downloads", 3),
        "naming_pattern": current_settings.get("naming_pattern", "{project}/{platform}/{mediaType}/{title}_{quality}"),
        "auto_import_to_resolve": True,
        "auto_import_to_premiere": True,
        "auto_import_to_aftereffects": True,
        "preferred_video_format": "original",
        "preferred_audio_format": "wav",
    }

    save_settings_to_db(update_payload)
    print(f"      {GREEN}[+] Tailored Default Editor: {recommended_editor.upper()}{RESET}")
    print(f"      {GREEN}[+] Media Storage Location:  {default_download_dir}{RESET}")

    # Generate 1-click launchers run.bat & run.sh
    run_bat = ROOT_DIR / "run.bat"
    run_bat_content = f"""@echo off
setlocal enabledelayedexpansion
title Xdrop Desktop Service
cd /d "%~dp0"
echo Starting Xdrop Engine...

set "PYTHON_EXE="

if exist "%~dp0.venv\\Scripts\\python.exe" (
    set "PYTHON_EXE=%~dp0.venv\\Scripts\\python.exe"
    goto :RunService
)

if exist "{sys.executable}" (
    set "PYTHON_EXE={sys.executable}"
    goto :RunService
)

python -c "import sys" >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    set "PYTHON_EXE=python"
    goto :RunService
)

py -c "import sys" >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    set "PYTHON_EXE=py"
    goto :RunService
)

for %%P in (
    "%LOCALAPPDATA%\\Programs\\Python\\Python314\\python.exe"
    "%LOCALAPPDATA%\\Programs\\Python\\Python313\\python.exe"
    "%LOCALAPPDATA%\\Programs\\Python\\Python312\\python.exe"
    "%LOCALAPPDATA%\\Programs\\Python\\Python311\\python.exe"
    "%LOCALAPPDATA%\\Programs\\Python\\Python310\\python.exe"
    "%LOCALAPPDATA%\\Programs\\Python\\Python39\\python.exe"
    "C:\\Program Files\\Python314\\python.exe"
    "C:\\Program Files\\Python313\\python.exe"
    "C:\\Program Files\\Python312\\python.exe"
    "C:\\Program Files\\Python311\\python.exe"
    "C:\\Program Files\\Python310\\python.exe"
    "C:\\Program Files\\Python39\\python.exe"
) do (
    if exist %%P (
        set "PYTHON_EXE=%%~P"
        goto :RunService
    )
)

echo.
echo [!] Python not found on this computer.
echo [*] Please run setup.bat first to configure Python.
pause
exit /b 1

:RunService
set "PYTHONPATH=%~dp0src\\desktop-service;%PYTHONPATH%"
"%PYTHON_EXE%" -m xdrop.main %*
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Service stopped or encountered an error.
    pause
)
"""
    try:
        run_bat.write_text(run_bat_content, encoding="utf-8")
        if platform.system() == "Windows":
            print(f"      {GREEN}[+] Created 1-Click Windows Launcher: run.bat{RESET}")
    except Exception:
        pass

    run_sh = ROOT_DIR / "run.sh"
    run_sh_content = f"""#!/usr/bin/env bash
# Xdrop — macOS / Linux Desktop Service Launcher
set -e

DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" >/dev/null 2>&1 && pwd)"
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
"""
    try:
        run_sh.write_text(run_sh_content, encoding="utf-8")
        if platform.system() != "Windows":
            os.chmod(run_sh, 0o755)
            print(f"      {GREEN}[+] Created 1-Click Launcher: run.sh{RESET}")
    except Exception:
        pass

def print_completion_summary(detected_editors: dict):
    print("\n" + "=" * 72)
    print(f"{GREEN}{BOLD}  🎉 XDROP AUTOMATED SETUP COMPLETED SUCCESSFULLY! 🎉{RESET}")
    print("=" * 72)
    print(f"\n{BOLD}Installed & Configured Features:{RESET}")
    print(f"  • Cross-NLE Engine:        {GREEN}Active (Port 8484){RESET}")
    print(f"  • DaVinci Resolve Script:  {GREEN + 'Installed' if detected_editors.get('resolve') else CYAN + 'Configured'}{RESET}")
    print(f"  • Premiere Pro Plugin:     {GREEN + 'Installed' if detected_editors.get('premiere') else CYAN + 'Configured'}{RESET}")
    print(f"  • After Effects Plugin:    {GREEN + 'Installed' if detected_editors.get('aftereffects') else CYAN + 'Configured'}{RESET}")
    print(f"  • Multi-Threaded FFmpeg:   {GREEN}Verified & Ready{RESET}")

    print(f"\n{BOLD}How to Launch Xdrop:{RESET}")
    if platform.system() == "Windows":
        print(f"  {CYAN}👉 Double-click 'run.bat' in the project folder{RESET}")
        print(f"  {CYAN}   or run: python -m xdrop.main --gui{RESET}")
    else:
        print(f"  {CYAN}👉 Run: ./run.sh or python3 -m xdrop.main --gui{RESET}")

    print(f"\n{BOLD}Using in Your Video Editors:{RESET}")
    print("  • DaVinci Resolve:   Workspace -> Scripts -> Utility -> Xdrop")
    print("  • Premiere Pro:      Window -> Extensions -> Xdrop")
    print("  • After Effects:     Window -> Extensions -> Xdrop")
    print("  • Web Browser:       http://localhost:8484")
    print("=" * 72 + "\n")

def main():
    print_banner()
    if not check_python_version():
        sys.exit(1)

    install_python_dependencies()
    verify_ui_bundle()
    ffmpeg_path = check_and_setup_ffmpeg()
    detect_hardware_acceleration(ffmpeg_path)
    detected_editors = detect_and_configure_editors()
    configure_user_settings(detected_editors)
    print_completion_summary(detected_editors)

if __name__ == "__main__":
    main()
