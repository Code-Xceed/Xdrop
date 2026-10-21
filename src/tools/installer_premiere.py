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
8. Provides a minimal, studio-grade dark GUI with high-DPI awareness and automatic headless CLI fallback.
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


# --- High-DPI Windows Awareness --------------------------------------------------
def enable_high_dpi_awareness():
    """Enables per-monitor high-DPI awareness on Windows to prevent blurry OS bitmap stretching."""
    if sys.platform == "win32":
        try:
            import ctypes
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
            except Exception:
                try:
                    ctypes.windll.shcore.SetProcessDpiAwareness(1)
                except Exception:
                    ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def get_dpi_scale() -> float:
    """Returns the primary monitor DPI scale factor (1.0 = 100%, 1.25 = 125%, 1.5 = 150%, 2.0 = 200%)."""
    if sys.platform == "win32":
        try:
            import ctypes
            hdc = ctypes.windll.user32.GetDC(0)
            dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)  # 88 = LOGPIXELSX
            ctypes.windll.user32.ReleaseDC(0, hdc)
            return max(1.0, dpi / 96.0)
        except Exception:
            pass
    return 1.0


# --- Studio Monochromatic Palette (Matches Extension theme.css 1:1) ---------------
COLOR_BG = "#09090b"            # Void dark background (--bg-void)
COLOR_SURFACE = "#111216"       # Matte studio card surface (--bg-primary)
COLOR_SURFACE_INSET = "#0c0d10" # Inset container for paths
COLOR_BORDER = "#1f2229"        # 1px studio boundary (--border-default)
COLOR_BORDER_SUBTLE = "#17181f" # Internal row dividers

COLOR_TEXT_PRIMARY = "#f4f4f5"  # High-contrast crisp white (--text-primary)
COLOR_TEXT_SECONDARY = "#a1a1aa"# Muted zinc for body/labels (--text-secondary)
COLOR_TEXT_MUTED = "#71717a"    # Dim text for meta/headers (--text-muted)
COLOR_TEXT_DIM = "#52525b"      # Footnote / inactive (--text-disabled)

# High-contrast studio action button (Matches extension style)
COLOR_BTN_PRIMARY_BG = "#f4f4f5"
COLOR_BTN_PRIMARY_FG = "#09090b"
COLOR_BTN_PRIMARY_HOVER = "#e4e4e7"
COLOR_BTN_PRIMARY_ACTIVE = "#d4d4d8"

# Minimal dark secondary button
COLOR_BTN_SEC_BG = "#16181f"
COLOR_BTN_SEC_BORDER = "#272a34"
COLOR_BTN_SEC_FG = "#d4d4d8"
COLOR_BTN_SEC_HOVER_BG = "#20232c"
COLOR_BTN_SEC_HOVER_FG = "#ffffff"

# Discrete Status Tokens (Subtle, never neon or jarring)
COLOR_STATUS_OK = "#34d399"       # Muted emerald
COLOR_STATUS_OK_BG = "#0d2218"    # Soft green badge
COLOR_STATUS_OK_BORDER = "#1b4d32"
COLOR_STATUS_NOTE = "#94a3b8"     # Calm slate note


