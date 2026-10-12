#!/usr/bin/env python3
"""
Xdrop Adobe Premiere Pro & Creative Cloud Native Extension Installer.

Dedicated standalone installer specifically tailored for Adobe Premiere Pro,
After Effects, and Audition:
1. Deep-scans the system to detect installed Adobe host applications.
2. Installs the high-performance native CEP panel into Adobe extensions directory.
3. Configures CSXS PlayerDebugMode across versions 9..16 in Windows Registry (no admin required).
4. Packages and provisions modern UXP .ccx bundles (Premiere Pro and After Effects).
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


class PremiereExtensionInstaller(ExtensionInstaller):
    """Specialized installer that provisions Adobe Creative Cloud extensions only."""

    def run_premiere_only(self):
        log_header("Configuring Adobe Creative Cloud Native Extensions")

        # 1. Background Engine (Headless, 0 CMD windows)
        self.install_desktop_service()

        # 2. Install Adobe CEP & UXP Panels + CSXS Registry
        self.install_adobe_creative_cloud()

        # 3. Configure Universal Timeline Sidecars
        self.configure_fcpxml_drag_and_drop()


def print_premiere_banner():
    print(f"""{CYAN}{BOLD}
========================================================================
   __   __      _                 
   \\ \\ / /     | |                
    \\ V /  ____| | _ __  ___  _ __  
    /   \\ / _  | |/ / _ \\/ _ \\| '_ \\ 
   / /^\\ \\ (_| | | < (_) | (_) | |_) |
  /_/   \\_\\__,_|_|\\_\\___/ \\___/| .__/ 
                               | |    
  Adobe Premiere Pro Edition   |_|    
========================================================================{RESET}
{BOLD}        ADOBE PREMIERE PRO & CREATIVE CLOUD INSTALLER{RESET}
  Supports: Adobe Premiere Pro (2020-2026+), After Effects, Audition
  Architecture: Native CEP Panel + Modern UXP (.ccx) Package
""")


def print_premiere_guide(discovered: List[DiscoveredApp]):
    print(f"\n{BOLD}{GREEN}========================================================================{RESET}")
    print(f"{BOLD}{GREEN}          ADOBE EXTENSIONS SUCCESSFULLY CONFIGURED                      {RESET}")
    print(f"{BOLD}{GREEN}========================================================================{RESET}")

    print(f"\n{BOLD}How to Launch Xdrop inside Adobe Premiere Pro:{RESET}\n")

    print(f"1. {BOLD}Open Extension Panel in Premiere Pro:{RESET}")
    print(f"   {CYAN}Top Menu -> Window -> Extensions -> Xdrop{RESET}")
    print(f"   * Dock the panel anywhere in your editing workspace (e.g. next to Project or Effect Controls).")
    print(f"   * Automatically detects your active project and sequence.")

    print(f"\n2. {BOLD}Automatic Bin & Timeline Insertion:{RESET}")
    print(f"   * Downloads are organized into the canonical {CYAN}000_Xdrop Assets{RESET} bin.")
    print(f"   * Enabling 'Auto-import' drops the media directly at your playhead on Track 1.")

    print(f"\n3. {BOLD}Also Available in After Effects & Audition:{RESET}")
    print(f"   * After Effects: {CYAN}Window -> Extensions -> Xdrop{RESET} (inserts directly into active composition).")
    print(f"   * Audition:      {CYAN}Window -> Extensions -> Xdrop{RESET} (imports audio clips into active session).")

    print(f"\n4. {BOLD}Modern UXP Package (.ccx):{RESET}")
    print(f"   * Available in your Xdrop dist folder: {DIM}dist/xdrop-uxp-premiere-1.0.0.ccx{RESET}")
    print(f"   * Can be installed directly via Adobe Creative Cloud Desktop if preferred.")

    print(f"\n5. {BOLD}Background Service Status:{RESET}")
    print(f"   Listening on {CYAN}http://127.0.0.1:8484{RESET} (auto-starts silently with Windows/system startup).")
    print(f"   100% Zero-Flicker: runs via pythonw / start_engine.vbs with zero console popups.\n")


def main():
    print_premiere_banner()

    print(f"System: {platform.system()} {platform.release()} ({platform.architecture()[0]})")
    print(f"Python: {sys.version.split()[0]}")
    print(f"Location: {BASE_DIR}")

    # Phase 1: Deep Scanning for Adobe Apps
    log_header("Phase 1: Scanning for Adobe Creative Cloud Applications")
    scanner = DeepAppScanner()
    all_apps = scanner.scan()

    adobe_apps = [a for a in all_apps if a.vendor.lower() == "adobe" or a.app_id in ("premiere", "aftereffects", "audition")]
    if adobe_apps:
        for app in adobe_apps:
            running_tag = f" {GREEN}(Currently Running){RESET}" if app.is_running else ""
            log_success(f"Found: {BOLD}{app.name}{RESET} - v{app.version}{running_tag}")
            if app.executable:
                log_info(f"Executable: {DIM}{app.executable}{RESET}")
    else:
        log_info("Adobe applications not detected in standard locations (installing CEP extension anyway).")

    # Phase 2: Provision Extensions
    log_header("Phase 2: Installing Adobe CEP & UXP Native Extensions")
    installer = PremiereExtensionInstaller(all_apps)
    installer.run_premiere_only()

    # Phase 3: Guide
    print_premiere_guide(adobe_apps)

    # Hold open if double-clicked
    if getattr(sys, "frozen", False) and not any(arg in sys.argv for arg in ["--silent", "-y", "--non-interactive"]):
        try:
            input(f"\n{BOLD}Press Enter to exit...{RESET}")
        except Exception:
            pass


if __name__ == "__main__":
    main()
