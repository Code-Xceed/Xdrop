#!/usr/bin/env python3
"""
Xdrop Adobe Premiere Pro & Creative Cloud Native Extension Installer.

Minimal, usable, and professional installer for Adobe Premiere Pro,
After Effects, and Audition:
1. Deep-scans workstation drives, registry, and running processes to detect installed Adobe host applications.
2. Supports standard per-user (%APPDATA%), system common files, and custom folder installations.
3. Installs the high-performance native CEP panel (com.xdrop.panel) into Adobe extensions directories.
4. Configures CSXS PlayerDebugMode across versions 6..18 in Windows Registry (no admin required).
5. Generates extension runtime config.json linking directly to the local Xdrop service.
6. Packages and provisions modern UXP .ccx bundles for Premiere Pro and After Effects.
7. Installs and silently starts the Xdrop zero-flicker headless background engine (0 CMD windows).
8. Provides a minimal, studio-grade dark GUI with automatic headless CLI fallback.
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

# --- Minimal Design Tokens (Creative Cloud Midnight / Blue) ---------------------
COLOR_BG = "#0c0d12"             # Deep Midnight Black
COLOR_CARD = "#141620"           # Inset surface
COLOR_CARD_BORDER = "#222638"    # Subtle 1px boundary
COLOR_ACCENT = "#38bdf8"         # Creative Cloud Sky Blue
COLOR_ACCENT_HOVER = "#0284c7"   # Blue on press
COLOR_CYAN = "#00e5ff"           # Xdrop Cyan
COLOR_TEXT = "#fafafa"           # Crisp white
COLOR_TEXT_MUTED = "#94a3b8"     # Secondary body text
COLOR_TEXT_DIM = "#64748b"       # Footnote / meta
COLOR_SUCCESS = "#22c55e"        # Emerald green
COLOR_SUCCESS_BG = "#0d2218"     # Green container
COLOR_SUCCESS_BORDER = "#1b4d32" # Green boundary
COLOR_WARN = "#f59e0b"


def load_app_icon_image(target_size: int = 34) -> Optional[object]:
    """Safely loads a crisp, compact app icon for the header without heavy dependencies."""
    import tkinter as tk
    candidates = [
        SCRIPT_DIR / "assets" / "logo-40.png",
        REPO_ROOT / "src" / "tools" / "assets" / "logo-40.png",
        REPO_ROOT / "src" / "tools" / "assets" / "logo-64.png",
    ]
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        meipass = Path(sys._MEIPASS)
        candidates = [
            meipass / "src" / "tools" / "assets" / "logo-40.png",
            meipass / "src" / "tools" / "assets" / "logo-64.png",
            meipass / "assets" / "logo-40.png",
        ] + candidates

    for c in candidates:
        if c.is_file():
            try:
                photo = tk.PhotoImage(file=str(c))
                w = photo.width()
                if w > target_size * 1.4:
                    factor = max(1, round(w / target_size))
                    return photo.subsample(factor, factor)
                return photo
            except Exception:
                pass
    return None


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
# Minimal, Usable, Professional GUI
# ==============================================================================

class PremiereGuiInstaller:
    """Minimal, elegant studio installer tailored specifically for Adobe Creative Cloud."""

    def __init__(self, initial_custom_dir: Optional[Path] = None):
        import tkinter as tk
        from tkinter import ttk, filedialog

        self.tk = tk
        self.ttk = ttk
        self.filedialog = filedialog

        self.root = tk.Tk()
        self.root.title("Xdrop Setup — Adobe Premiere Pro")
        self.root.geometry("520x460")
        self.root.minsize(520, 460)
        self.root.maxsize(520, 460)
        self.root.resizable(False, False)
        self.root.configure(bg=COLOR_BG)

        # Windows taskbar AppUserModelID
        if sys.platform == "win32":
            try:
                import ctypes
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("com.xdrop.installer.premiere.1.0")
            except Exception:
                pass

        self._load_app_icons()
        self._center_window()

        self.default_paths = get_default_adobe_paths()
        self.target_dir = Path(initial_custom_dir).resolve() if initial_custom_dir else self.default_paths.get("user_cep")
        self.is_custom_location = initial_custom_dir is not None

        self.discovered_adobe_apps: List[DiscoveredApp] = []
        self.is_installing = False
        self.is_completed = False

        self._build_ui()
        threading.Thread(target=self._run_async_scan, daemon=True).start()

    def _load_app_icons(self):
        candidates_ico = [
            SCRIPT_DIR / "assets" / "xdrop.ico",
            REPO_ROOT / "src" / "assets" / "xdrop.ico",
            REPO_ROOT / "src" / "assets" / "logo.ico",
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

        self._logo_photo = load_app_icon_image(size=32)

    def _center_window(self):
        self.root.update_idletasks()
        w, h = 520, 460
        x = max(0, (self.root.winfo_screenwidth() // 2) - (w // 2))
        y = max(0, (self.root.winfo_screenheight() // 2) - (h // 2))
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def _build_ui(self):
        self.container = self.tk.Frame(self.root, bg=COLOR_BG, padx=28, pady=24)
        self.container.pack(fill=self.tk.BOTH, expand=True)

        # 1. Header Row
        header = self.tk.Frame(self.container, bg=COLOR_BG)
        header.pack(fill=self.tk.X, pady=(0, 16))

        if self._logo_photo:
            lbl_logo = self.tk.Label(header, image=self._logo_photo, bg=COLOR_BG)
            lbl_logo.pack(side=self.tk.LEFT, padx=(0, 12))

        title_col = self.tk.Frame(header, bg=COLOR_BG)
        title_col.pack(side=self.tk.LEFT, fill=self.tk.Y)

        title_row = self.tk.Frame(title_col, bg=COLOR_BG)
        title_row.pack(anchor="w")

        lbl_title = self.tk.Label(
            title_row,
            text="Xdrop",
            font=("Segoe UI", 16, "bold"),
            fg=COLOR_TEXT,
            bg=COLOR_BG
        )
        lbl_title.pack(side=self.tk.LEFT)

        lbl_pill = self.tk.Label(
            title_row,
            text=" Premiere Pro & CC ",
            font=("Segoe UI", 9, "bold"),
            fg=COLOR_ACCENT,
            bg="#162438",
            padx=6,
            pady=2
        )
        lbl_pill.pack(side=self.tk.LEFT, padx=(8, 0))

        lbl_sub = self.tk.Label(
            title_col,
            text="High-performance media importer for Adobe Premiere Pro, AE & Audition",
            font=("Segoe UI", 9),
            fg=COLOR_TEXT_DIM,
            bg=COLOR_BG
        )
        lbl_sub.pack(anchor="w", pady=(2, 0))

        # 2. Status Detection Strip
        self.detect_card = self.tk.Frame(
            self.container,
            bg=COLOR_CARD,
            highlightbackground=COLOR_CARD_BORDER,
            highlightthickness=1,
            padx=14,
            pady=10
        )
        self.detect_card.pack(fill=self.tk.X, pady=(0, 14))

        strip_row = self.tk.Frame(self.detect_card, bg=COLOR_CARD)
        strip_row.pack(fill=self.tk.X)

        self.lbl_detect_dot = self.tk.Label(strip_row, text="●", font=("Segoe UI", 10), fg=COLOR_CYAN, bg=COLOR_CARD)
        self.lbl_detect_dot.pack(side=self.tk.LEFT, padx=(0, 6))

        self.lbl_detect_text = self.tk.Label(
            strip_row,
            text="Scanning workstation for Adobe applications...",
            font=("Segoe UI", 9, "bold"),
            fg=COLOR_TEXT,
            bg=COLOR_CARD
        )
        self.lbl_detect_text.pack(side=self.tk.LEFT)

        self.lbl_detect_ver = self.tk.Label(strip_row, text="", font=("Segoe UI", 9), fg=COLOR_TEXT_DIM, bg=COLOR_CARD)
        self.lbl_detect_ver.pack(side=self.tk.RIGHT)

        self.lbl_detect_warn = self.tk.Label(
            self.detect_card,
            text="",
            font=("Segoe UI", 8),
            fg=COLOR_WARN,
            bg=COLOR_CARD
        )

        # 3. Features Card (Clean, minimal bullet overview)
        feat_card = self.tk.Frame(
            self.container,
            bg=COLOR_CARD,
            highlightbackground=COLOR_CARD_BORDER,
            highlightthickness=1,
            padx=14,
            pady=12
        )
        feat_card.pack(fill=self.tk.X, pady=(0, 16))

        feats = [
            ("✓", "Native docked panel (Window → Extensions → Xdrop)"),
            ("✓", "Automatic bin import & playhead timeline insertion"),
            ("✓", "Zero-flicker background engine (auto-starts on demand, 0 CMD windows)"),
        ]
        for mark, desc in feats:
            row = self.tk.Frame(feat_card, bg=COLOR_CARD)
            row.pack(fill=self.tk.X, pady=2)
            self.tk.Label(row, text=mark, font=("Segoe UI", 9, "bold"), fg=COLOR_SUCCESS, bg=COLOR_CARD).pack(side=self.tk.LEFT, padx=(0, 8))
            self.tk.Label(row, text=desc, font=("Segoe UI", 9), fg=COLOR_TEXT_MUTED, bg=COLOR_CARD).pack(side=self.tk.LEFT)

        # Inset Target Folder Row
        dest_div = self.tk.Frame(feat_card, bg=COLOR_CARD_BORDER, height=1)
        dest_div.pack(fill=self.tk.X, pady=(10, 8))

        dest_row = self.tk.Frame(feat_card, bg=COLOR_CARD)
        dest_row.pack(fill=self.tk.X)

        lbl_dest_tag = self.tk.Label(dest_row, text="Install to:", font=("Segoe UI", 8, "bold"), fg=COLOR_TEXT_DIM, bg=COLOR_CARD)
        lbl_dest_tag.pack(side=self.tk.LEFT, padx=(0, 6))

        self.lbl_dest_path = self.tk.Label(
            dest_row,
            text=self._format_path_short(self.target_dir),
            font=("Consolas", 8),
            fg=COLOR_TEXT_MUTED,
            bg=COLOR_CARD
        )
        self.lbl_dest_path.pack(side=self.tk.LEFT, fill=self.tk.X, expand=True)

        btn_change = self.tk.Button(
            dest_row,
            text="Change...",
            font=("Segoe UI", 8),
            fg=COLOR_CYAN,
            bg=COLOR_CARD,
            activeforeground="#ffffff",
            activebackground=COLOR_CARD,
            relief=self.tk.FLAT,
            bd=0,
            cursor="hand2",
            command=self._choose_custom_folder
        )
        btn_change.pack(side=self.tk.RIGHT)

        # 4. Progress Section
        self.progress_frame = self.tk.Frame(self.container, bg=COLOR_BG)
        self.progress_frame.pack(fill=self.tk.X, pady=(0, 16))

        self.lbl_status = self.tk.Label(
            self.progress_frame,
            text="Ready to install",
            font=("Segoe UI", 8),
            fg=COLOR_TEXT_DIM,
            bg=COLOR_BG
        )
        self.lbl_status.pack(anchor="w", pady=(0, 4))

        style = self.ttk.Style()
        style.theme_use("default")
        style.configure(
            "Adobe.Horizontal.TProgressbar",
            background=COLOR_ACCENT,
            troughcolor=COLOR_CARD,
            borderwidth=0,
            thickness=4
        )
        self.progress_bar = self.ttk.Progressbar(
            self.progress_frame,
            style="Adobe.Horizontal.TProgressbar",
            mode="determinate"
        )
        self.progress_bar.pack(fill=self.tk.X)
        self.progress_bar["value"] = 0

        # 5. Bottom Action Bar
        self.action_bar = self.tk.Frame(self.container, bg=COLOR_BG)
        self.action_bar.pack(fill=self.tk.X, side=self.tk.BOTTOM)

        self.btn_cancel = self.tk.Button(
            self.action_bar,
            text="Cancel",
            font=("Segoe UI", 9),
            fg=COLOR_TEXT_MUTED,
            bg=COLOR_CARD,
            activeforeground=COLOR_TEXT,
            activebackground=COLOR_CARD_BORDER,
            relief=self.tk.FLAT,
            padx=16,
            pady=6,
            cursor="hand2",
            command=self.root.destroy
        )
        self.btn_cancel.pack(side=self.tk.LEFT)

        self.btn_install = self.tk.Button(
            self.action_bar,
            text="  Install for Premiere Pro  ",
            font=("Segoe UI", 9, "bold"),
            fg="#000000",
            bg=COLOR_ACCENT,
            activeforeground="#000000",
            activebackground=COLOR_ACCENT_HOVER,
            relief=self.tk.FLAT,
            padx=20,
            pady=7,
            cursor="hand2",
            command=self._start_installation
        )
        self.btn_install.pack(side=self.tk.RIGHT)

    def _format_path_short(self, path: Optional[Path]) -> str:
        if not path:
            return "Standard User Directory"
        p_str = str(path)
        if len(p_str) > 48:
            return p_str[:22] + "..." + p_str[-22:]
        return p_str

    def _choose_custom_folder(self):
        folder = self.filedialog.askdirectory(title="Select Adobe CEP Extensions Directory")
        if folder:
            self.target_dir = Path(folder)
            self.is_custom_location = True
            self.lbl_dest_path.config(text=self._format_path_short(self.target_dir))

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
                    self.lbl_detect_dot.config(fg=COLOR_SUCCESS)
                    self.lbl_detect_text.config(text=f"{len(names)} Adobe app(s) detected")
                    self.lbl_detect_ver.config(text="Ready to install")
                    if running:
                        self.lbl_detect_warn.config(text="⚠️ Adobe apps are running. Please restart them after setup to load the extension.")
                        self.lbl_detect_warn.pack(anchor="w", pady=(4, 0))
                else:
                    self.lbl_detect_dot.config(fg=COLOR_CYAN)
                    self.lbl_detect_text.config(text="Adobe apps not running")
                    self.lbl_detect_ver.config(text="Standard paths ready")

            self.root.after(0, update_ui)
        except Exception:
            pass

    def _start_installation(self):
        if self.is_completed:
            self.root.destroy()
            return
        if self.is_installing:
            return

        self.is_installing = True
        self.btn_install.config(state=self.tk.DISABLED, text="Installing...")
        self.btn_cancel.config(state=self.tk.DISABLED)

        threading.Thread(target=self._installation_thread, daemon=True).start()

    def _update_progress(self, percent: int, msg: str):
        def _apply():
            if self.root.winfo_exists():
                self.progress_bar["value"] = percent
                self.lbl_status.config(text=msg)
        self.root.after(0, _apply)

    def _installation_thread(self):
        try:
            custom_dir = self.target_dir if self.is_custom_location else None
            self._update_progress(15, "Setting up background engine...")

            installer = PremiereExtensionInstaller(
                discovered=self.discovered_adobe_apps,
                custom_cep_dir=custom_dir,
            )

            # 1. Background Engine
            installer.install_desktop_service()
            self._update_progress(45, "Deploying CEP panel & configuring CSXS debug mode...")

            # 2. Deploy CEP Panel & CSXS Registry
            installer.install_adobe_creative_cloud()

            # 3. Custom directory deployment if requested
            if custom_dir:
                self._update_progress(80, "Configuring custom CEP directory...")
                installer.deploy_to_custom_cep_dir(custom_dir)

            # 4. Universal Timeline Sidecars
            installer.configure_fcpxml_drag_and_drop()
            self._update_progress(100, "✓ Installed successfully!")

            time.sleep(0.3)
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
        self.btn_install.config(state=self.tk.NORMAL, text="Done", bg=COLOR_SUCCESS, fg="#ffffff")
        self.btn_cancel.pack_forget()

        # Replace features card with success instructions
        for child in self.container.winfo_children():
            if child not in (self.progress_frame, self.action_bar):
                child.destroy()

        success_box = self.tk.Frame(
            self.container,
            bg=COLOR_SUCCESS_BG,
            highlightbackground=COLOR_SUCCESS_BORDER,
            highlightthickness=1,
            padx=16,
            pady=16
        )
        success_box.pack(fill=self.tk.BOTH, expand=True, pady=(8, 16))

        lbl_check = self.tk.Label(success_box, text="✓  Adobe Extension Setup Complete", font=("Segoe UI", 12, "bold"), fg=COLOR_SUCCESS, bg=COLOR_SUCCESS_BG)
        lbl_check.pack(anchor="w", pady=(0, 10))

        guide = (
            "How to launch Xdrop inside Premiere Pro, AE & Audition:\n\n"
            "• Top Menu:\n"
            "  Window → Extensions → Xdrop\n\n"
            "• Dock the panel anywhere next to Project Bins or Timeline.\n\n"
            "Background service is active on http://127.0.0.1:8484"
        )
        lbl_guide = self.tk.Label(success_box, text=guide, font=("Segoe UI", 9), fg=COLOR_TEXT, bg=COLOR_SUCCESS_BG, justify=self.tk.LEFT)
        lbl_guide.pack(anchor="w", pady=(0, 14))

        premiere_app = next((a for a in self.discovered_adobe_apps if a.app_id == "premiere" and a.executable), None)
        if premiere_app and premiere_app.executable and premiere_app.executable.is_file():
            btn_launch = self.tk.Button(
                success_box,
                text="  Launch Premiere Pro  ",
                font=("Segoe UI", 9, "bold"),
                bg=COLOR_ACCENT,
                fg="#000000",
                activebackground=COLOR_ACCENT_HOVER,
                relief=self.tk.FLAT,
                cursor="hand2",
                command=lambda: subprocess.Popen([str(premiere_app.executable)], start_new_session=True)
            )
            btn_launch.pack(side=self.tk.LEFT)

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
    print(f"1. {BOLD}Open Panel:{RESET} Top Menu -> Window -> Extensions -> Xdrop")
    print(f"2. {BOLD}Automatic Bin & Timeline Insertion:{RESET} Downloads drop into 000_Xdrop Assets bin.")
    print(f"3. {BOLD}Background Service:{RESET} Listening on {CYAN}http://127.0.0.1:8484{RESET}\n")


def run_cli_installer(custom_dir: Optional[Path] = None):
    print_premiere_banner()
    print(f"System: {platform.system()} {platform.release()} ({platform.architecture()[0]})")
    print(f"Location: {BASE_DIR}")

    log_header("Phase 1: Scanning for Adobe Creative Cloud Applications Across All Drives")
    scanner = DeepAppScanner()
    all_apps = scanner.scan()
    adobe_apps = [a for a in all_apps if a.vendor.lower() == "adobe" or a.app_id in ("premiere", "aftereffects", "audition")]

    if adobe_apps:
        for app in adobe_apps:
            running_tag = f" {GREEN}(Currently Running){RESET}" if app.is_running else ""
            log_success(f"Found: {BOLD}{app.name}{RESET} - v{app.version}{running_tag}")
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

    force_cli = args.cli or args.silent
    if not force_cli:
        try:
            app = PremiereGuiInstaller(initial_custom_dir=custom_path)
            app.run()
            return
        except Exception as gui_err:
            print(f"[Notice] GUI could not be initialized ({gui_err}). Switching to CLI mode...")

    run_cli_installer(custom_dir=custom_path)


if __name__ == "__main__":
    main()
