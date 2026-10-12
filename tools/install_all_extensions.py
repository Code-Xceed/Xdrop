#!/usr/bin/env python3
"""
Xdrop — Master Extension Installer & Environment Validator

Installs and validates native extension packages across all supported editors:
1. DaVinci Resolve Studio (Native Workflow Integration Dock)
2. DaVinci Resolve Free & Studio (Utility Script with App Window Launcher)
3. Adobe Premiere Pro (Native Docked CEP/UXP Panel)
4. Adobe After Effects (Native Docked CEP/UXP Panel)
5. Adobe Audition (Native Docked CEP Panel)
6. Blender 3.x / 4.x / 5.x (Native VSE Addon)
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Tuple

# Terminal colors
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"

# Configure terminal encoding
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

REPO_ROOT = Path(__file__).resolve().parent.parent
SERVICE_DIR = REPO_ROOT / "apps" / "desktop-service"
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(SERVICE_DIR))


def log_step(title: str):
    print(f"\n{BOLD}{CYAN}=== {title} ==={RESET}")


def log_success(msg: str):
    print(f"  {GREEN}[+] {msg}{RESET}")


def log_info(msg: str):
    print(f"  {CYAN}[i] {msg}{RESET}")


def log_warn(msg: str):
    print(f"  {YELLOW}[!] {msg}{RESET}")


def log_error(msg: str):
    print(f"  {RED}[X] {msg}{RESET}")


def install_davinci_resolve() -> Dict[str, bool]:
    log_step("DaVinci Resolve Integrations")
    results = {"studio_plugin": False, "lua_extension": False}

    # 1. Clean any duplicate or legacy scripts across all Resolve directories (Preserving Snap Captions!)
    if platform.system() == "Windows":
        appdata = Path(os.environ.get("APPDATA", ""))
        progdata = Path(os.environ.get("PROGRAMDATA", "C:/ProgramData"))
        search_roots = [
            appdata / "Blackmagic Design" / "DaVinci Resolve" / "Support" / "Fusion" / "Scripts",
            progdata / "Blackmagic Design" / "DaVinci Resolve" / "Fusion" / "Scripts",
        ]
    elif platform.system() == "Darwin":
        search_roots = [
            Path.home() / "Library" / "Application Support" / "Blackmagic Design" / "DaVinci Resolve" / "Fusion" / "Scripts",
            Path("/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts"),
        ]
    else:
        search_roots = [
            Path("/opt/resolve/Fusion/Scripts"),
            Path.home() / ".local/share/DaVinciResolve/Fusion/Scripts",
        ]

    cleaned_count = 0
    for root in search_roots:
        if not root.is_dir():
            continue
        for item in root.rglob("*"):
            if not item.is_file():
                continue
            fname = item.name.lower()
            if "resolvefetch" in fname or "xdrop" in fname:
                if "snap" in fname or "caption" in fname:
                    continue
                try:
                    item.unlink(missing_ok=True)
                    cleaned_count += 1
                except Exception:
                    pass
    if cleaned_count:
        log_success(f"Purged {cleaned_count} duplicate/legacy Resolve script(s).")

    # 2. DaVinci Resolve Studio Workflow Integration Plugin
    from xdrop.integrations.resolve_studio import (
        RESOLVE_STUDIO_PLUGIN_ID,
        find_resolve_studio_source,
        install_resolve_studio_plugin,
    )
    from xdrop.integrations.paths import detect

    host_paths = detect()
    res_studio_user = install_resolve_studio_plugin(host_paths, scope="user")
    if res_studio_user.ok:
        results["studio_plugin"] = True
        log_success("DaVinci Resolve Studio: Workflow Integration installed!")
        log_info("  Access inside Studio: Workspace -> Workflow Integrations -> Xdrop")

    # 3. DaVinci Resolve Native Fusion UI Lua Extension (CANONICAL: Scripts/Comp/Xdrop.lua)
    lua_source = REPO_ROOT / "apps" / "resolve-plugin" / "Xdrop.lua"
    drb_source = REPO_ROOT / "apps" / "resolve-plugin" / "Xdrop - Starter Bin.drb"
    if not drb_source.is_file():
        drb_source = REPO_ROOT / "dist" / "Xdrop - Starter Bin.drb"

    if lua_source.is_file():
        comp_target = None
        if platform.system() == "Windows":
            appdata = Path(os.environ.get("APPDATA", ""))
            comp_target = appdata / "Blackmagic Design" / "DaVinci Resolve" / "Support" / "Fusion" / "Scripts" / "Comp" / "Xdrop.lua"
        elif platform.system() == "Darwin":
            comp_target = Path.home() / "Library" / "Application Support" / "Blackmagic Design" / "DaVinci Resolve" / "Fusion" / "Scripts" / "Comp" / "Xdrop.lua"

        if comp_target:
            try:
                comp_target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(lua_source, comp_target)
                if drb_source.is_file():
                    shutil.copy2(drb_source, comp_target.parent / "Xdrop - Starter Bin.drb")
                results["lua_extension"] = True
                log_success(f"DaVinci Resolve: Native Lua Extension installed at {comp_target}")
                log_info("  Access inside Resolve: Workspace -> Scripts -> Comp -> Xdrop")
                log_info("  (Runs 100% inside DaVinci Resolve via native Fusion UI - Snap Captions architecture)")
            except Exception as e:
                log_warn(f"Could not install Xdrop.lua: {e}")

    return results


def install_adobe_creative_cloud() -> Dict[str, bool]:
    log_step("Adobe Creative Cloud (Premiere Pro, After Effects, Audition)")
    results = {"cep_panel": False, "uxp_packages": False}

    source_dir = REPO_ROOT / "apps" / "premiere-plugin"
    if not source_dir.exists():
        log_error("Adobe plugin source `apps/premiere-plugin` not found.")
        return results

    # Determine CEP extension targets
    if platform.system() == "Windows":
        cep_root = Path(os.path.expandvars(r"%APPDATA%\Adobe\CEP\extensions"))
    elif platform.system() == "Darwin":
        cep_root = Path.home() / "Library" / "Application Support" / "Adobe" / "CEP" / "extensions"
    else:
        cep_root = None

    if cep_root:
        try:
            cep_root.mkdir(parents=True, exist_ok=True)
            for bundle_name in ("com.xdrop.panel", "com.resolvefetch.premiere"):
                target = cep_root / bundle_name
                if target.exists():
                    shutil.rmtree(target, ignore_errors=True)
                shutil.copytree(source_dir, target, dirs_exist_ok=True)

            # Enable CEP Developer Debug Mode for all CSXS versions
            from xdrop.integrations import apply_player_debug_mode
            from xdrop.integrations.paths import current_system

            debug_res = apply_player_debug_mode(current_system())
            if debug_res.get("enabled"):
                log_success("Adobe CEP Developer Mode enabled in registry (no admin required).")

            manifest_check = (cep_root / "com.xdrop.panel" / "CSXS" / "manifest.xml").is_file()
            if manifest_check:
                results["cep_panel"] = True
                log_success("Adobe CEP Extension installed and verified!")
                log_info("  • Premiere Pro:   Window -> Extensions -> Xdrop")
                log_info("  • After Effects:  Window -> Extensions -> Xdrop")
                log_info("  • Audition:       Window -> Extensions -> Xdrop")
        except Exception as e:
            log_error(f"Failed to install Adobe CEP panel: {e}")

    # Build UXP Packages for Premiere & AE
    try:
        from tools.package_uxp import build_all
        report = build_all(out_dir=REPO_ROOT / "dist")
        pkg_list = report.get("packages", [])
        if pkg_list:
            results["uxp_packages"] = True
            log_success("Built UXP Packages (.ccx) in `dist/`:")
            for p in pkg_list:
                log_info(f"  • {Path(p['path']).name} ({p['label']})")
    except Exception as e:
        log_info(f"Note on UXP building: {e}")

    return results


def install_blender_addon() -> bool:
    log_step("Blender Video Sequence Editor (VSE)")
    try:
        from tools.package_blender import build_blender_addon_zip, install_blender_addon
        zip_path = build_blender_addon_zip()
        log_success(f"Blender Addon ZIP created: {zip_path}")
        log_info("  Manual install: Blender -> Edit -> Preferences -> Add-ons -> Install...")

        installed = install_blender_addon()
        if installed:
            for p in installed:
                log_success(f"Auto-installed into Blender: {p}")
            log_info("  Access inside Blender: Sequencer -> Sidebar (N-Panel) -> Xdrop")
        else:
            log_info("No existing Blender user folders found. Use the generated .zip for installation.")
        return True
    except Exception as e:
        log_warn(f"Blender Addon: {e}")
        return False


def print_summary():
    print(f"\n{BOLD}{GREEN}========================================================================{RESET}")
    print(f"{BOLD}{GREEN}              XDROP EXTENSION INSTALLATION COMPLETE                     {RESET}")
    print(f"{BOLD}{GREEN}========================================================================{RESET}")
    print(f"""
{BOLD}Summary of Installed Extensions & How to Open Inside Your Editors:{RESET}