def load_app_icon_image(
    logical_size: int = 34,
    scale: float = 1.0,
    size: Optional[int] = None,
    target_size: Optional[int] = None,
) -> Optional[object]:
    """Safely loads a crystal-sharp, high-DPI app icon matching the display scale."""
    import tkinter as tk

    eff_logical = target_size or size or logical_size
    target_px = int(round(eff_logical * scale))

    # Priority 1: PIL downsample with LANCZOS from master logo.png for pixel-perfect sharpness
    try:
        from PIL import Image, ImageTk

        master_candidates = [
            SCRIPT_DIR / "assets" / "logo.png",
            REPO_ROOT / "src" / "assets" / "logo.png",
            REPO_ROOT / "src" / "tools" / "assets" / "logo.png",
        ]
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            meipass = Path(sys._MEIPASS)
            master_candidates = [
                meipass / "src" / "assets" / "logo.png",
                meipass / "src" / "tools" / "assets" / "logo.png",
                meipass / "assets" / "logo.png",
            ] + master_candidates

        for m in master_candidates:
            if m.is_file():
                with Image.open(m) as img:
                    img_rgba = img.convert("RGBA")
                    resized = img_rgba.resize((target_px, target_px), Image.Resampling.LANCZOS)
                    return ImageTk.PhotoImage(resized)
    except Exception:
        pass

    # Priority 2: Pre-rendered multi-resolution icons in src/tools/assets/
    available_sizes = [24, 32, 40, 48, 64, 72, 96, 128]
    best_size = min(available_sizes, key=lambda s: abs(s - target_px))
    candidates = [
        SCRIPT_DIR / "assets" / f"logo-{best_size}.png",
        REPO_ROOT / "src" / "tools" / "assets" / f"logo-{best_size}.png",
        SCRIPT_DIR / "assets" / "logo-40.png",
        REPO_ROOT / "src" / "tools" / "assets" / "logo-40.png",
    ]
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        meipass = Path(sys._MEIPASS)
        candidates = [
            meipass / "src" / "tools" / "assets" / f"logo-{best_size}.png",
            meipass / "src" / "tools" / "assets" / "logo-40.png",
        ] + candidates

    for c in candidates:
        if c.is_file():
            try:
                photo = tk.PhotoImage(file=str(c))
                w = photo.width()
                if w > target_px * 1.5:
                    factor = max(1, round(w / target_px))
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
# Minimal, Usable, High-DPI Studio GUI
# ==============================================================================

