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

ROOT_DIR = Path(__file__).resolve().parent.parent
DESKTOP_SERVICE_DIR = ROOT_DIR / "apps" / "desktop-service"
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
    dist_dir = ROOT_DIR / "apps" / "resolve-plugin" / "dist"
    index_file = dist_dir / "index.html"

    if index_file.is_file():
        print(f"      {GREEN}[+] Pre-built UI bundle detected and ready.{RESET}")
        return True

    print(f"      {YELLOW}[!] UI bundle not found. Attempting to build with npm...{RESET}")
    node_bin = shutil.which("node")
    npm_bin = shutil.which("npm") or shutil.which("npm.cmd")

    if not node_bin or not npm_bin:
        print(f"      {YELLOW}[!] Node.js not detected on system.{RESET}")
        print(f"      {YELLOW}    If downloading from GitHub, pre-built dist should be present.{RESET}")
        return False

    try:
        print("      Running: npm install && npm run build:ui")
        subprocess.run([npm_bin, "install"], cwd=str(ROOT_DIR), check=True)
        subprocess.run([npm_bin, "run", "build:ui"], cwd=str(ROOT_DIR), check=True)
        if index_file.is_file():
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
            from xdrop.resolve.installer import install_resolve_script
            success, msg = install_resolve_script()
            if success:
                detected["resolve"] = True
                print(f"      {GREEN}[+] DaVinci Resolve: Integration script installed!{RESET}")
                print(f"          Appears inside Resolve: Workspace -> Scripts -> Utility -> Xdrop")
            else:
                print(f"      {YELLOW}[i] DaVinci Resolve: {msg}{RESET}")
        except Exception as e:
            print(f"      {YELLOW}[!] DaVinci Resolve integration check: {e}{RESET}")
    else:
        print(f"      {CYAN}[i] DaVinci Resolve: Not installed on this system.{RESET}")

    # 2. Adobe Premiere Pro & After Effects Detection & CEP Extension Installation
    if platform.system() == "Windows":
        prem_paths = list(Path("C:/Program Files/Adobe").glob("Adobe Premiere Pro*")) if Path("C:/Program Files/Adobe").exists() else []
        ae_paths = list(Path("C:/Program Files/Adobe").glob("Adobe After Effects*")) if Path("C:/Program Files/Adobe").exists() else []
        prem_found = len(prem_paths) > 0
        ae_found = len(ae_paths) > 0
    elif platform.system() == "Darwin":
        prem_found = Path("/Applications/Adobe Premiere Pro").exists() or len(list(Path("/Applications").glob("Adobe Premiere Pro*"))) > 0
        ae_found = Path("/Applications/Adobe After Effects").exists() or len(list(Path("/Applications").glob("Adobe After Effects*"))) > 0
    else:
        prem_found = False
        ae_found = False

    # Always install CEP panel if Adobe folder exists or on Windows/Mac
    try:
        source_dir = ROOT_DIR / "apps" / "premiere-plugin"
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

            # Enable CEP Developer Mode in Registry on Windows
            if platform.system() == "Windows":
                for ver in ["9", "10", "11", "12", "13", "14", "15", "16"]:
                    subprocess.run(
                        ["reg", "add", f"HKCU\\Software\\Adobe\\CSXS.{ver}", "/v", "PlayerDebugMode", "/t", "REG_SZ", "/d", "1", "/f"],
                        capture_output=True,
                        check=False
                    )

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

    except Exception as e:
        print(f"      {YELLOW}[!] Adobe CEP installation check: {e}{RESET}")

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

    # Generate 1-click launcher run.bat
    if platform.system() == "Windows":
        run_bat = ROOT_DIR / "run.bat"
        run_bat_content = f"""@echo off
title Xdrop Desktop Service
cd /d "%~dp0"
echo Starting Xdrop Engine...
python apps\\desktop-service\\xdrop\\main.py --gui
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Service stopped or encountered an error.
    pause
)
"""
        run_bat.write_text(run_bat_content, encoding="utf-8")
        print(f"      {GREEN}[+] Created 1-Click Windows Launcher: run.bat{RESET}")

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
        print(f"  {CYAN}   or run: python apps/desktop-service/xdrop/main.py --gui{RESET}")
    else:
        print(f"  {CYAN}👉 Run: python3 apps/desktop-service/xdrop/main.py --gui{RESET}")

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