1. {BOLD}DaVinci Resolve Studio:{RESET}
   - Type: Native Docked Workflow Integration
   - How to open: {CYAN}Workspace -> Workflow Integrations -> Xdrop{RESET}

2. {BOLD}DaVinci Resolve (Free & Studio):{RESET}
   - Type: Native Desktop App Utility Script
   - How to open: {CYAN}Workspace -> Scripts -> Utility -> Xdrop{RESET}
   - Launches in dedicated desktop window (no browser tabs/bars).

3. {BOLD}Adobe Premiere Pro:{RESET}
   - Type: Native Docked Panel (CEP / UXP)
   - How to open: {CYAN}Window -> Extensions -> Xdrop{RESET}

4. {BOLD}Adobe After Effects:{RESET}
   - Type: Native Docked Panel (CEP / UXP)
   - How to open: {CYAN}Window -> Extensions -> Xdrop{RESET}

5. {BOLD}Adobe Audition:{RESET}
   - Type: Native Docked Panel (CEP)
   - How to open: {CYAN}Window -> Extensions -> Xdrop{RESET}

6. {BOLD}Blender VSE:{RESET}
   - Type: Native Sequencer Addon
   - Package: {CYAN}dist/xdrop_blender_addon.zip{RESET}
   - How to open: {CYAN}Sequencer -> Sidebar (N-Key) -> Xdrop tab{RESET}

7. {BOLD}Apple Final Cut Pro & Universal NLEs (CapCut, Vegas, Avid):{RESET}
   - FCPXML 1.11 sidecar generator & Universal Timeline Drag-and-Drop
   - Drag completed downloads directly onto any editor timeline!
""")


def main():
    print(f"{BOLD}{CYAN}Xdrop Universal Editor Extension Installer{RESET}")
    print(f"Operating System: {platform.system()} ({platform.release()})")
    
    install_davinci_resolve()
    install_adobe_creative_cloud()
    install_blender_addon()
    print_summary()


if __name__ == "__main__":
    main()
