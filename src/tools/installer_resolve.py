#!/usr/bin/env python3
"""
Xdrop DaVinci Resolve Native Extension Installer.

Dedicated standalone installer specifically tailored for DaVinci Resolve (Free & Studio):
1. Deep-scans workstation drives, registry, and running processes to detect all DaVinci Resolve installations.
2. Supports standard per-user (%APPDATA%), system-wide (%PROGRAMDATA%), and custom folder installations.
3. Purges legacy/duplicate ResolveFetch scripts while strictly preserving third-party plugins (e.g. Snap Captions).
4. Deploys the DaVinci Resolve Native Lua Extension (Xdrop.lua + Xdrop - Starter Bin.drb + XdropLogo.png) into Scripts/Comp/.
5. Deploys the DaVinci Resolve Desktop Utility script (Xdrop.py) into Scripts/Utility/.
6. Deploys the DaVinci Resolve Studio Workflow Integration docked panel (WorkflowIntegration.node + web bundle).
7. Installs and silently starts the Xdrop zero-flicker headless background engine (0 CMD windows).
8. Configures FCPXML 1.11 drag-and-drop timeline generation.
9. Provides a polished DaVinci Resolve Studio dark GUI with automatic headless CLI fallback.
"""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Tuple

if sys.platform == "win32":
    import winreg
else:
    winreg = None

# Ensure tools and repository directories are on sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent if SCRIPT_DIR.name == "tools" and SCRIPT_DIR.parent.name != "src" else SCRIPT_DIR.parent.parent
for p in [str(SCRIPT_DIR), str(REPO_ROOT), str(REPO_ROOT / "src"), str(REPO_ROOT / "src" / "desktop-service")]:
    if p not in sys.path:
        sys.path.insert(0, p)

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
        find_source_dir,
        find_system_python,
        log_error,
        log_header,
        log_info,
        log_success,
        log_warn,
    )
except ImportError:
    from installer import (
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
        find_source_dir,
        find_system_python,
        log_error,
        log_header,
        log_info,
        log_success,
        log_warn,
    )

# --- GUI Design Tokens (DaVinci Resolve Studio Dark / Obsidian) -----------------
COLOR_RESOLVE_BG = "#0c0d12"             # Deep Obsidian Black
COLOR_RESOLVE_CARD = "#141722"           # Inset panel charcoal
COLOR_RESOLVE_CARD_BORDER = "#252a3b"    # Subtle structural border
COLOR_RESOLVE_ACCENT = "#f59e0b"         # Resolve Signature Amber / Gold
COLOR_RESOLVE_CYAN = "#00e5ff"           # Xdrop Electric Cyan
COLOR_RESOLVE_HOVER = "#fbbf24"          # Amber highlight hover
COLOR_RESOLVE_TEXT = "#fafafa"           # Crisp white
COLOR_RESOLVE_TEXT_MUTED = "#94a3b8"     # Secondary body text
COLOR_RESOLVE_TEXT_DIM = "#64748b"       # Footnote / path labels
COLOR_RESOLVE_SUCCESS = "#22c55e"        # Green verification accent
COLOR_RESOLVE_SUCCESS_BG = "#0f2318"     # Soft green container


