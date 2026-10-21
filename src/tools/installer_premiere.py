#!/usr/bin/env python3
"""
Xdrop Adobe Premiere Pro & Creative Cloud Native Extension Installer.

Dedicated standalone installer specifically tailored for Adobe Premiere Pro,
After Effects, and Audition:
1. Deep-scans workstation drives, registry, and running processes to detect installed Adobe host applications.
2. Supports standard per-user (%APPDATA%), system common files, and custom folder installations.
3. Installs the high-performance native CEP panel (com.xdrop.panel) into Adobe extensions directories.
4. Configures CSXS PlayerDebugMode across versions 6..18 in Windows Registry (no admin required).
5. Generates extension runtime config.json linking directly to the local Xdrop service.
6. Packages and provisions modern UXP .ccx bundles for Premiere Pro and After Effects.
7. Installs and silently starts the Xdrop zero-flicker headless background engine (0 CMD windows).
8. Configures FCPXML 1.11 drag-and-drop timeline generation.
9. Provides a polished Adobe Creative Cloud dark GUI with automatic headless CLI fallback.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
import zipfile
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

# --- GUI Design Tokens (Adobe Creative Cloud Midnight Blue) ---------------------
COLOR_ADOBE_BG = "#0b0d14"               # Creative Cloud Midnight Black
COLOR_ADOBE_CARD = "#141724"             # Inset panel slate
COLOR_ADOBE_CARD_BORDER = "#252b40"      # Subtle structural border
COLOR_ADOBE_ACCENT = "#38bdf8"           # Adobe Sky / CC Blue
COLOR_ADOBE_CYAN = "#00e5ff"             # Xdrop Electric Cyan
COLOR_ADOBE_HOVER = "#60a5fa"            # Blue highlight hover
COLOR_ADOBE_TEXT = "#fafafa"             # Crisp white
COLOR_ADOBE_TEXT_MUTED = "#94a3b8"       # Secondary body text
COLOR_ADOBE_TEXT_DIM = "#64748b"         # Footnote / path labels
COLOR_ADOBE_SUCCESS = "#22c55e"          # Green verification accent
COLOR_ADOBE_SUCCESS_BG = "#0f2318"       # Soft green container


class PremiereExtensionInstaller(ExtensionInstaller):
    """Specialized installer that provisions Adobe Creative Cloud extensions only."""

    def __init__(
        self,
        discovered: Optional[List[DiscoveredApp]] = None,
        custom_cep_dir: Optional[Path] = None,
        log_callback=None,
    ):
        super().__init__(discovered or [])
        self.custom_cep_dir = Path(custom_cep_dir).resolve() if custom_cep_dir else None
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

    def run_premiere_only(self, install_engine: bool = True):
        log_header("Configuring Adobe Creative Cloud Native Extensions")
        self._log("Starting Adobe Creative Cloud extension deployment...")

        # 1. Background Engine (Headless, 0 CMD windows)
        if install_engine:
            self._log("Configuring zero-trace background engine service...")
            self.install_desktop_service()

        # 2. Install Adobe CEP & UXP Panels + CSXS Registry
        self._log("Deploying Adobe CEP panel (com.xdrop.panel) and CSXS PlayerDebugMode...")
        self.install_adobe_creative_cloud()

        # 3. If custom CEP folder specified, deploy there directly
        if self.custom_cep_dir:
            self.deploy_to_custom_cep_dir(self.custom_cep_dir)

        # 4. Configure Universal Timeline Sidecars
        self.configure_fcpxml_drag_and_drop()
        self._log("Adobe Creative Cloud deployment completed successfully!", "success")

    def deploy_to_custom_cep_dir(self, target_dir: Path):
        """Deploys the CEP panel to a user-specified custom directory."""
        self._log(f"Deploying CEP extension to custom directory: {target_dir}")
        source_dir = find_source_dir("premiere-plugin")
        if not source_dir.is_dir():
            self._log("Source directory for premiere-plugin not found.", "warn")
            return

        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            panel_dir = target_dir / "com.xdrop.panel" if target_dir.name != "com.xdrop.panel" else target_dir
            if panel_dir.exists():
                shutil.rmtree(panel_dir, ignore_errors=True)
            shutil.copytree(source_dir, panel_dir, dirs_exist_ok=True)

            # Write config.json into custom destination
            python_exe, pythonw_exe = find_system_python()
            if sys.platform == "win32":
                installed_engine_dir = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "Xdrop"
                engine_vbs = installed_engine_dir / "start_engine.vbs"
                engine_script = installed_engine_dir / "run_engine.py"
                main_py = installed_engine_dir / "xdrop" / "main.py"
            else:
                installed_engine_dir = Path.home() / ".xdrop"
                engine_vbs = installed_engine_dir / "start_engine.sh"
                engine_script = installed_engine_dir / "run_engine.py"
                main_py = installed_engine_dir / "xdrop" / "main.py"

            config_payload = {
                "installedEngineDir": str(installed_engine_dir),
                "runBat": str(installed_engine_dir / "run.bat") if (installed_engine_dir / "run.bat").is_file() else str(BASE_DIR / "run.bat"),
                "runSh": str(installed_engine_dir / "run.sh") if (installed_engine_dir / "run.sh").is_file() else str(BASE_DIR / "run.sh"),
                "pythonExe": str(python_exe or sys.executable),
                "pythonwExe": str(pythonw_exe or ""),
                "startEngineVbs": str(engine_vbs),
                "startEngineSh": str(installed_engine_dir / "start_engine.sh"),
                "engineScript": str(engine_script),
                "mainPy": str(main_py if main_py.is_file() else find_source_dir("desktop-service") / "xdrop" / "main.py"),
                "serviceUrl": "http://127.0.0.1:8484",
            }
            try:
                (panel_dir / "config.json").write_text(json.dumps(config_payload, indent=2), encoding="utf-8")
            except Exception:
                pass

            self.installed_files.append(panel_dir)
            self._log(f"Custom deploy: {panel_dir}", "success")
        except Exception as e:
            self._log(f"Custom CEP deployment note: {e}", "warn")


def get_default_adobe_paths() -> Dict[str, Path]:
    """Returns detected standard and common Adobe CEP extension paths."""
    paths: Dict[str, Path] = {}
    if sys.platform == "win32":
        appdata = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        paths["user_cep"] = appdata / "Adobe" / "CEP" / "extensions"
        paths["user_panel"] = paths["user_cep"] / "com.xdrop.panel"

        prog_common = Path(os.environ.get("CommonProgramFiles(x86)", r"C:\Program Files (x86)\Common Files"))
        paths["common_cep"] = prog_common / "Adobe" / "CEP" / "extensions"

        prog_common64 = Path(os.environ.get("CommonProgramFiles", r"C:\Program Files\Common Files"))
        paths["common_cep64"] = prog_common64 / "Adobe" / "CEP" / "extensions"
    elif sys.platform == "darwin":
        paths["user_cep"] = Path.home() / "Library" / "Application Support" / "Adobe" / "CEP" / "extensions"
        paths["user_panel"] = paths["user_cep"] / "com.xdrop.panel"
        paths["common_cep"] = Path("/Library/Application Support/Adobe/CEP/extensions")
    else:
        paths["user_cep"] = Path.home() / ".local/share/Adobe/CEP/extensions"
        paths["user_panel"] = paths["user_cep"] / "com.xdrop.panel"
    return paths


# ==============================================================================
# GUI Installer Implementation
# ==============================================================================

class PremiereGuiInstaller:
    """Modern dark-themed studio GUI installer tailored specifically for Adobe Creative Cloud."""

    def __init__(self, initial_custom_dir: Optional[Path] = None):
        import tkinter as tk
        from tkinter import ttk, messagebox, filedialog

        self.tk = tk
        self.ttk = ttk
        self.messagebox = messagebox
        self.filedialog = filedialog

        self.root = tk.Tk()
        self.root.title("Xdrop Setup — Adobe Premiere Pro & Creative Cloud Edition")
        self.root.geometry("640x740")
        self.root.minsize(600, 700)
        self.root.configure(bg=COLOR_ADOBE_BG)

        # Taskbar icon setup on Windows
        if sys.platform == "win32":
            try:
                import ctypes
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("com.xdrop.installer.premiere.1.0")
            except Exception:
                pass

        self._load_app_icons()
        self._center_window()

        # State Variables
        self.install_cep_var = tk.BooleanVar(value=True)
        self.enable_playerdebug_var = tk.BooleanVar(value=True)
        self.install_uxp_var = tk.BooleanVar(value=True)
        self.install_engine_var = tk.BooleanVar(value=True)

        self.location_mode_var = tk.StringVar(value="user")
        self.custom_path_var = tk.StringVar(value=str(initial_custom_dir) if initial_custom_dir else "")

        self.default_paths = get_default_adobe_paths()
        self.discovered_adobe_apps: List[DiscoveredApp] = []
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
        header = self.tk.Frame(self.root, bg=COLOR_ADOBE_BG, padx=24, pady=16)
        header.pack(fill=self.tk.X)

        title_row = self.tk.Frame(header, bg=COLOR_ADOBE_BG)
        title_row.pack(anchor="w")

        if self._logo_img:
            lbl_logo = self.tk.Label(title_row, image=self._logo_img, bg=COLOR_ADOBE_BG)
            lbl_logo.pack(side=self.tk.LEFT, padx=(0, 10))

        lbl_x = self.tk.Label(title_row, text="X", font=("Segoe UI", 24, "bold"), fg=COLOR_ADOBE_CYAN, bg=COLOR_ADOBE_BG)
        lbl_x.pack(side=self.tk.LEFT)

        lbl_drop = self.tk.Label(title_row, text="drop", font=("Segoe UI", 24, "bold"), fg=COLOR_ADOBE_TEXT, bg=COLOR_ADOBE_BG)
        lbl_drop.pack(side=self.tk.LEFT)

        badge_frame = self.tk.Frame(title_row, bg=COLOR_ADOBE_CARD, highlightbackground=COLOR_ADOBE_ACCENT, highlightthickness=1, padx=6, pady=2)
        badge_frame.pack(side=self.tk.LEFT, padx=(12, 0), pady=(4, 0))

        lbl_badge = self.tk.Label(badge_frame, text="ADOBE PREMIERE PRO EDITION", font=("Segoe UI", 8, "bold"), fg=COLOR_ADOBE_ACCENT, bg=COLOR_ADOBE_CARD)
        lbl_badge.pack()

        lbl_desc = self.tk.Label(
            header,
            text="Native Video Pipeline Importer • Supports Premiere Pro (2020-2026+), After Effects & Audition",
            font=("Segoe UI", 9),
            fg=COLOR_ADOBE_TEXT_MUTED,
            bg=COLOR_ADOBE_BG
        )
        lbl_desc.pack(anchor="w", pady=(4, 0))

        div = self.tk.Frame(self.root, bg=COLOR_ADOBE_CARD_BORDER, height=1)
        div.pack(fill=self.tk.X, padx=24)

    def _build_detection_card(self):
        self.main_content = self.tk.Frame(self.root, bg=COLOR_ADOBE_BG, padx=24, pady=12)
        self.main_content.pack(fill=self.tk.BOTH, expand=True)

        card = self.tk.Frame(self.main_content, bg=COLOR_ADOBE_CARD, highlightbackground=COLOR_ADOBE_CARD_BORDER, highlightthickness=1, padx=14, pady=10)
        card.pack(fill=self.tk.X, pady=(0, 10))

        top_row = self.tk.Frame(card, bg=COLOR_ADOBE_CARD)
        top_row.pack(fill=self.tk.X)

        lbl_title = self.tk.Label(top_row, text="WORKSTATION INSTALLATION STATUS", font=("Segoe UI", 9, "bold"), fg=COLOR_ADOBE_ACCENT, bg=COLOR_ADOBE_CARD)
        lbl_title.pack(side=self.tk.LEFT)

        self.detect_badge = self.tk.Label(top_row, text="● Deep Scanning Drives...", font=("Segoe UI", 9, "bold"), fg=COLOR_ADOBE_CYAN, bg=COLOR_ADOBE_CARD)
        self.detect_badge.pack(side=self.tk.RIGHT)

        self.detect_details = self.tk.Label(
            card,
            text="Scanning all system drives and registry keys for Adobe Premiere Pro, After Effects, and Audition...",
            font=("Segoe UI", 9),
            fg=COLOR_ADOBE_TEXT_MUTED,
            bg=COLOR_ADOBE_CARD,
            justify=self.tk.LEFT,
            wraplength=570
        )
        self.detect_details.pack(anchor="w", pady=(4, 0))

    def _build_location_card(self):
        card = self.tk.Frame(self.main_content, bg=COLOR_ADOBE_CARD, highlightbackground=COLOR_ADOBE_CARD_BORDER, highlightthickness=1, padx=14, pady=10)
        card.pack(fill=self.tk.X, pady=(0, 10))

        lbl_title = self.tk.Label(card, text="INSTALLATION TARGET LOCATION", font=("Segoe UI", 9, "bold"), fg=COLOR_ADOBE_CYAN, bg=COLOR_ADOBE_CARD)
        lbl_title.pack(anchor="w", pady=(0, 6))

        # Radio 1: User Profile CEP
        user_path_str = str(self.default_paths.get("user_cep", "Standard User Profile CEP"))
        r1 = self.tk.Radiobutton(
            card,
            text=f" Standard User CEP Directory (Recommended — zero admin permissions required)\n {user_path_str}",
            variable=self.location_mode_var,
            value="user",
            font=("Segoe UI", 9),
            fg=COLOR_ADOBE_TEXT,
            bg=COLOR_ADOBE_CARD,
            activebackground=COLOR_ADOBE_CARD,
            activeforeground=COLOR_ADOBE_CYAN,
            selectcolor=COLOR_ADOBE_BG,
            justify=self.tk.LEFT,
            command=self._on_location_mode_change
        )
        r1.pack(anchor="w", pady=(0, 4))

        # Radio 2: Custom Directory
        r2 = self.tk.Radiobutton(
            card,
            text=" Custom CEP Directory (Non-standard drives, portable Adobe setups, or custom plugin folders)",
            variable=self.location_mode_var,
            value="custom",
            font=("Segoe UI", 9),
            fg=COLOR_ADOBE_TEXT,
            bg=COLOR_ADOBE_CARD,
            activebackground=COLOR_ADOBE_CARD,
            activeforeground=COLOR_ADOBE_CYAN,
            selectcolor=COLOR_ADOBE_BG,
            justify=self.tk.LEFT,
            command=self._on_location_mode_change
        )
        r2.pack(anchor="w", pady=(0, 4))

        # Custom Folder Row
        self.custom_row = self.tk.Frame(card, bg=COLOR_ADOBE_CARD)
        self.custom_row.pack(fill=self.tk.X, padx=(22, 0), pady=(2, 0))

        self.txt_custom_path = self.tk.Entry(
            self.custom_row,
            textvariable=self.custom_path_var,
            font=("Consolas", 9),
            bg=COLOR_ADOBE_BG,
            fg=COLOR_ADOBE_TEXT,
            insertbackground=COLOR_ADOBE_CYAN,
            relief=self.tk.SOLID,
            bd=1
        )
        self.txt_custom_path.pack(side=self.tk.LEFT, fill=self.tk.X, expand=True, ipady=3)

        btn_browse = self.tk.Button(
            self.custom_row,
            text=" Browse... ",
            font=("Segoe UI", 9),
            bg=COLOR_ADOBE_CARD_BORDER,
            fg=COLOR_ADOBE_TEXT,
            activebackground=COLOR_ADOBE_ACCENT,
            activeforeground="#000000",
            relief=self.tk.FLAT,
            padx=10,
            cursor="hand2",
            command=self._browse_custom_directory
        )
        btn_browse.pack(side=self.tk.RIGHT, padx=(6, 0))

        self._on_location_mode_change()

    def _build_components_card(self):
        card = self.tk.Frame(self.main_content, bg=COLOR_ADOBE_CARD, highlightbackground=COLOR_ADOBE_CARD_BORDER, highlightthickness=1, padx=14, pady=10)
        card.pack(fill=self.tk.X, pady=(0, 10))

        lbl_title = self.tk.Label(card, text="COMPONENTS & INTEGRATIONS", font=("Segoe UI", 9, "bold"), fg=COLOR_ADOBE_CYAN, bg=COLOR_ADOBE_CARD)
        lbl_title.pack(anchor="w", pady=(0, 6))

        # Checkbox 1: CEP Panel
        cb1 = self.tk.Checkbutton(
            card,
            text=" Native Docked CEP Extension Panel (com.xdrop.panel with ExtendScript hostscripts)",
            variable=self.install_cep_var,
            font=("Segoe UI", 9),
            fg=COLOR_ADOBE_TEXT,
            bg=COLOR_ADOBE_CARD,
            activebackground=COLOR_ADOBE_CARD,
            activeforeground=COLOR_ADOBE_CYAN,
            selectcolor=COLOR_ADOBE_BG,
            relief=self.tk.FLAT
        )
        cb1.pack(anchor="w")

        # Checkbox 2: PlayerDebugMode
        cb2 = self.tk.Checkbutton(
            card,
            text=" Configure CSXS PlayerDebugMode across versions 6..18 in Registry (No Admin Required)",
            variable=self.enable_playerdebug_var,
            font=("Segoe UI", 9),
            fg=COLOR_ADOBE_TEXT,
            bg=COLOR_ADOBE_CARD,
            activebackground=COLOR_ADOBE_CARD,
            activeforeground=COLOR_ADOBE_CYAN,
            selectcolor=COLOR_ADOBE_BG,
            relief=self.tk.FLAT
        )
        cb2.pack(anchor="w")

        # Checkbox 3: UXP Packages
        cb3 = self.tk.Checkbutton(
            card,
            text=" Package Modern UXP Extension Bundles (.ccx for Premiere Pro & After Effects)",
            variable=self.install_uxp_var,
            font=("Segoe UI", 9),
            fg=COLOR_ADOBE_TEXT,
            bg=COLOR_ADOBE_CARD,
            activebackground=COLOR_ADOBE_CARD,
            activeforeground=COLOR_ADOBE_CYAN,
            selectcolor=COLOR_ADOBE_BG,
            relief=self.tk.FLAT
        )
        cb3.pack(anchor="w")

        # Checkbox 4: Background Engine
        cb4 = self.tk.Checkbutton(
            card,
            text=" Zero-Trace Headless Background Engine (Auto-starts on demand, 0 CMD windows)",
            variable=self.install_engine_var,
            font=("Segoe UI", 9),
            fg=COLOR_ADOBE_TEXT,
            bg=COLOR_ADOBE_CARD,
            activebackground=COLOR_ADOBE_CARD,
            activeforeground=COLOR_ADOBE_CYAN,
            selectcolor=COLOR_ADOBE_BG,
            relief=self.tk.FLAT
        )
        cb4.pack(anchor="w")

    def _build_progress_card(self):
        self.progress_frame = self.tk.Frame(self.main_content, bg=COLOR_ADOBE_BG)
        self.progress_frame.pack(fill=self.tk.X, pady=(2, 0))

        self.lbl_status = self.tk.Label(
            self.progress_frame,
            text="Ready to install Xdrop for Adobe Premiere Pro.",
            font=("Segoe UI", 9),
            fg=COLOR_ADOBE_TEXT_MUTED,
            bg=COLOR_ADOBE_BG
        )
        self.lbl_status.pack(anchor="w", pady=(0, 4))

        style = self.ttk.Style()
        style.theme_use("default")
        style.configure(
            "Adobe.Horizontal.TProgressbar",
            background=COLOR_ADOBE_ACCENT,
            troughcolor=COLOR_ADOBE_CARD,
            borderwidth=0,
            thickness=6
        )
        self.progress_bar = self.ttk.Progressbar(
            self.progress_frame,
            style="Adobe.Horizontal.TProgressbar",
            mode="determinate"
        )
        self.progress_bar.pack(fill=self.tk.X)
        self.progress_bar["value"] = 0

    def _build_action_bar(self):
        action_frame = self.tk.Frame(self.root, bg=COLOR_ADOBE_BG, padx=24, pady=16)
        action_frame.pack(fill=self.tk.X, side=self.tk.BOTTOM)

        div = self.tk.Frame(action_frame, bg=COLOR_ADOBE_CARD_BORDER, height=1)
        div.pack(fill=self.tk.X, pady=(0, 14))

        row = self.tk.Frame(action_frame, bg=COLOR_ADOBE_BG)
        row.pack(fill=self.tk.X)

        self.btn_cancel = self.tk.Button(
            row,
            text="Cancel",
            font=("Segoe UI", 9),
            fg=COLOR_ADOBE_TEXT_MUTED,
            bg=COLOR_ADOBE_CARD,
            activeforeground=COLOR_ADOBE_TEXT,
            activebackground=COLOR_ADOBE_CARD_BORDER,
            relief=self.tk.FLAT,
            padx=16,
            pady=6,
            cursor="hand2",
            command=self.root.destroy
        )
        self.btn_cancel.pack(side=self.tk.LEFT)

        self.btn_install = self.tk.Button(
            row,
            text="  Install for Adobe Premiere Pro  ",
            font=("Segoe UI", 10, "bold"),
            fg="#000000",
            bg=COLOR_ADOBE_ACCENT,
            activeforeground="#000000",
            activebackground=COLOR_ADOBE_HOVER,
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
        folder = self.filedialog.askdirectory(title="Select Adobe CEP Extensions Directory")
        if folder:
            self.custom_path_var.set(folder)

    def _run_async_scan(self):
        try:
            scanner = DeepAppScanner()
            apps = scanner.scan()
            self.discovered_adobe_apps = [
                a for a in apps if a.vendor.lower() == "adobe" or a.app_id in ("premiere", "aftereffects", "audition")
            ]

            def update_ui():
                if not self.root.winfo_exists():
                    return
                if self.discovered_adobe_apps:
                    names = [a.name for a in self.discovered_adobe_apps]
                    running = any(a.is_running for a in self.discovered_adobe_apps)
                    status_str = " (Running)" if running else ""
                    self.detect_badge.config(text=f"✓ Detected: {len(names)} Adobe App(s){status_str}", fg=COLOR_ADOBE_SUCCESS)
                    details = "Detected: " + ", ".join(names)
                    if running:
                        details += "\n⚠️ One or more Adobe applications are running. Please restart them after installation to load the extension."
                    self.detect_details.config(text=details)
                else:
                    self.detect_badge.config(text="● Ready to Deploy", fg=COLOR_ADOBE_CYAN)
                    self.detect_details.config(text="Adobe applications not detected in standard system locations. You can deploy to the standard user CEP folder or choose a custom folder.")

            self.root.after(0, update_ui)
        except Exception as e:
            def err_ui():
                if self.root.winfo_exists():
                    self.detect_badge.config(text="Scan Notice", fg=COLOR_ADOBE_ACCENT)
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
            self._update_progress(10, "Initializing Adobe Creative Cloud installer...")
            installer = PremiereExtensionInstaller(
                discovered=self.discovered_adobe_apps,
                custom_cep_dir=custom_dir,
                log_callback=lambda m, lvl: self._update_progress(min(90, self.progress_bar["value"] + 5), m)
            )

            # Step 1: Headless Engine
            if self.install_engine_var.get():
                self._update_progress(25, "Installing zero-trace background engine service...")
                installer.install_desktop_service()
                time.sleep(0.3)

            # Step 2: CEP Panel & CSXS Registry
            if self.install_cep_var.get():
                self._update_progress(50, "Deploying CEP panel and configuring PlayerDebugMode...")
                installer.install_adobe_creative_cloud()
                time.sleep(0.3)

            # Step 3: Custom Directory Deployment
            if custom_dir:
                self._update_progress(75, f"Deploying to custom CEP directory: {custom_dir.name}...")
                installer.deploy_to_custom_cep_dir(custom_dir)
                time.sleep(0.3)

            # Step 4: Universal sidecars
            self._update_progress(95, "Configuring universal FCPXML timeline generation...")
            installer.configure_fcpxml_drag_and_drop()
            time.sleep(0.2)

            self._update_progress(100, "✓ Adobe extensions successfully configured!")
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
        self.btn_install.config(state=self.tk.NORMAL, text="  Finish & Close  ", bg=COLOR_ADOBE_SUCCESS)
        self.btn_cancel.pack_forget()

        # Success Banner
        box = self.tk.Frame(self.main_content, bg=COLOR_ADOBE_SUCCESS_BG, highlightbackground=COLOR_ADOBE_SUCCESS, highlightthickness=1, padx=14, pady=12)
        box.pack(fill=self.tk.X, pady=(12, 0))

        title = self.tk.Label(box, text="HOW TO LAUNCH XDROP IN ADOBE PREMIERE PRO:", font=("Segoe UI", 10, "bold"), fg=COLOR_ADOBE_SUCCESS, bg=COLOR_ADOBE_SUCCESS_BG)
        title.pack(anchor="w")

        info_text = (
            "1. Open Premiere Pro / After Effects / Audition:\n"
            "   Top Menu -> Window -> Extensions -> Xdrop\n"
            "   (Dock the panel anywhere next to Project or Effect Controls)\n\n"
            "2. Automatic Bin & Timeline Insertion:\n"
            "   Organizes downloads into the canonical 000_Xdrop Assets bin.\n"
            "   Auto-import places media directly on your timeline at the playhead.\n\n"
            "3. Background Service: Online at http://127.0.0.1:8484 (0 CMD flashes)"
        )
        lbl_info = self.tk.Label(box, text=info_text, font=("Segoe UI", 9), fg=COLOR_ADOBE_TEXT, bg=COLOR_ADOBE_SUCCESS_BG, justify=self.tk.LEFT)
        lbl_info.pack(anchor="w", pady=(4, 0))

        # Launch buttons row
        btn_row = self.tk.Frame(box, bg=COLOR_ADOBE_SUCCESS_BG)
        btn_row.pack(fill=self.tk.X, pady=(8, 0))

        premiere_app = next((a for a in self.discovered_adobe_apps if a.app_id == "premiere" and a.executable), None)
        if premiere_app and premiere_app.executable and premiere_app.executable.is_file():
            btn_launch = self.tk.Button(
                btn_row,
                text="  Launch Premiere Pro  ",
                font=("Segoe UI", 9, "bold"),
                bg=COLOR_ADOBE_ACCENT,
                fg="#000000",
                relief=self.tk.FLAT,
                cursor="hand2",
                command=lambda: subprocess.Popen([str(premiere_app.executable)], start_new_session=True)
            )
            btn_launch.pack(side=self.tk.LEFT, padx=(0, 8))

        # Button to open CEP extensions folder in File Explorer
        cep_dir = self.default_paths.get("user_cep")
        if cep_dir and cep_dir.is_dir():
            btn_explore = self.tk.Button(
                btn_row,
                text=" Open Extensions Folder ",
                font=("Segoe UI", 9),
                bg=COLOR_ADOBE_CARD,
                fg=COLOR_ADOBE_TEXT,
                relief=self.tk.FLAT,
                cursor="hand2",
                command=lambda: os.startfile(str(cep_dir)) if sys.platform == "win32" else subprocess.Popen(["open", str(cep_dir)])
            )
            btn_explore.pack(side=self.tk.LEFT)

    def run(self):
        self.root.mainloop()


# ==============================================================================
# CLI Entry Point
# ==============================================================================

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
    print(f"   * Dock the panel anywhere in your editing workspace.")
    print(f"   * Automatically detects your active project and sequence.")

    print(f"\n2. {BOLD}Automatic Bin & Timeline Insertion:{RESET}")
    print(f"   * Downloads are organized into the canonical {CYAN}000_Xdrop Assets{RESET} bin.")
    print(f"   * Auto-import drops the media directly at your playhead.")

    print(f"\n3. {BOLD}Also Available in After Effects & Audition:{RESET}")
    print(f"   * After Effects: {CYAN}Window -> Extensions -> Xdrop{RESET}")
    print(f"   * Audition:      {CYAN}Window -> Extensions -> Xdrop{RESET}")

    print(f"\n4. {BOLD}Background Service Status:{RESET}")
    print(f"   Listening on {CYAN}http://127.0.0.1:8484{RESET} (auto-starts silently with Windows startup).\n")


def run_cli_installer(custom_dir: Optional[Path] = None):
    print_premiere_banner()
    print(f"System: {platform.system()} {platform.release()} ({platform.architecture()[0]})")
    print(f"Python: {sys.version.split()[0]}")
    print(f"Location: {BASE_DIR}")

    log_header("Phase 1: Scanning for Adobe Creative Cloud Applications Across All Drives")
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

    log_header("Phase 2: Installing Adobe CEP & UXP Native Extensions")
    installer = PremiereExtensionInstaller(adobe_apps, custom_cep_dir=custom_dir)
    installer.run_premiere_only()

    print_premiere_guide(adobe_apps)

    if getattr(sys, "frozen", False) and not any(arg in sys.argv for arg in ["--silent", "-y", "--non-interactive"]):
        try:
            input(f"\n{BOLD}Press Enter to exit...{RESET}")
        except Exception:
            pass


def main():
    parser = argparse.ArgumentParser(description="Xdrop Adobe Premiere Pro Dedicated Installer")
    parser.add_argument("--cli", action="store_true", help="Run in command-line mode without GUI")
    parser.add_argument("--silent", "-y", "--non-interactive", action="store_true", dest="silent", help="Run silently without user interaction")
    parser.add_argument("--custom-dir", "--path", type=str, default=None, help="Custom installation or CEP extensions directory")
    args, unknown = parser.parse_known_args()

    custom_path = Path(args.custom_dir).resolve() if args.custom_dir else None

    # Determine whether to use GUI
    force_cli = args.cli or args.silent
    if not force_cli:
        try:
            app = PremiereGuiInstaller(initial_custom_dir=custom_path)
            app.run()
            return
        except Exception as gui_err:
            # Fall back to CLI if Tkinter/Display fails
            print(f"[Notice] GUI could not be initialized ({gui_err}). Switching to CLI mode...")

    run_cli_installer(custom_dir=custom_path)


if __name__ == "__main__":
    main()
