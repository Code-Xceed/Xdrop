#!/usr/bin/env python3
"""
Xdrop DaVinci Resolve Native Extension Installer.

Minimal, usable, and professional installer for DaVinci Resolve (Free & Studio):
1. Deep-scans workstation drives, registry, and running processes.
2. Supports standard per-user (%APPDATA%), system-wide (%PROGRAMDATA%), and custom folder installations.
3. Purges legacy ResolveFetch scripts while strictly preserving third-party plugins (Snap Captions).
4. Deploys the DaVinci Resolve Native Lua Extension (Xdrop.lua + Starter Bin.drb) into Scripts/Comp/.
5. Deploys the DaVinci Resolve Desktop Utility script (Xdrop.py) into Scripts/Utility/.
6. Deploys the DaVinci Resolve Studio Workflow Integration docked panel (WorkflowIntegration.node).
7. Installs and silently starts the Xdrop zero-flicker headless background engine (0 CMD windows).
8. Provides a minimal, studio-grade dark GUI with automatic headless CLI fallback.
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

# --- Minimal Design Tokens (Obsidian / Resolve Studio Theme) --------------------
COLOR_BG = "#0c0d12"             # Deep Obsidian Black
COLOR_CARD = "#141620"           # Inset surface
COLOR_CARD_BORDER = "#222638"    # Subtle 1px boundary
COLOR_ACCENT = "#f59e0b"         # Resolve Amber / Gold
COLOR_ACCENT_HOVER = "#d97706"   # Deep Amber on press
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
# Minimal, Usable, Professional GUI
# ==============================================================================

class ResolveGuiInstaller:
    """Minimal, elegant studio installer tailored specifically for DaVinci Resolve."""

    def __init__(self, initial_custom_dir: Optional[Path] = None):
        import tkinter as tk
        from tkinter import ttk, filedialog

        self.tk = tk
        self.ttk = ttk
        self.filedialog = filedialog

        self.root = tk.Tk()
        self.root.title("Xdrop Setup — DaVinci Resolve")
        self.root.geometry("520x460")
        self.root.minsize(520, 460)
        self.root.maxsize(520, 460)
        self.root.resizable(False, False)
        self.root.configure(bg=COLOR_BG)

        # Windows taskbar AppUserModelID
        if sys.platform == "win32":
            try:
                import ctypes
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("com.xdrop.installer.resolve.1.0")
            except Exception:
                pass

        self._load_app_icons()
        self._center_window()

        self.default_paths = get_default_resolve_paths()
        self.target_dir = Path(initial_custom_dir).resolve() if initial_custom_dir else self.default_paths.get("user_comp")
        self.is_custom_location = initial_custom_dir is not None

        self.discovered_resolve_apps: List[DiscoveredApp] = []
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
            text=" DaVinci Resolve ",
            font=("Segoe UI", 9, "bold"),
            fg=COLOR_ACCENT,
            bg="#1d1e28",
            padx=6,
            pady=2
        )
        lbl_pill.pack(side=self.tk.LEFT, padx=(8, 0))

        lbl_sub = self.tk.Label(
            title_col,
            text="High-performance media importer for DaVinci Resolve Free & Studio",
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
            text="Scanning workstation for DaVinci Resolve...",
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
            ("✓", "Native Studio UI script (Workspace → Scripts → Comp → Xdrop)"),
            ("✓", "Pre-configured Starter Bins & Studio Workflow Integration"),
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
            "Resolve.Horizontal.TProgressbar",
            background=COLOR_ACCENT,
            troughcolor=COLOR_CARD,
            borderwidth=0,
            thickness=4
        )
        self.progress_bar = self.ttk.Progressbar(
            self.progress_frame,
            style="Resolve.Horizontal.TProgressbar",
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
            text="  Install for DaVinci Resolve  ",
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
        folder = self.filedialog.askdirectory(title="Select DaVinci Resolve or Fusion Scripts Directory")
        if folder:
            self.target_dir = Path(folder)
            self.is_custom_location = True
            self.lbl_dest_path.config(text=self._format_path_short(self.target_dir))

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
                    self.lbl_detect_dot.config(fg=COLOR_SUCCESS)
                    self.lbl_detect_text.config(text=f"{app.name} detected")
                    self.lbl_detect_ver.config(text=f"v{app.version}")
                    if app.is_running:
                        self.lbl_detect_warn.config(text="⚠️ Resolve is running. Please restart it after setup to load extensions.")
                        self.lbl_detect_warn.pack(anchor="w", pady=(4, 0))
                else:
                    self.lbl_detect_dot.config(fg=COLOR_CYAN)
                    self.lbl_detect_text.config(text="DaVinci Resolve not running")
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

            installer = ResolveExtensionInstaller(
                discovered=self.discovered_resolve_apps,
                custom_scripts_dir=custom_dir,
            )

            # 1. Background Engine
            installer.install_desktop_service()
            self._update_progress(40, "Cleaning duplicate legacy scripts...")

            # 2. Cleanup legacy duplicates (preserves Snap Captions)
            installer.clean_davinci_resolve_scripts()
            self._update_progress(70, "Deploying Xdrop.lua and Starter Bin...")

            # 3. Resolve Native Comp script & Workflow Integration
            installer.install_davinci_resolve()

            # 4. Custom directory deployment if requested
            if custom_dir:
                self._update_progress(85, "Configuring custom scripts folder...")
                installer.deploy_to_custom_scripts_dir(custom_dir)

            # 5. Universal Timeline Sidecars
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

        lbl_check = self.tk.Label(success_box, text="✓  DaVinci Resolve Setup Complete", font=("Segoe UI", 12, "bold"), fg=COLOR_SUCCESS, bg=COLOR_SUCCESS_BG)
        lbl_check.pack(anchor="w", pady=(0, 10))

        guide = (
            "How to launch Xdrop inside DaVinci Resolve:\n\n"
            "• Free & Studio:\n"
            "  Workspace → Scripts → Comp → Xdrop\n\n"
            "• Studio Docked Panel:\n"
            "  Workspace → Workflow Integrations → Xdrop\n\n"
            "Background service is active on http://127.0.0.1:8484"
        )
        lbl_guide = self.tk.Label(success_box, text=guide, font=("Segoe UI", 9), fg=COLOR_TEXT, bg=COLOR_SUCCESS_BG, justify=self.tk.LEFT)
        lbl_guide.pack(anchor="w", pady=(0, 14))

        resolve_exe = None
        if self.discovered_resolve_apps and self.discovered_resolve_apps[0].executable:
            resolve_exe = self.discovered_resolve_apps[0].executable

        if resolve_exe and resolve_exe.is_file():
            btn_launch = self.tk.Button(
                success_box,
                text="  Launch DaVinci Resolve  ",
                font=("Segoe UI", 9, "bold"),
                bg=COLOR_ACCENT,
                fg="#000000",
                activebackground=COLOR_ACCENT_HOVER,
                relief=self.tk.FLAT,
                cursor="hand2",
                command=lambda: subprocess.Popen([str(resolve_exe)], start_new_session=True)
            )
            btn_launch.pack(side=self.tk.LEFT)

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
    print(f"1. {BOLD}Free & Studio:{RESET} Top Menu -> Workspace -> Scripts -> Comp -> Xdrop")
    print(f"2. {BOLD}Studio Workflow Integration:{RESET} Top Menu -> Workspace -> Workflow Integrations -> Xdrop")
    print(f"3. {BOLD}Background Service:{RESET} Listening on {CYAN}http://127.0.0.1:8484{RESET}\n")


def run_cli_installer(custom_dir: Optional[Path] = None):
    print_resolve_banner()
    print(f"System: {platform.system()} {platform.release()} ({platform.architecture()[0]})")
    print(f"Location: {BASE_DIR}")

    log_header("Phase 1: Scanning for DaVinci Resolve Installations Across All Drives")
    scanner = DeepAppScanner()
    all_apps = scanner.scan()
    resolve_apps = [a for a in all_apps if a.app_id == "resolve"]

    if resolve_apps:
        for app in resolve_apps:
            running_tag = f" {GREEN}(Currently Running){RESET}" if app.is_running else ""
            log_success(f"Found: {BOLD}{app.name}{RESET} - v{app.version}{running_tag}")
    else:
        log_info("DaVinci Resolve not detected in standard locations (installing to standard script paths).")

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

    force_cli = args.cli or args.silent
    if not force_cli:
        try:
            app = ResolveGuiInstaller(initial_custom_dir=custom_path)
            app.run()
            return
        except Exception as gui_err:
            print(f"[Notice] GUI could not be initialized ({gui_err}). Switching to CLI mode...")

    run_cli_installer(custom_dir=custom_path)


if __name__ == "__main__":
    main()
