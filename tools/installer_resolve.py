#!/usr/bin/env python3
"""
Xdrop DaVinci Resolve Native Extension Installer.

Dedicated standalone installer specifically tailored for DaVinci Resolve (Free & Studio):
1. Deep-scans the system to detect DaVinci Resolve installations and running processes.
2. Purges legacy/duplicate ResolveFetch scripts while preserving third-party plugins (Snap Captions).
3. Deploys the DaVinci Resolve Native Lua Extension (Xdrop.lua + Xdrop - Starter Bin.drb) into Scripts/Comp/.
4. Deploys the DaVinci Resolve Studio Workflow Integration plugin (WorkflowIntegration.node).
5. Installs and silently starts the Xdrop headless background engine (0 CMD windows).
6. Configures FCPXML 1.11 drag-and-drop timeline generation.
"""

from __future__ import annotations

import os
import platform
import shutil
import sys
import time
from pathlib import Path
from typing import List

# Import core scanner and installer components from tools.installer
try:
    from tools.installer import (
        BASE_DIR,
        CHECK,
        CROSS,
        CYAN,
        DIM,
        GREEN,
        INFO,
        RED,
        RESET,
        WARN,
        BOLD,
        DeepAppScanner,
        DiscoveredApp,
        ExtensionInstaller,
        find_system_python,
        log_error,
        log_header,
        log_info,
        log_success,
        log_warn,
    )
except ImportError:
    # Running from tools directory directly
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from tools.installer import (
        BASE_DIR,
        CHECK,
        CROSS,
        CYAN,
        DIM,
        GREEN,
        INFO,
        RED,
        RESET,
        WARN,
        BOLD,
        DeepAppScanner,
        DiscoveredApp,
        ExtensionInstaller,
        find_system_python,
        log_error,
        log_header,
        log_info,
        log_success,
        log_warn,
    )


class ResolveExtensionInstaller(ExtensionInstaller):
    """Specialized installer that provisions DaVinci Resolve extensions only."""

    def run_resolve_only(self):
        log_header("Configuring DaVinci Resolve Native Integrations")

        # 1. Background Engine (Headless, 0 CMD windows)
        self.install_desktop_service()

        # 2. Cleanup legacy duplicates (preserving Snap Captions)
        self.clean_davinci_resolve_scripts()

        # 3. Install DaVinci Resolve Lua & Studio Workflow Integration
        self.install_davinci_resolve()

        # 4. Configure Universal Timeline Sidecars
        self.configure_fcpxml_drag_and_drop()


def print_resolve_banner():
    print(f"""{CYAN}{BOLD}
========================================================================
   __   __      _                 
   \\ \\ / /     | |                
    \\ V /  ____| | _ __  ___  _ __  
    /   \\ / _  | |/ / _ \\/ _ \\| '_ \\ 
   / /^\\ \\ (_| | | < (_) | (_) | |_) |
  /_/   \\_\\__,_|_|\\_\\___/ \\___/| .__/ 
                               | |    
  DaVinci Resolve Edition      |_|    
========================================================================{RESET}
{BOLD}        DAVINCI RESOLVE NATIVE EXTENSION INSTALLER{RESET}
  Supports: DaVinci Resolve Free & Studio (18, 19, 20+)
  Architecture: Native Lua UI Dialog + Studio Workflow Integration
""")


def print_resolve_guide(discovered: List[DiscoveredApp]):
    print(f"\n{BOLD}{GREEN}========================================================================{RESET}")
    print(f"{BOLD}{GREEN}         DAVINCI RESOLVE EXTENSIONS SUCCESSFULLY CONFIGURED             {RESET}")
    print(f"{BOLD}{GREEN}========================================================================{RESET}")

    print(f"\n{BOLD}How to Launch Xdrop inside DaVinci Resolve:{RESET}\n")

    print(f"1. {BOLD}DaVinci Resolve Free & Studio (Recommended Native UI):{RESET}")
    print(f"   {CYAN}Top Menu -> Workspace -> Scripts -> Comp -> Xdrop{RESET}")
    print(f"   * Built on the exact same native Fusion UI architecture as Snap Captions.")
    print(f"   * Zero browser tabs or popup windows.")
    print(f"   * Pre-loads the canonical '000_Xdrop Assets' bin and sub-bins automatically.")

    print(f"\n2. {BOLD}DaVinci Resolve Studio (Workflow Integrations):{RESET}")
    print(f"   {CYAN}Top Menu -> Workspace -> Workflow Integrations -> Xdrop{RESET}")
    print(f"   * Fully dockable Studio panel next to Media Pool and Timeline.")
    print(f"   * Direct real-time drag-and-drop into any bin or timeline.")

    print(f"\n3. {BOLD}Starter Bin Structure (Pre-configured in Media Pool):{RESET}")
    print(f"   {DIM}000_Xdrop Assets/{RESET}")
    print(f"   {DIM}  |-- 01_Downloads{RESET}")
    print(f"   {DIM}  |-- 02_Video Clips{RESET}")
    print(f"   {DIM}  |-- 03_Music & SFX{RESET}")
    print(f"   {DIM}  |-- 04_Dialogue & Audio{RESET}")
    print(f"   {DIM}  \\-- 05_Proxies & Renders{RESET}")

    print(f"\n4. {BOLD}Background Service Status:{RESET}")
    print(f"   Listening on {CYAN}http://127.0.0.1:8484{RESET} (auto-starts silently with Windows/system startup).")
    print(f"   100% Zero-Flicker: runs via pythonw / start_engine.vbs with no console popups.\n")


def main():
    print_resolve_banner()

    print(f"System: {platform.system()} {platform.release()} ({platform.architecture()[0]})")
    print(f"Python: {sys.version.split()[0]}")
    print(f"Location: {BASE_DIR}")

    # Phase 1: Deep Scanning for DaVinci Resolve
    log_header("Phase 1: Scanning for DaVinci Resolve Installation")
    scanner = DeepAppScanner()
    all_apps = scanner.scan()

    resolve_apps = [a for a in all_apps if a.app_id == "resolve"]
    if resolve_apps:
        for app in resolve_apps:
            running_tag = f" {GREEN}(Currently Running){RESET}" if app.is_running else ""
            log_success(f"Found: {BOLD}{app.name}{RESET} [{app.vendor}] - v{app.version}{running_tag}")
            if app.executable:
                log_info(f"Executable: {DIM}{app.executable}{RESET}")
    else:
        log_info("DaVinci Resolve not detected in standard locations (installing scripts to standard user paths anyway).")

    # Phase 2: Provision Extensions
    log_header("Phase 2: Installing Native DaVinci Resolve Extensions")
    installer = ResolveExtensionInstaller(all_apps)
    installer.run_resolve_only()

    # Phase 3: Guide
    print_resolve_guide(resolve_apps)

    # Hold open if double-clicked
    if getattr(sys, "frozen", False) and not any(arg in sys.argv for arg in ["--silent", "-y", "--non-interactive"]):
        try:
            input(f"\n{BOLD}Press Enter to exit...{RESET}")
        except Exception:
            pass


if __name__ == "__main__":
    main()