class ResolveExtensionInstaller(ExtensionInstaller):
    """Specialized installer that provisions DaVinci Resolve extensions only."""

    def __init__(
        self,
        discovered: Optional[List[DiscoveredApp]] = None,
        custom_scripts_dir: Optional[Path] = None,
        custom_workflow_dir: Optional[Path] = None,
        log_callback=None,
    ):
        super().__init__(discovered or [])
        self.custom_scripts_dir = Path(custom_scripts_dir).resolve() if custom_scripts_dir else None
        self.custom_workflow_dir = Path(custom_workflow_dir).resolve() if custom_workflow_dir else None
        self.log_callback = log_callback
        self.installed_files: List[Path] = []

    def _log(self, msg: str, level: str = "info"):
        if self.log_callback:
            try:
                self.log_callback(msg, level)
            except Exception:
                pass
        if level == "success":
            log_success(msg)
        elif level == "warn":
            log_warn(msg)
        elif level == "error":
            log_error(msg)
        else:
            log_info(msg)

    def run_resolve_only(self, install_engine: bool = True, clean_legacy: bool = True):
        log_header("Configuring DaVinci Resolve Native Integrations")
        self._log("Starting DaVinci Resolve integration deployment...")

        # 1. Background Engine (Headless, 0 CMD windows)
        if install_engine:
            self._log("Configuring zero-trace background engine service...")
            self.install_desktop_service()

        # 2. Cleanup legacy duplicates (preserving Snap Captions and third-party tools)
        if clean_legacy:
            self._log("Scanning for legacy/duplicate script files...")
            self.clean_davinci_resolve_scripts()

        # 3. Install DaVinci Resolve Lua & Studio Workflow Integration
        self._log("Deploying native Fusion UI script, Starter Bin, and Workflow Integration...")
        self.install_davinci_resolve()

        # 4. If custom scripts directory was specified, deploy directly there as well
        if self.custom_scripts_dir:
            self.deploy_to_custom_scripts_dir(self.custom_scripts_dir)

        # 5. Configure Universal Timeline Sidecars
        self.configure_fcpxml_drag_and_drop()
        self._log("DaVinci Resolve deployment completed successfully!", "success")

    def deploy_to_custom_scripts_dir(self, target_dir: Path):
        """Deploys Fusion Lua script, Utility script, and Starter Bin to a user-specified custom folder."""
        self._log(f"Deploying extensions to custom folder: {target_dir}")
        try:
            target_dir.mkdir(parents=True, exist_ok=True)

            # Determine Comp and Utility directories
            if target_dir.name.lower() == "comp":
                comp_dir = target_dir
                utility_dir = target_dir.parent / "Utility"
            elif target_dir.name.lower() == "scripts":
                comp_dir = target_dir / "Comp"
                utility_dir = target_dir / "Utility"
            elif (target_dir / "Support" / "Fusion" / "Scripts").is_dir() or (target_dir / "Resolve.exe").is_file():
                comp_dir = target_dir / "Support" / "Fusion" / "Scripts" / "Comp"
                utility_dir = target_dir / "Support" / "Fusion" / "Scripts" / "Utility"
            else:
                comp_dir = target_dir / "Comp"
                utility_dir = target_dir / "Utility"

            comp_dir.mkdir(parents=True, exist_ok=True)
            utility_dir.mkdir(parents=True, exist_ok=True)

            # 1. Copy Lua script
            lua_src = find_source_dir("resolve-plugin") / "Xdrop.lua"
            if lua_src.is_file():
                tgt = comp_dir / "Xdrop.lua"
                shutil.copy2(lua_src, tgt)
                self.installed_files.append(tgt)
                self._log(f"Custom deploy: {tgt}", "success")

            # 2. Copy Starter Bin
            drb_src = find_source_dir("resolve-plugin") / "Xdrop - Starter Bin.drb"
            if not drb_src.is_file():
                drb_src = BASE_DIR / "dist" / "Xdrop - Starter Bin.drb"
            if drb_src.is_file():
                tgt_drb = comp_dir / "Xdrop - Starter Bin.drb"
                shutil.copy2(drb_src, tgt_drb)
                self.installed_files.append(tgt_drb)
                self._log(f"Custom deploy: {tgt_drb}", "success")

            # 3. Copy Logo
            logo_src = find_source_dir("resolve-plugin") / "XdropLogo.png"
            if not logo_src.is_file():
                logo_src = BASE_DIR / "src" / "assets" / "logo.png"
            if logo_src.is_file():
                tgt_logo = comp_dir / "XdropLogo.png"
                shutil.copy2(logo_src, tgt_logo)
                self.installed_files.append(tgt_logo)

            # 4. Generate Utility Script
            try:
                from xdrop.integrations.resolve import build_resolve_script_content
                script_code = build_resolve_script_content()
                tgt_py = utility_dir / "Xdrop.py"
                tgt_py.write_text(script_code, encoding="utf-8")
                self.installed_files.append(tgt_py)
                self._log(f"Custom deploy: {tgt_py}", "success")
            except Exception:
                pass

        except Exception as e:
            self._log(f"Custom folder deployment note: {e}", "warn")


def get_default_resolve_paths() -> Dict[str, Path]:
    """Returns detected standard and system Resolve scripts and workflow paths."""
    paths: Dict[str, Path] = {}
    if sys.platform == "win32":
        appdata = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        progdata = Path(os.environ.get("PROGRAMDATA", "C:/ProgramData"))
        paths["user_scripts"] = appdata / "Blackmagic Design" / "DaVinci Resolve" / "Support" / "Fusion" / "Scripts"
        paths["user_comp"] = paths["user_scripts"] / "Comp"
        paths["user_utility"] = paths["user_scripts"] / "Utility"
        paths["user_workflow"] = appdata / "Blackmagic Design" / "DaVinci Resolve" / "Support" / "Workflow Integration Plugins" / "com.xdrop.resolve.workflowintegration"
        paths["system_scripts"] = progdata / "Blackmagic Design" / "DaVinci Resolve" / "Fusion" / "Scripts"
        paths["system_comp"] = paths["system_scripts"] / "Comp"
        paths["system_workflow"] = progdata / "Blackmagic Design" / "DaVinci Resolve" / "Workflow Integration Plugins" / "com.xdrop.resolve.workflowintegration"
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / "Blackmagic Design" / "DaVinci Resolve"
        paths["user_scripts"] = base / "Fusion" / "Scripts"
        paths["user_comp"] = paths["user_scripts"] / "Comp"
        paths["user_utility"] = paths["user_scripts"] / "Utility"
        paths["user_workflow"] = base / "Workflow Integration Plugins" / "com.xdrop.resolve.workflowintegration"
        sys_base = Path("/Library/Application Support/Blackmagic Design/DaVinci Resolve")
        paths["system_scripts"] = sys_base / "Fusion" / "Scripts"
        paths["system_comp"] = paths["system_scripts"] / "Comp"
        paths["system_workflow"] = sys_base / "Workflow Integration Plugins" / "com.xdrop.resolve.workflowintegration"
    else:
        base = Path.home() / ".local/share/DaVinciResolve"
        paths["user_scripts"] = base / "Fusion" / "Scripts"
        paths["user_comp"] = paths["user_scripts"] / "Comp"
        paths["user_utility"] = paths["user_scripts"] / "Utility"
        paths["system_scripts"] = Path("/opt/resolve/Fusion/Scripts")
        paths["system_comp"] = paths["system_scripts"] / "Comp"
    return paths