class PremiereGuiInstaller:
    """Minimal, elegant studio installer tailored specifically for Adobe Creative Cloud."""

    def __init__(self, initial_custom_dir: Optional[Path] = None):
        enable_high_dpi_awareness()
        self.scale = get_dpi_scale()

        import tkinter as tk
        from tkinter import ttk, filedialog

        self.tk = tk
        self.ttk = ttk
        self.filedialog = filedialog

        self.root = tk.Tk()
        self.root.title("Xdrop Setup — Adobe Premiere Pro")
        self.root.configure(bg=COLOR_BG)

        # Scale window geometry to match monitor DPI perfectly
        base_w, base_h = 480, 360
        win_w = int(round(base_w * self.scale))
        win_h = int(round(base_h * self.scale))
        self.root.geometry(f"{win_w}x{win_h}")
        self.root.minsize(win_w, win_h)
        self.root.maxsize(win_w, win_h)
        self.root.resizable(False, False)

        # Windows taskbar AppUserModelID
        if sys.platform == "win32":
            try:
                import ctypes
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("com.xdrop.installer.premiere.1.0")
            except Exception:
                pass

        self._load_app_icons()
        self._center_window(win_w, win_h)

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

        self._logo_photo = load_app_icon_image(logical_size=34, scale=self.scale)

    def _center_window(self, w: int, h: int):
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = max(0, (sw // 2) - (w // 2))
        y = max(0, (sh // 2) - (h // 2))
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def _build_ui(self):
        pad_x = int(round(24 * self.scale))
        pad_y = int(round(20 * self.scale))
        self.container = self.tk.Frame(self.root, bg=COLOR_BG, padx=pad_x, pady=pad_y)
        self.container.pack(fill=self.tk.BOTH, expand=True)

        # 1. Header Row (Crisp icon, brand, studio pill, subtitle)
        header = self.tk.Frame(self.container, bg=COLOR_BG)
        header.pack(fill=self.tk.X, pady=(0, int(round(14 * self.scale))))

        if self._logo_photo:
            lbl_logo = self.tk.Label(header, image=self._logo_photo, bg=COLOR_BG)
            lbl_logo.pack(side=self.tk.LEFT, padx=(0, int(round(12 * self.scale))))

        title_col = self.tk.Frame(header, bg=COLOR_BG)
        title_col.pack(side=self.tk.LEFT, fill=self.tk.Y)

        title_row = self.tk.Frame(title_col, bg=COLOR_BG)
        title_row.pack(anchor="w")

        lbl_title = self.tk.Label(
            title_row,
            text="Xdrop",
            font=("Segoe UI", 15, "bold"),
            fg=COLOR_TEXT_PRIMARY,
            bg=COLOR_BG,
        )
        lbl_title.pack(side=self.tk.LEFT)

        # Studio Pill Badge (Subtle dark badge matching extension)
        lbl_pill = self.tk.Label(
            title_row,
            text=" PREMIERE PRO ",
            font=("Segoe UI", 8, "bold"),
            fg=COLOR_TEXT_SECONDARY,
            bg="#181a20",
            highlightbackground=COLOR_BORDER,
            highlightthickness=1,
            padx=int(round(7 * self.scale)),
            pady=int(round(2 * self.scale)),
        )
        lbl_pill.pack(side=self.tk.LEFT, padx=(int(round(8 * self.scale)), 0))

        lbl_sub = self.tk.Label(
            title_col,
            text="Native Media Importer & Background Service",
            font=("Segoe UI", 9),
            fg=COLOR_TEXT_MUTED,
            bg=COLOR_BG,
        )
        lbl_sub.pack(anchor="w", pady=(int(round(2 * self.scale)), 0))

        # 2. Main Studio Card (Single clean panel, 1px studio border)
        self.studio_card = self.tk.Frame(
            self.container,
            bg=COLOR_SURFACE,
            highlightbackground=COLOR_BORDER,
            highlightthickness=1,
            padx=int(round(16 * self.scale)),
            pady=int(round(14 * self.scale)),
        )
        self.studio_card.pack(fill=self.tk.X, pady=(0, int(round(16 * self.scale))))

        # Section A: Target Host Application
        sec_a_lbl = self.tk.Label(
            self.studio_card,
            text="TARGET APPLICATION",
            font=("Segoe UI", 8, "bold"),
            fg=COLOR_TEXT_MUTED,
            bg=COLOR_SURFACE,
        )
        sec_a_lbl.pack(anchor="w")

        row_target = self.tk.Frame(self.studio_card, bg=COLOR_SURFACE)
        row_target.pack(fill=self.tk.X, pady=(int(round(4 * self.scale)), 0))

        self.lbl_target_name = self.tk.Label(
            row_target,
            text="Scanning for Adobe applications...",
            font=("Segoe UI", 9, "bold"),
            fg=COLOR_TEXT_PRIMARY,
            bg=COLOR_SURFACE,
        )
        self.lbl_target_name.pack(side=self.tk.LEFT)

        self.lbl_target_status = self.tk.Label(
            row_target,
            text="Scanning",
            font=("Segoe UI", 8, "bold"),
            fg=COLOR_TEXT_MUTED,
            bg="#181a20",
            highlightbackground=COLOR_BORDER,
            highlightthickness=1,
            padx=int(round(6 * self.scale)),
            pady=int(round(1 * self.scale)),
        )
        self.lbl_target_status.pack(side=self.tk.RIGHT)

        self.lbl_target_running = self.tk.Label(
            self.studio_card,
            text="",
            font=("Segoe UI", 8),
            fg=COLOR_STATUS_NOTE,
            bg=COLOR_SURFACE,
        )

        # Divider 1
        div_1 = self.tk.Frame(self.studio_card, bg=COLOR_BORDER_SUBTLE, height=1)
        div_1.pack(fill=self.tk.X, pady=int(round(12 * self.scale)))

        # Section B: Installation Directory
        sec_b_lbl = self.tk.Label(
            self.studio_card,
            text="INSTALLATION DIRECTORY",
            font=("Segoe UI", 8, "bold"),
            fg=COLOR_TEXT_MUTED,
            bg=COLOR_SURFACE,
        )
        sec_b_lbl.pack(anchor="w")

        path_box = self.tk.Frame(
            self.studio_card,
            bg=COLOR_SURFACE_INSET,
            highlightbackground=COLOR_BORDER,
            highlightthickness=1,
            padx=int(round(12 * self.scale)),
            pady=int(round(7 * self.scale)),
        )
        path_box.pack(fill=self.tk.X, pady=(int(round(5 * self.scale)), 0))

        self.lbl_dest_path = self.tk.Label(
            path_box,
            text=self._format_path_short(self.target_dir),
            font=("Consolas", 8),
            fg=COLOR_TEXT_SECONDARY,
            bg=COLOR_SURFACE_INSET,
            anchor="w",
            justify=self.tk.LEFT,
        )
        self.lbl_dest_path.pack(side=self.tk.LEFT, fill=self.tk.X, expand=True, anchor="w")

        btn_change = self.tk.Button(
            path_box,
            text="Browse...",
            font=("Segoe UI", 8),
            fg=COLOR_TEXT_SECONDARY,
            bg=COLOR_SURFACE_INSET,
            activeforeground=COLOR_TEXT_PRIMARY,
            activebackground=COLOR_SURFACE_INSET,
            relief=self.tk.FLAT,
            bd=0,
            cursor="hand2",
            padx=int(round(4 * self.scale)),
            command=self._choose_custom_folder,
        )
        btn_change.pack(side=self.tk.RIGHT, padx=(int(round(8 * self.scale)), 0))
        btn_change.bind("<Enter>", lambda e: btn_change.config(fg=COLOR_TEXT_PRIMARY))
        btn_change.bind("<Leave>", lambda e: btn_change.config(fg=COLOR_TEXT_SECONDARY))

        # 3. Progress Section
        self.progress_frame = self.tk.Frame(self.container, bg=COLOR_BG)
        self.progress_frame.pack(fill=self.tk.X, pady=(0, int(round(14 * self.scale))))

        self.lbl_status = self.tk.Label(
            self.progress_frame,
            text="Ready to install",
            font=("Segoe UI", 8),
            fg=COLOR_TEXT_MUTED,
            bg=COLOR_BG,
        )
        self.lbl_status.pack(anchor="w", pady=(0, int(round(4 * self.scale))))

        style = self.ttk.Style()
        style.theme_use("default")
        style.configure(
            "Studio.Horizontal.TProgressbar",
            background=COLOR_BTN_PRIMARY_BG,
            troughcolor=COLOR_SURFACE,
            borderwidth=0,
            thickness=int(round(3 * self.scale)),
        )
        self.progress_bar = self.ttk.Progressbar(
            self.progress_frame,
            style="Studio.Horizontal.TProgressbar",
            mode="determinate",
        )
        self.progress_bar.pack(fill=self.tk.X)
        self.progress_bar["value"] = 0

        # 4. Action Bar (Cancel on left, high-contrast studio install on right)
        self.action_bar = self.tk.Frame(self.container, bg=COLOR_BG)
        self.action_bar.pack(fill=self.tk.X, side=self.tk.BOTTOM)

        self.btn_cancel = self.tk.Button(
            self.action_bar,
            text="Cancel",
            font=("Segoe UI", 9),
            fg=COLOR_BTN_SEC_FG,
            bg=COLOR_BTN_SEC_BG,
            activeforeground=COLOR_BTN_SEC_HOVER_FG,
            activebackground=COLOR_BTN_SEC_HOVER_BG,
            relief=self.tk.FLAT,
            bd=0,
            highlightbackground=COLOR_BTN_SEC_BORDER,
            highlightthickness=1,
            padx=int(round(18 * self.scale)),
            pady=int(round(7 * self.scale)),
            cursor="hand2",
            command=self.root.destroy,
        )
        self.btn_cancel.pack(side=self.tk.LEFT)
        self.btn_cancel.bind("<Enter>", lambda e: self.btn_cancel.config(bg=COLOR_BTN_SEC_HOVER_BG, fg=COLOR_BTN_SEC_HOVER_FG))
        self.btn_cancel.bind("<Leave>", lambda e: self.btn_cancel.config(bg=COLOR_BTN_SEC_BG, fg=COLOR_BTN_SEC_FG))

        self.btn_install = self.tk.Button(
            self.action_bar,
            text="  Install for Premiere Pro  ",
            font=("Segoe UI", 9, "bold"),
            fg=COLOR_BTN_PRIMARY_FG,
            bg=COLOR_BTN_PRIMARY_BG,
            activeforeground=COLOR_BTN_PRIMARY_FG,
            activebackground=COLOR_BTN_PRIMARY_HOVER,
            relief=self.tk.FLAT,
            bd=0,
            padx=int(round(22 * self.scale)),
            pady=int(round(7 * self.scale)),
            cursor="hand2",
            command=self._start_installation,
        )
        self.btn_install.pack(side=self.tk.RIGHT)
        self.btn_install.bind("<Enter>", lambda e: self.btn_install.config(bg=COLOR_BTN_PRIMARY_HOVER) if not self.is_installing else None)
        self.btn_install.bind("<Leave>", lambda e: self.btn_install.config(bg=COLOR_BTN_PRIMARY_BG) if not self.is_installing else None)

    def _format_path_short(self, path: Optional[Path]) -> str:
        if not path:
            return "Standard User Directory"
        p_str = str(path)
        if len(p_str) > 52:
            return p_str[:24] + "..." + p_str[-24:]
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
                    self.lbl_target_name.config(text=", ".join(names[:2]) + ("..." if len(names) > 2 else ""))
                    self.lbl_target_status.config(
                        text="Detected",
                        fg=COLOR_STATUS_OK,
                        bg=COLOR_STATUS_OK_BG,
                        highlightbackground=COLOR_STATUS_OK_BORDER,
                    )
                    if running:
                        self.lbl_target_running.config(
                            text="Note: Adobe applications are running. Restart them after setup to load the extension."
                        )
                        self.lbl_target_running.pack(anchor="w", pady=(int(round(4 * self.scale)), 0))
                else:
                    self.lbl_target_name.config(text="Adobe Premiere Pro (Standard Paths)")
                    self.lbl_target_status.config(
                        text="Ready",
                        fg=COLOR_TEXT_SECONDARY,
                        bg="#181a20",
                        highlightbackground=COLOR_BORDER,
                    )

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
        self.btn_install.config(
            state=self.tk.NORMAL,
            text="Done",
            bg=COLOR_BTN_PRIMARY_BG,
            fg=COLOR_BTN_PRIMARY_FG,
        )
        self.btn_cancel.pack_forget()

        # Replace studio card with completion card
        for child in self.container.winfo_children():
            if child not in (self.progress_frame, self.action_bar):
                child.destroy()

        success_box = self.tk.Frame(
            self.container,
            bg=COLOR_SURFACE,
            highlightbackground=COLOR_BORDER,
            highlightthickness=1,
            padx=int(round(18 * self.scale)),
            pady=int(round(18 * self.scale)),
        )
        success_box.pack(fill=self.tk.BOTH, expand=True, pady=(int(round(8 * self.scale)), int(round(16 * self.scale))))

        lbl_check = self.tk.Label(
            success_box,
            text="Extension Installed Successfully",
            font=("Segoe UI", 12, "bold"),
            fg=COLOR_TEXT_PRIMARY,
            bg=COLOR_SURFACE,
        )
        lbl_check.pack(anchor="w", pady=(0, int(round(10 * self.scale))))

        guide = (
            "How to access Xdrop in Premiere Pro, AE & Audition:\n\n"
            "1. Launch or restart Adobe Premiere Pro\n"
            "2. In the top menu, select:\n"
            "   Window  →  Extensions  →  Xdrop\n"
            "3. Dock the panel beside your Project Bins or Timeline\n\n"
            "Background service is active on http://127.0.0.1:8484"
        )
        lbl_guide = self.tk.Label(
            success_box,
            text=guide,
            font=("Segoe UI", 9),
            fg=COLOR_TEXT_SECONDARY,
            bg=COLOR_SURFACE,
            justify=self.tk.LEFT,
        )
        lbl_guide.pack(anchor="w", pady=(0, int(round(14 * self.scale))))

        premiere_app = next((a for a in self.discovered_adobe_apps if a.app_id == "premiere" and a.executable), None)
        if premiere_app and premiere_app.executable and premiere_app.executable.is_file():
            btn_launch = self.tk.Button(
                success_box,
                text="  Launch Premiere Pro  ",
                font=("Segoe UI", 9, "bold"),
                bg=COLOR_BTN_PRIMARY_BG,
                fg=COLOR_BTN_PRIMARY_FG,
                activebackground=COLOR_BTN_PRIMARY_HOVER,
                relief=self.tk.FLAT,
                bd=0,
                padx=int(round(16 * self.scale)),
                pady=int(round(6 * self.scale)),
                cursor="hand2",
                command=lambda: subprocess.Popen([str(premiere_app.executable)], start_new_session=True),
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
    enable_high_dpi_awareness()
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
            import traceback
            traceback.print_exc()
            if getattr(sys, "frozen", False):
                try:
                    import tkinter.messagebox as mb
                    mb.showerror("Xdrop Installer Error", f"Could not launch installer GUI:\n{gui_err}")
                except Exception:
                    pass
            print(f"[Notice] GUI could not be initialized ({gui_err}). Switching to CLI mode...")

    run_cli_installer(custom_dir=custom_path)


if __name__ == "__main__":
    main()