# ==============================================================================
# GUI Installer Implementation
# ==============================================================================

class ResolveGuiInstaller:
    """Modern dark-themed studio GUI installer tailored specifically for DaVinci Resolve."""

    def __init__(self, initial_custom_dir: Optional[Path] = None):
        import tkinter as tk
        from tkinter import ttk, messagebox, filedialog

        self.tk = tk
        self.ttk = ttk
        self.messagebox = messagebox
        self.filedialog = filedialog

        self.root = tk.Tk()
        self.root.title("Xdrop Setup — DaVinci Resolve Edition")
        self.root.geometry("640x740")
        self.root.minsize(600, 700)
        self.root.configure(bg=COLOR_RESOLVE_BG)

        # Taskbar icon setup on Windows
        if sys.platform == "win32":
            try:
                import ctypes
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("com.xdrop.installer.resolve.1.0")
            except Exception:
                pass

        self._load_app_icons()
        self._center_window()

        # State Variables
        self.install_comp_lua_var = tk.BooleanVar(value=True)
        self.install_workflow_var = tk.BooleanVar(value=True)
        self.install_utility_py_var = tk.BooleanVar(value=True)
        self.install_engine_var = tk.BooleanVar(value=True)
        self.clean_legacy_var = tk.BooleanVar(value=True)

        self.location_mode_var = tk.StringVar(value="user")
        self.custom_path_var = tk.StringVar(value=str(initial_custom_dir) if initial_custom_dir else "")

        self.default_paths = get_default_resolve_paths()
        self.discovered_resolve_apps: List[DiscoveredApp] = []
        self.is_installing = False
        self.is_completed = False

        # Build UI layout
        self._build_header()
        self._build_detection_card()
        self._build_location_card()
        self._build_components_card()
        self._build_progress_card()
        self._build_action_bar()

        # Run asynchronous scan
        threading.Thread(target=self._run_async_scan, daemon=True).start()

    def _load_app_icons(self):
        candidates_ico = [
            SCRIPT_DIR / "assets" / "xdrop.ico",
            REPO_ROOT / "src" / "assets" / "xdrop.ico",
            REPO_ROOT / "src" / "assets" / "logo.ico",
            REPO_ROOT / "src" / "tools" / "assets" / "xdrop.ico",
        ]
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            meipass = Path(sys._MEIPASS)
            candidates_ico.extend([
                meipass / "src" / "assets" / "logo.ico",
                meipass / "src" / "assets" / "xdrop.ico",
                meipass / "xdrop.ico",
            ])

        for c in candidates_ico:
            if c.is_file():
                try:
                    self.root.iconbitmap(default=str(c))
                    break
                except Exception:
                    pass

        candidates_png = [
            SCRIPT_DIR / "assets" / "logo-40.png",
            REPO_ROOT / "src" / "tools" / "assets" / "logo-40.png",
            REPO_ROOT / "src" / "assets" / "logo.png",
        ]
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            meipass = Path(sys._MEIPASS)
            candidates_png.extend([
                meipass / "src" / "assets" / "logo.png",
                meipass / "logo.png",
            ])

        self._logo_img = None
        for c in candidates_png:
            if c.is_file():
                try:
                    self._logo_img = self.tk.PhotoImage(file=str(c))
                    self.root.iconphoto(False, self._logo_img)
                    break
                except Exception:
                    pass

    def _center_window(self):
        self.root.update_idletasks()
        w, h = 640, 740
        x = max(0, (self.root.winfo_screenwidth() // 2) - (w // 2))
        y = max(0, (self.root.winfo_screenheight() // 2) - (h // 2))
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def _build_header(self):
        header = self.tk.Frame(self.root, bg=COLOR_RESOLVE_BG, padx=24, pady=16)
        header.pack(fill=self.tk.X)

        title_row = self.tk.Frame(header, bg=COLOR_RESOLVE_BG)
        title_row.pack(anchor="w")

        if self._logo_img:
            lbl_logo = self.tk.Label(title_row, image=self._logo_img, bg=COLOR_RESOLVE_BG)
            lbl_logo.pack(side=self.tk.LEFT, padx=(0, 10))

        lbl_x = self.tk.Label(title_row, text="X", font=("Segoe UI", 24, "bold"), fg=COLOR_RESOLVE_CYAN, bg=COLOR_RESOLVE_BG)
        lbl_x.pack(side=self.tk.LEFT)

        lbl_drop = self.tk.Label(title_row, text="drop", font=("Segoe UI", 24, "bold"), fg=COLOR_RESOLVE_TEXT, bg=COLOR_RESOLVE_BG)
        lbl_drop.pack(side=self.tk.LEFT)

        badge_frame = self.tk.Frame(title_row, bg=COLOR_RESOLVE_CARD, highlightbackground=COLOR_RESOLVE_ACCENT, highlightthickness=1, padx=6, pady=2)
        badge_frame.pack(side=self.tk.LEFT, padx=(12, 0), pady=(4, 0))

        lbl_badge = self.tk.Label(badge_frame, text="DAVINCI RESOLVE EDITION", font=("Segoe UI", 8, "bold"), fg=COLOR_RESOLVE_ACCENT, bg=COLOR_RESOLVE_CARD)
        lbl_badge.pack()

        lbl_desc = self.tk.Label(
            header,
            text="Native Video Pipeline Importer • Supports DaVinci Resolve Free & Studio (18, 19, 20+)",
            font=("Segoe UI", 9),
            fg=COLOR_RESOLVE_TEXT_MUTED,
            bg=COLOR_RESOLVE_BG
        )
        lbl_desc.pack(anchor="w", pady=(4, 0))

        div = self.tk.Frame(self.root, bg=COLOR_RESOLVE_CARD_BORDER, height=1)
        div.pack(fill=self.tk.X, padx=24)

    def _build_detection_card(self):
        self.main_content = self.tk.Frame(self.root, bg=COLOR_RESOLVE_BG, padx=24, pady=12)
        self.main_content.pack(fill=self.tk.BOTH, expand=True)

        card = self.tk.Frame(self.main_content, bg=COLOR_RESOLVE_CARD, highlightbackground=COLOR_RESOLVE_CARD_BORDER, highlightthickness=1, padx=14, pady=10)
        card.pack(fill=self.tk.X, pady=(0, 10))

        top_row = self.tk.Frame(card, bg=COLOR_RESOLVE_CARD)
        top_row.pack(fill=self.tk.X)

        lbl_title = self.tk.Label(top_row, text="WORKSTATION INSTALLATION STATUS", font=("Segoe UI", 9, "bold"), fg=COLOR_RESOLVE_ACCENT, bg=COLOR_RESOLVE_CARD)
        lbl_title.pack(side=self.tk.LEFT)

        self.detect_badge = self.tk.Label(top_row, text="● Deep Scanning Drives...", font=("Segoe UI", 9, "bold"), fg=COLOR_RESOLVE_CYAN, bg=COLOR_RESOLVE_CARD)
        self.detect_badge.pack(side=self.tk.RIGHT)

        self.detect_details = self.tk.Label(
            card,
            text="Scanning all system drives and registry keys for Blackmagic DaVinci Resolve...",
            font=("Segoe UI", 9),
            fg=COLOR_RESOLVE_TEXT_MUTED,
            bg=COLOR_RESOLVE_CARD,
            justify=self.tk.LEFT,
            wraplength=570
        )
        self.detect_details.pack(anchor="w", pady=(4, 0))

    def _build_location_card(self):
        card = self.tk.Frame(self.main_content, bg=COLOR_RESOLVE_CARD, highlightbackground=COLOR_RESOLVE_CARD_BORDER, highlightthickness=1, padx=14, pady=10)
        card.pack(fill=self.tk.X, pady=(0, 10))

        lbl_title = self.tk.Label(card, text="INSTALLATION TARGET LOCATION", font=("Segoe UI", 9, "bold"), fg=COLOR_RESOLVE_CYAN, bg=COLOR_RESOLVE_CARD)
        lbl_title.pack(anchor="w", pady=(0, 6))

        # Radio 1: User Profile
        user_path_str = str(self.default_paths.get("user_comp", "Standard User Profile"))
        r1 = self.tk.Radiobutton(
            card,
            text=f" Standard User Profile (Recommended — zero admin permissions required)\n {user_path_str}",
            variable=self.location_mode_var,
            value="user",
            font=("Segoe UI", 9),
            fg=COLOR_RESOLVE_TEXT,
            bg=COLOR_RESOLVE_CARD,
            activebackground=COLOR_RESOLVE_CARD,
            activeforeground=COLOR_RESOLVE_CYAN,
            selectcolor=COLOR_RESOLVE_BG,
            justify=self.tk.LEFT,
            command=self._on_location_mode_change
        )
        r1.pack(anchor="w", pady=(0, 4))

        # Radio 2: Custom Directory
        r2 = self.tk.Radiobutton(
            card,
            text=" Custom Installation Directory (Non-standard drives, portable, or custom Fusion scripts folder)",
            variable=self.location_mode_var,
            value="custom",
            font=("Segoe UI", 9),
            fg=COLOR_RESOLVE_TEXT,
            bg=COLOR_RESOLVE_CARD,
            activebackground=COLOR_RESOLVE_CARD,
            activeforeground=COLOR_RESOLVE_CYAN,
            selectcolor=COLOR_RESOLVE_BG,
            justify=self.tk.LEFT,
            command=self._on_location_mode_change
        )
        r2.pack(anchor="w", pady=(0, 4))

        # Custom Folder Row
        self.custom_row = self.tk.Frame(card, bg=COLOR_RESOLVE_CARD)
        self.custom_row.pack(fill=self.tk.X, padx=(22, 0), pady=(2, 0))

        self.txt_custom_path = self.tk.Entry(
            self.custom_row,
            textvariable=self.custom_path_var,
            font=("Consolas", 9),
            bg=COLOR_RESOLVE_BG,
            fg=COLOR_RESOLVE_TEXT,
            insertbackground=COLOR_RESOLVE_CYAN,
            relief=self.tk.SOLID,
            bd=1
        )
        self.txt_custom_path.pack(side=self.tk.LEFT, fill=self.tk.X, expand=True, ipady=3)

        btn_browse = self.tk.Button(
            self.custom_row,
            text=" Browse... ",
            font=("Segoe UI", 9),
            bg=COLOR_RESOLVE_CARD_BORDER,
            fg=COLOR_RESOLVE_TEXT,
            activebackground=COLOR_RESOLVE_ACCENT,
            activeforeground="#000000",
            relief=self.tk.FLAT,
            padx=10,
            cursor="hand2",
            command=self._browse_custom_directory
        )
        btn_browse.pack(side=self.tk.RIGHT, padx=(6, 0))

        self._on_location_mode_change()

    def _build_components_card(self):
        card = self.tk.Frame(self.main_content, bg=COLOR_RESOLVE_CARD, highlightbackground=COLOR_RESOLVE_CARD_BORDER, highlightthickness=1, padx=14, pady=10)
        card.pack(fill=self.tk.X, pady=(0, 10))

        lbl_title = self.tk.Label(card, text="COMPONENTS & INTEGRATIONS", font=("Segoe UI", 9, "bold"), fg=COLOR_RESOLVE_CYAN, bg=COLOR_RESOLVE_CARD)
        lbl_title.pack(anchor="w", pady=(0, 6))

        # Checkbox 1: Comp Lua Script
        cb1 = self.tk.Checkbutton(
            card,
            text=" Native Comp Fusion UI Script (Xdrop.lua + Pre-configured Starter Bin.drb)",
            variable=self.install_comp_lua_var,
            font=("Segoe UI", 9),
            fg=COLOR_RESOLVE_TEXT,
            bg=COLOR_RESOLVE_CARD,
            activebackground=COLOR_RESOLVE_CARD,
            activeforeground=COLOR_RESOLVE_CYAN,
            selectcolor=COLOR_RESOLVE_BG,
            relief=self.tk.FLAT
        )
        cb1.pack(anchor="w")

        # Checkbox 2: Studio Workflow Integration
        cb2 = self.tk.Checkbutton(
            card,
            text=" DaVinci Resolve Studio Workflow Integration (Dockable Studio Panel)",
            variable=self.install_workflow_var,
            font=("Segoe UI", 9),
            fg=COLOR_RESOLVE_TEXT,
            bg=COLOR_RESOLVE_CARD,
            activebackground=COLOR_RESOLVE_CARD,
            activeforeground=COLOR_RESOLVE_CYAN,
            selectcolor=COLOR_RESOLVE_BG,
            relief=self.tk.FLAT
        )
        cb2.pack(anchor="w")

        # Checkbox 3: Utility Script
        cb3 = self.tk.Checkbutton(
            card,
            text=" Python Utility Launcher Script (Workspace -> Scripts -> Utility -> Xdrop)",
            variable=self.install_utility_py_var,
            font=("Segoe UI", 9),
            fg=COLOR_RESOLVE_TEXT,
            bg=COLOR_RESOLVE_CARD,
            activebackground=COLOR_RESOLVE_CARD,
            activeforeground=COLOR_RESOLVE_CYAN,
            selectcolor=COLOR_RESOLVE_BG,
            relief=self.tk.FLAT
        )
        cb3.pack(anchor="w")

        # Checkbox 4: Background Engine
        cb4 = self.tk.Checkbutton(
            card,
            text=" Zero-Trace Headless Background Engine (Auto-starts on demand, 0 CMD windows)",
            variable=self.install_engine_var,
            font=("Segoe UI", 9),
            fg=COLOR_RESOLVE_TEXT,
            bg=COLOR_RESOLVE_CARD,
            activebackground=COLOR_RESOLVE_CARD,
            activeforeground=COLOR_RESOLVE_CYAN,
            selectcolor=COLOR_RESOLVE_BG,
            relief=self.tk.FLAT
        )
        cb4.pack(anchor="w")

        # Checkbox 5: Clean Legacy
        cb5 = self.tk.Checkbutton(
            card,
            text=" Purge legacy ResolveFetch duplicate scripts (Safely preserves Snap Captions)",
            variable=self.clean_legacy_var,
            font=("Segoe UI", 9),
            fg=COLOR_RESOLVE_TEXT,
            bg=COLOR_RESOLVE_CARD,
            activebackground=COLOR_RESOLVE_CARD,
            activeforeground=COLOR_RESOLVE_CYAN,
            selectcolor=COLOR_RESOLVE_BG,
            relief=self.tk.FLAT
        )
        cb5.pack(anchor="w")

    def _build_progress_card(self):
        self.progress_frame = self.tk.Frame(self.main_content, bg=COLOR_RESOLVE_BG)
        self.progress_frame.pack(fill=self.tk.X, pady=(2, 0))

        self.lbl_status = self.tk.Label(
            self.progress_frame,
            text="Ready to install Xdrop for DaVinci Resolve.",
            font=("Segoe UI", 9),
            fg=COLOR_RESOLVE_TEXT_MUTED,
            bg=COLOR_RESOLVE_BG
        )
        self.lbl_status.pack(anchor="w", pady=(0, 4))

        style = self.ttk.Style()
        style.theme_use("default")
        style.configure(
            "Resolve.Horizontal.TProgressbar",
            background=COLOR_RESOLVE_ACCENT,
            troughcolor=COLOR_RESOLVE_CARD,
            borderwidth=0,
            thickness=6
        )
        self.progress_bar = self.ttk.Progressbar(
            self.progress_frame,
            style="Resolve.Horizontal.TProgressbar",
            mode="determinate"
        )
        self.progress_bar.pack(fill=self.tk.X)
        self.progress_bar["value"] = 0

    def _build_action_bar(self):
        action_frame = self.tk.Frame(self.root, bg=COLOR_RESOLVE_BG, padx=24, pady=16)
        action_frame.pack(fill=self.tk.X, side=self.tk.BOTTOM)

        div = self.tk.Frame(action_frame, bg=COLOR_RESOLVE_CARD_BORDER, height=1)
        div.pack(fill=self.tk.X, pady=(0, 14))

        row = self.tk.Frame(action_frame, bg=COLOR_RESOLVE_BG)
        row.pack(fill=self.tk.X)

        self.btn_cancel = self.tk.Button(
            row,
            text="Cancel",
            font=("Segoe UI", 9),
            fg=COLOR_RESOLVE_TEXT_MUTED,
            bg=COLOR_RESOLVE_CARD,
            activeforeground=COLOR_RESOLVE_TEXT,
            activebackground=COLOR_RESOLVE_CARD_BORDER,
            relief=self.tk.FLAT,
            padx=16,
            pady=6,
            cursor="hand2",
            command=self.root.destroy
        )
        self.btn_cancel.pack(side=self.tk.LEFT)

        self.btn_install = self.tk.Button(
            row,
            text="  Install for DaVinci Resolve  ",
            font=("Segoe UI", 10, "bold"),
            fg="#000000",
            bg=COLOR_RESOLVE_ACCENT,
            activeforeground="#000000",
            activebackground=COLOR_RESOLVE_HOVER,
            relief=self.tk.FLAT,
            padx=20,
            pady=7,
            cursor="hand2",
            command=self._start_installation
        )
        self.btn_install.pack(side=self.tk.RIGHT)

    def _on_location_mode_change(self):
        is_custom = self.location_mode_var.get() == "custom"
        self.txt_custom_path.config(state=self.tk.NORMAL if is_custom else self.tk.DISABLED)

    def _browse_custom_directory(self):
        self.location_mode_var.set("custom")
        self._on_location_mode_change()
        folder = self.filedialog.askdirectory(title="Select DaVinci Resolve or Fusion Scripts Directory")
        if folder:
            self.custom_path_var.set(folder)

    def _run_async_scan(self):
        try:
            scanner = DeepAppScanner()
            apps = scanner.scan()
            self.discovered_resolve_apps = [a for a in apps if a.app_id == "resolve"]

            def update_ui():
                if not self.root.winfo_exists():
                    return
                if self.discovered_resolve_apps:
                    app = self.discovered_resolve_apps[0]
                    status_str = " (Running)" if app.is_running else ""
                    self.detect_badge.config(text=f"✓ Detected: {app.name}{status_str}", fg=COLOR_RESOLVE_SUCCESS)
                    details = f"Version: {app.version}\nExecutable: {app.executable or 'Standard Path'}"
                    if app.is_running:
                        details += "\n⚠️ DaVinci Resolve is currently running. Please restart it after setup to load new scripts."
                    self.detect_details.config(text=details)
                else:
                    self.detect_badge.config(text="● Ready to Deploy", fg=COLOR_RESOLVE_CYAN)
                    self.detect_details.config(text="DaVinci Resolve not found in standard system directories. You can deploy to the standard user script folder or pick a custom folder.")

            self.root.after(0, update_ui)
        except Exception as e:
            def err_ui():
                if self.root.winfo_exists():
                    self.detect_badge.config(text="Scan Notice", fg=COLOR_RESOLVE_ACCENT)
                    self.detect_details.config(text=str(e))
            self.root.after(0, err_ui)

    def _start_installation(self):
        if self.is_completed:
            self.root.destroy()
            return
        if self.is_installing:
            return

        custom_dir = None
        if self.location_mode_var.get() == "custom":
            c_str = self.custom_path_var.get().strip()
            if not c_str:
                self.messagebox.showwarning("Custom Path Missing", "Please select or enter a valid directory path.")
                return
            custom_dir = Path(c_str)

        self.is_installing = True
        self.btn_install.config(state=self.tk.DISABLED, text="Installing...")
        self.btn_cancel.config(state=self.tk.DISABLED)

        threading.Thread(target=self._installation_thread, args=(custom_dir,), daemon=True).start()

    def _update_progress(self, percent: int, msg: str):
        def _apply():
            if self.root.winfo_exists():
                self.progress_bar["value"] = percent
                self.lbl_status.config(text=msg)
        self.root.after(0, _apply)

    def _installation_thread(self, custom_dir: Optional[Path]):
        try:
            self._update_progress(10, "Initializing DaVinci Resolve installer...")
            installer = ResolveExtensionInstaller(
                discovered=self.discovered_resolve_apps,
                custom_scripts_dir=custom_dir,
                log_callback=lambda m, lvl: self._update_progress(min(90, self.progress_bar["value"] + 5), m)
            )

            # Step 1: Headless Engine
            if self.install_engine_var.get():
                self._update_progress(25, "Installing zero-trace background engine service...")
                installer.install_desktop_service()
                time.sleep(0.3)

            # Step 2: Legacy Cleanup
            if self.clean_legacy_var.get():
                self._update_progress(45, "Purging duplicate legacy scripts (safely keeping Snap Captions)...")
                installer.clean_davinci_resolve_scripts()
                time.sleep(0.3)

            # Step 3: DaVinci Resolve Core
            self._update_progress(65, "Deploying Xdrop.lua, Starter Bin, and Workflow Integration...")
            installer.install_davinci_resolve()
            time.sleep(0.3)

            # Step 4: Custom Directory Deployment
            if custom_dir:
                self._update_progress(80, f"Deploying to custom directory: {custom_dir.name}...")
                installer.deploy_to_custom_scripts_dir(custom_dir)
                time.sleep(0.3)

            # Step 5: Timeline sidecars
            self._update_progress(95, "Configuring universal FCPXML timeline generation...")
            installer.configure_fcpxml_drag_and_drop()
            time.sleep(0.2)

            self._update_progress(100, "✓ DaVinci Resolve extensions successfully configured!")
            self.root.after(0, self._render_completion_screen)
        except Exception as e:
            self._update_progress(100, f"Error: {e}")
            def on_err():
                self.btn_install.config(state=self.tk.NORMAL, text="Retry Installation")
                self.btn_cancel.config(state=self.tk.NORMAL)
                self.is_installing = False
            self.root.after(0, on_err)

    def _render_completion_screen(self):
        self.is_completed = True
        self.btn_install.config(state=self.tk.NORMAL, text="  Finish & Close  ", bg=COLOR_RESOLVE_SUCCESS)
        self.btn_cancel.pack_forget()

        # Success Banner
        box = self.tk.Frame(self.main_content, bg=COLOR_RESOLVE_SUCCESS_BG, highlightbackground=COLOR_RESOLVE_SUCCESS, highlightthickness=1, padx=14, pady=12)
        box.pack(fill=self.tk.X, pady=(12, 0))

        title = self.tk.Label(box, text="HOW TO LAUNCH XDROP IN DAVINCI RESOLVE:", font=("Segoe UI", 10, "bold"), fg=COLOR_RESOLVE_SUCCESS, bg=COLOR_RESOLVE_SUCCESS_BG)
        title.pack(anchor="w")

        info_text = (
            "1. DaVinci Resolve Free & Studio (Unified Studio UI):\n"
            "   Top Menu -> Workspace -> Scripts -> Comp -> Xdrop\n"
            "   (Launches dedicated standalone window with canonical 000_Xdrop Assets bin)\n\n"
            "2. DaVinci Resolve Studio (Dockable Panel):\n"
            "   Top Menu -> Workspace -> Workflow Integrations -> Xdrop\n\n"
            "3. Background Engine: Online at http://127.0.0.1:8484 (0 CMD flashes)"
        )
        lbl_info = self.tk.Label(box, text=info_text, font=("Segoe UI", 9), fg=COLOR_RESOLVE_TEXT, bg=COLOR_RESOLVE_SUCCESS_BG, justify=self.tk.LEFT)
        lbl_info.pack(anchor="w", pady=(4, 0))

        # Launch buttons row
        btn_row = self.tk.Frame(box, bg=COLOR_RESOLVE_SUCCESS_BG)
        btn_row.pack(fill=self.tk.X, pady=(8, 0))

        resolve_exe = None
        if self.discovered_resolve_apps and self.discovered_resolve_apps[0].executable:
            resolve_exe = self.discovered_resolve_apps[0].executable

        if resolve_exe and resolve_exe.is_file():
            btn_launch = self.tk.Button(
                btn_row,
                text="  Launch DaVinci Resolve  ",
                font=("Segoe UI", 9, "bold"),
                bg=COLOR_RESOLVE_ACCENT,
                fg="#000000",
                relief=self.tk.FLAT,
                cursor="hand2",
                command=lambda: subprocess.Popen([str(resolve_exe)], start_new_session=True)
            )
            btn_launch.pack(side=self.tk.LEFT, padx=(0, 8))

        # Button to open Comp scripts directory in File Explorer
        comp_dir = self.default_paths.get("user_comp")
        if comp_dir and comp_dir.is_dir():
            btn_explore = self.tk.Button(
                btn_row,
                text=" Open Scripts Folder ",
                font=("Segoe UI", 9),
                bg=COLOR_RESOLVE_CARD,
                fg=COLOR_RESOLVE_TEXT,
                relief=self.tk.FLAT,
                cursor="hand2",
                command=lambda: os.startfile(str(comp_dir)) if sys.platform == "win32" else subprocess.Popen(["open", str(comp_dir)])
            )
            btn_explore.pack(side=self.tk.LEFT)

    def run(self):
        self.root.mainloop()


# ==============================================================================
# CLI Entry Point
# ==============================================================================

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
  Architecture: Standalone Studio UI (Comp/Xdrop.lua) + Workflow Integration
""")


def print_resolve_guide(discovered: List[DiscoveredApp]):
    print(f"\n{BOLD}{GREEN}========================================================================{RESET}")
    print(f"{BOLD}{GREEN}         DAVINCI RESOLVE EXTENSIONS SUCCESSFULLY CONFIGURED             {RESET}")
    print(f"{BOLD}{GREEN}========================================================================{RESET}")

    print(f"\n{BOLD}How to Launch Xdrop inside DaVinci Resolve:{RESET}\n")

    print(f"1. {BOLD}DaVinci Resolve Free & Studio (Unified Studio UI):{RESET}")
    print(f"   {CYAN}Top Menu -> Workspace -> Scripts -> Comp -> Xdrop{RESET}")
    print(f"   * Launches modern React Studio UI as a dedicated standalone window.")
    print(f"   * 100% Zero-Flicker: Zero CMD or console window flashes.")
    print(f"   * Pre-loads the canonical '000_Xdrop Assets' bin and sub-bins automatically.")

    print(f"\n2. {BOLD}DaVinci Resolve Studio (Workflow Integrations):{RESET}")
    print(f"   {CYAN}Top Menu -> Workspace -> Workflow Integrations -> Xdrop{RESET}")
    print(f"   * Dockable Studio panel next to Media Pool and Timeline.")

    print(f"\n3. {BOLD}Desktop Utility Script:{RESET}")
    print(f"   {CYAN}Top Menu -> Workspace -> Scripts -> Utility -> Xdrop{RESET}")

    print(f"\n4. {BOLD}Background Service Status:{RESET}")
    print(f"   Listening on {CYAN}http://127.0.0.1:8484{RESET} (auto-starts silently with Windows startup).\n")


def run_cli_installer(custom_dir: Optional[Path] = None):
    print_resolve_banner()
    print(f"System: {platform.system()} {platform.release()} ({platform.architecture()[0]})")
    print(f"Python: {sys.version.split()[0]}")
    print(f"Location: {BASE_DIR}")

    log_header("Phase 1: Scanning for DaVinci Resolve Installations Across All Drives")
    scanner = DeepAppScanner()
    all_apps = scanner.scan()
    resolve_apps = [a for a in all_apps if a.app_id == "resolve"]

    if resolve_apps:
        for app in resolve_apps:
            running_tag = f" {GREEN}(Currently Running){RESET}" if app.is_running else ""
            log_success(f"Found: {BOLD}{app.name}{RESET} - v{app.version}{running_tag}")
            if app.executable:
                log_info(f"Executable: {DIM}{app.executable}{RESET}")
    else:
        log_info("DaVinci Resolve not detected in standard locations (installing to standard script paths anyway).")

    log_header("Phase 2: Installing Native DaVinci Resolve Extensions")
    installer = ResolveExtensionInstaller(resolve_apps, custom_scripts_dir=custom_dir)
    installer.run_resolve_only()

    print_resolve_guide(resolve_apps)

    if getattr(sys, "frozen", False) and not any(arg in sys.argv for arg in ["--silent", "-y", "--non-interactive"]):
        try:
            input(f"\n{BOLD}Press Enter to exit...{RESET}")
        except Exception:
            pass


def main():
    parser = argparse.ArgumentParser(description="Xdrop DaVinci Resolve Dedicated Installer")
    parser.add_argument("--cli", action="store_true", help="Run in command-line mode without GUI")
    parser.add_argument("--silent", "-y", "--non-interactive", action="store_true", dest="silent", help="Run silently without user interaction")
    parser.add_argument("--custom-dir", "--path", type=str, default=None, help="Custom installation or scripts directory")
    args, unknown = parser.parse_known_args()

    custom_path = Path(args.custom_dir).resolve() if args.custom_dir else None

    # Determine whether to use GUI
    force_cli = args.cli or args.silent
    if not force_cli:
        try:
            app = ResolveGuiInstaller(initial_custom_dir=custom_path)
            app.run()
            return
        except Exception as gui_err:
            # Fall back to CLI if Tkinter/Display fails
            print(f"[Notice] GUI could not be initialized ({gui_err}). Switching to CLI mode...")

    run_cli_installer(custom_dir=custom_path)


if __name__ == "__main__":
    main()
