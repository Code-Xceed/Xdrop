#!/usr/bin/env python3
"""
Xdrop Unified Modern GUI Installer.

Graphical User Interface (GUI) installer for video editors:
1. Deep-scans workstation for DaVinci Resolve (Free/Studio) and Adobe Creative Cloud.
2. 1-Click GUI deployment of native plugins:
   - DaVinci Resolve: Scripts/Comp/Xdrop.lua, Starter Bin.drb, Workflow Integration.
   - Adobe Premiere Pro, After Effects, Audition: CEP com.xdrop.panel + PlayerDebugMode Registry.
   - Zero-Flicker Headless Engine: Configures on-demand startup & zero-trace auto-shutdown.
3. 100% GUI — zero black command prompt windows.
"""

from __future__ import annotations

import os
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from typing import List, Optional

# Ensure repository root is on sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent if SCRIPT_DIR.name == "tools" and SCRIPT_DIR.parent.name != "src" else SCRIPT_DIR.parent.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

try:
    from tools.installer import DeepAppScanner, DiscoveredApp, ExtensionInstaller, find_source_dir
except ImportError:
    try:
        from src.tools.installer import DeepAppScanner, DiscoveredApp, ExtensionInstaller, find_source_dir
    except ImportError:
        from installer import DeepAppScanner, DiscoveredApp, ExtensionInstaller, find_source_dir

# --- Design Tokens (Zinc / Electric Cyan) -------------------------------------
COLOR_BG = "#09090b"           # Dark zinc background
COLOR_CARD = "#141418"         # Inset card background
COLOR_CARD_BORDER = "#27272a"  # Border gray
COLOR_PRIMARY = "#00e5ff"      # Electric Cyan
COLOR_PRIMARY_HOVER = "#38bdf8"
COLOR_PRIMARY_ACTIVE = "#0284c7"
COLOR_TEXT = "#fafafa"         # Crisp white
COLOR_TEXT_MUTED = "#a1a1aa"   # Muted body text
COLOR_TEXT_DIM = "#71717a"     # Darker label text
COLOR_SUCCESS = "#22c55e"      # Green accent
COLOR_SUCCESS_BG = "#13231b"   # Soft green container


class XdropGuiInstaller(tk.Tk):
    """Modern dark-themed GUI installer for Xdrop across video editors."""

    def __init__(self):
        super().__init__()
        self.title("Xdrop Setup — Universal Media Importer")
        self.geometry("620x720")
        self.minsize(580, 680)
        self.configure(bg=COLOR_BG)

        # Center on screen
        self._center_window()

        # State variables
        self.install_resolve_var = tk.BooleanVar(value=True)
        self.install_adobe_var = tk.BooleanVar(value=True)
        self.install_engine_var = tk.BooleanVar(value=True)

        self.discovered_apps: List[DiscoveredApp] = []
        self.resolve_detected_text = "Scanning workstation..."
        self.adobe_detected_text = "Scanning workstation..."

        self.is_installing = False
        self.is_completed = False

        # Build interface
        self._build_header()
        self._build_scan_section()
        self._build_progress_section()
        self._build_actions()

        # Start asynchronous deep scan
        threading.Thread(target=self._run_initial_scan, daemon=True).start()

    def _center_window(self):
        self.update_idletasks()
        w = 620
        h = 720
        x = (self.winfo_screenwidth() // 2) - (w // 2)
        y = (self.winfo_screenheight() // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build_header(self):
        header_frame = tk.Frame(self, bg=COLOR_BG, pady=18, padx=28)
        header_frame.pack(fill=tk.X)

        # Branding Row
        title_row = tk.Frame(header_frame, bg=COLOR_BG)
        title_row.pack(anchor="w")

        lbl_x = tk.Label(title_row, text="X", font=("Segoe UI", 26, "bold"), fg=COLOR_PRIMARY, bg=COLOR_BG)
        lbl_x.pack(side=tk.LEFT)

        lbl_drop = tk.Label(title_row, text="drop", font=("Segoe UI", 26, "bold"), fg=COLOR_TEXT, bg=COLOR_BG)
        lbl_drop.pack(side=tk.LEFT)

        lbl_setup = tk.Label(title_row, text="  SETUP", font=("Segoe UI", 12, "bold"), fg=COLOR_TEXT_DIM, bg=COLOR_BG)
        lbl_setup.pack(side=tk.LEFT, pady=(8, 0))

        # Subtitle
        lbl_sub = tk.Label(
            header_frame,
            text="Universal Media Importer • Native Plugins & Zero-Trace Headless Engine",
            font=("Segoe UI", 10),
            fg=COLOR_TEXT_MUTED,
            bg=COLOR_BG
        )
        lbl_sub.pack(anchor="w", pady=(4, 0))

        # Divider
        div = tk.Frame(self, bg=COLOR_CARD_BORDER, height=1)
        div.pack(fill=tk.X, padx=28)

    def _build_scan_section(self):
        self.content_frame = tk.Frame(self, bg=COLOR_BG, padx=28, pady=16)
        self.content_frame.pack(fill=tk.BOTH, expand=True)

        lbl_section = tk.Label(
            self.content_frame,
            text="TARGET VIDEO EDITORS & COMPONENTS",
            font=("Segoe UI", 9, "bold"),
            fg=COLOR_PRIMARY,
            bg=COLOR_BG
        )
        lbl_section.pack(anchor="w", pady=(0, 10))

        # 1. DaVinci Resolve Card
        self.resolve_card = tk.Frame(self.content_frame, bg=COLOR_CARD, highlightbackground=COLOR_CARD_BORDER, highlightthickness=1, padx=14, pady=12)
        self.resolve_card.pack(fill=tk.X, pady=(0, 10))

        resolve_top = tk.Frame(self.resolve_card, bg=COLOR_CARD)
        resolve_top.pack(fill=tk.X)

        cb_resolve = tk.Checkbutton(
            resolve_top,
            text=" DaVinci Resolve (Free & Studio)",
            variable=self.install_resolve_var,
            font=("Segoe UI", 11, "bold"),
            fg=COLOR_TEXT,
            bg=COLOR_CARD,
            activebackground=COLOR_CARD,
            activeforeground=COLOR_PRIMARY,
            selectcolor=COLOR_BG,
            relief=tk.FLAT
        )
        cb_resolve.pack(side=tk.LEFT)

        self.resolve_badge = tk.Label(resolve_top, text="● Checking...", font=("Segoe UI", 9, "bold"), fg=COLOR_PRIMARY, bg=COLOR_CARD)
        self.resolve_badge.pack(side=tk.RIGHT)

        lbl_resolve_desc = tk.Label(
            self.resolve_card,
            text="Deploys native Fusion UI script (Xdrop.lua), Starter Bin (.drb), and Studio Workflow Integration.\nInstalls to: %APPDATA%\\Blackmagic Design\\DaVinci Resolve\\Support\\Fusion\\Scripts\\Comp\\",
            font=("Segoe UI", 9),
            fg=COLOR_TEXT_MUTED,
            bg=COLOR_CARD,
            justify=tk.LEFT
        )
        lbl_resolve_desc.pack(anchor="w", pady=(6, 0))

        # 2. Adobe Creative Cloud Card
        self.adobe_card = tk.Frame(self.content_frame, bg=COLOR_CARD, highlightbackground=COLOR_CARD_BORDER, highlightthickness=1, padx=14, pady=12)
        self.adobe_card.pack(fill=tk.X, pady=(0, 10))

        adobe_top = tk.Frame(self.adobe_card, bg=COLOR_CARD)
        adobe_top.pack(fill=tk.X)

        cb_adobe = tk.Checkbutton(
            adobe_top,
            text=" Adobe Premiere Pro, After Effects & Audition",
            variable=self.install_adobe_var,
            font=("Segoe UI", 11, "bold"),
            fg=COLOR_TEXT,
            bg=COLOR_CARD,
            activebackground=COLOR_CARD,
            activeforeground=COLOR_PRIMARY,
            selectcolor=COLOR_BG,
            relief=tk.FLAT
        )
        cb_adobe.pack(side=tk.LEFT)

        self.adobe_badge = tk.Label(adobe_top, text="● Checking...", font=("Segoe UI", 9, "bold"), fg=COLOR_PRIMARY, bg=COLOR_CARD)
        self.adobe_badge.pack(side=tk.RIGHT)

        lbl_adobe_desc = tk.Label(
            self.adobe_card,
            text="Deploys docked extension panel (com.xdrop.panel) and configures PlayerDebugMode in Windows Registry.\nInstalls to: %APPDATA%\\Adobe\\CEP\\extensions\\com.xdrop.panel\\",
            font=("Segoe UI", 9),
            fg=COLOR_TEXT_MUTED,
            bg=COLOR_CARD,
            justify=tk.LEFT
        )
        lbl_adobe_desc.pack(anchor="w", pady=(6, 0))

        # 3. Headless Engine & Lifecycle Card
        self.engine_card = tk.Frame(self.content_frame, bg=COLOR_CARD, highlightbackground=COLOR_CARD_BORDER, highlightthickness=1, padx=14, pady=12)
        self.engine_card.pack(fill=tk.X, pady=(0, 10))

        engine_top = tk.Frame(self.engine_card, bg=COLOR_CARD)
        engine_top.pack(fill=tk.X)

        cb_engine = tk.Checkbutton(
            engine_top,
            text=" Zero-Trace Headless Engine (Auto-Start / Auto-Stop)",
            variable=self.install_engine_var,
            font=("Segoe UI", 11, "bold"),
            fg=COLOR_TEXT,
            bg=COLOR_CARD,
            activebackground=COLOR_CARD,
            activeforeground=COLOR_PRIMARY,
            selectcolor=COLOR_BG,
            relief=tk.FLAT
        )
        cb_engine.pack(side=tk.LEFT)

        lbl_engine_badge = tk.Label(engine_top, text="● Integrated", font=("Segoe UI", 9, "bold"), fg=COLOR_SUCCESS, bg=COLOR_CARD)
        lbl_engine_badge.pack(side=tk.RIGHT)

        lbl_engine_desc = tk.Label(
            self.engine_card,
            text="Silently launches on demand when extensions open (0 CMD windows). Automatically shuts down\ncleanly and removes temporary traces when extensions close or idle.",
            font=("Segoe UI", 9),
            fg=COLOR_TEXT_MUTED,
            bg=COLOR_CARD,
            justify=tk.LEFT
        )
        lbl_engine_desc.pack(anchor="w", pady=(6, 0))

    def _build_progress_section(self):
        self.progress_frame = tk.Frame(self.content_frame, bg=COLOR_BG, pady=6)
        self.progress_frame.pack(fill=tk.X)

        self.status_label = tk.Label(
            self.progress_frame,
            text="Ready to configure workstation video editors.",
            font=("Segoe UI", 10),
            fg=COLOR_TEXT_MUTED,
            bg=COLOR_BG
        )
        self.status_label.pack(anchor="w", pady=(0, 6))

        # Custom-styled ttk progressbar
        style = ttk.Style()
        style.theme_use("default")
        style.configure(
            "Xdrop.Horizontal.TProgressbar",
            background=COLOR_PRIMARY,
            troughcolor=COLOR_CARD,
            borderwidth=0,
            thickness=6
        )
        self.progress_bar = ttk.Progressbar(self.progress_frame, style="Xdrop.Horizontal.TProgressbar", mode="determinate")
        self.progress_bar.pack(fill=tk.X)
        self.progress_bar["value"] = 0

    def _build_actions(self):
        action_frame = tk.Frame(self, bg=COLOR_BG, padx=28, pady=18)
        action_frame.pack(fill=tk.X, side=tk.BOTTOM)

        div = tk.Frame(action_frame, bg=COLOR_CARD_BORDER, height=1)
        div.pack(fill=tk.X, pady=(0, 16))

        btns_row = tk.Frame(action_frame, bg=COLOR_BG)
        btns_row.pack(fill=tk.X)

        self.btn_cancel = tk.Button(
            btns_row,
            text="Cancel",
            font=("Segoe UI", 10),
            fg=COLOR_TEXT_MUTED,
            bg=COLOR_CARD,
            activeforeground=COLOR_TEXT,
            activebackground=COLOR_CARD_BORDER,
            relief=tk.FLAT,
            padx=16,
            pady=8,
            cursor="hand2",
            command=self.destroy
        )
        self.btn_cancel.pack(side=tk.LEFT)

        self.btn_install = tk.Button(
            btns_row,
            text="  Install & Configure Selected  ",
            font=("Segoe UI", 11, "bold"),
            fg="#09090b",
            bg=COLOR_PRIMARY,
            activeforeground="#09090b",
            activebackground=COLOR_PRIMARY_HOVER,
            relief=tk.FLAT,
            padx=20,
            pady=8,
            cursor="hand2",
            command=self._start_installation
        )
        self.btn_install.pack(side=tk.RIGHT)

    def _run_initial_scan(self):
        """Asynchronously inspects workstation for editor installations."""
        try:
            scanner = DeepAppScanner()
            self.discovered_apps = scanner.scan()

            has_resolve = any(a.app_id == "resolve" for a in self.discovered_apps)
            has_adobe = any(a.app_id in ("premiere", "aftereffects", "audition") or a.vendor.lower() == "adobe" for a in self.discovered_apps)

            def update_badges():
                try:
                    if not self.winfo_exists():
                        return
                    if has_resolve:
                        self.resolve_badge.config(text="✓ Detected", fg=COLOR_SUCCESS)
                    else:
                        self.resolve_badge.config(text="Ready to Install", fg=COLOR_PRIMARY)

                    if has_adobe:
                        self.adobe_badge.config(text="✓ Detected", fg=COLOR_SUCCESS)
                    else:
                        self.adobe_badge.config(text="Ready to Install", fg=COLOR_PRIMARY)
                except Exception:
                    pass

            try:
                if self.winfo_exists():
                    self.after(0, update_badges)
            except Exception:
                pass
        except Exception as e:
            try:
                if self.winfo_exists():
                    self.after(0, lambda: self.status_label.config(text=f"Scan note: {e}"))
            except Exception:
                pass

    def _set_status(self, text: str, progress: int):
        def _update():
            self.status_label.config(text=text)
            self.progress_bar["value"] = progress
        self.after(0, _update)

    def _start_installation(self):
        if self.is_completed:
            self.destroy()
            return

        if self.is_installing:
            return

        if not self.install_resolve_var.get() and not self.install_adobe_var.get() and not self.install_engine_var.get():
            messagebox.showwarning("Selection Required", "Please select at least one component to configure.")
            return

        self.is_installing = True
        self.btn_install.config(state=tk.DISABLED, text="Installing...")
        self.btn_cancel.config(state=tk.DISABLED)

        threading.Thread(target=self._installation_worker, daemon=True).start()

    def _installation_worker(self):
        """Executes full extension and headless engine configuration in background."""
        try:
            installer = ExtensionInstaller(self.discovered_apps)

            # Step 1: Headless Engine Service
            if self.install_engine_var.get():
                self._set_status("Installing zero-trace background engine (%LOCALAPPDATA%\\Xdrop)...", 25)
                installer.install_desktop_service()
                time.sleep(0.4)

            # Step 2: DaVinci Resolve
            if self.install_resolve_var.get():
                self._set_status("Purging legacy scripts and deploying DaVinci Resolve extensions...", 55)
                installer.clean_davinci_resolve_scripts()
                installer.install_davinci_resolve()
                time.sleep(0.4)

            # Step 3: Adobe Creative Cloud
            if self.install_adobe_var.get():
                self._set_status("Deploying Adobe CEP extension & configuring Windows Registry...", 80)
                installer.install_adobe_creative_cloud()
                time.sleep(0.4)

            # Step 4: Finalize timeline sidecars
            self._set_status("Configuring universal drag-and-drop timeline handlers...", 95)
            installer.configure_fcpxml_drag_and_drop()
            time.sleep(0.3)

            # Finished!
            self._set_status("✓ All extensions configured successfully!", 100)
            self.after(0, self._render_completion_screen)
        except Exception as err:
            self._set_status(f"Installation error: {err}", 100)
            self.after(0, lambda: self.btn_install.config(state=tk.NORMAL, text="Retry Installation"))
            self.after(0, lambda: self.btn_cancel.config(state=tk.NORMAL))
            self.is_installing = False

    def _render_completion_screen(self):
        self.is_completed = True
        self.btn_install.config(state=tk.NORMAL, text="  Finish & Close  ", bg=COLOR_SUCCESS)
        self.btn_cancel.pack_forget()

        # Display Quick Launch Instructions inside the window
        guide_box = tk.Frame(self.content_frame, bg=COLOR_SUCCESS_BG, highlightbackground=COLOR_SUCCESS, highlightthickness=1, padx=14, pady=12)
        guide_box.pack(fill=tk.X, pady=(12, 0))

        lbl_guide_title = tk.Label(
            guide_box,
            text="HOW TO ACCESS XDROP IN YOUR EDITORS:",
            font=("Segoe UI", 10, "bold"),
            fg=COLOR_SUCCESS,
            bg=COLOR_SUCCESS_BG
        )
        lbl_guide_title.pack(anchor="w")

        guide_text = ""
        if self.install_resolve_var.get():
            guide_text += "• DaVinci Resolve: Top menu -> Workspace -> Scripts -> Comp -> Xdrop\n"
        if self.install_adobe_var.get():
            guide_text += "• Adobe Premiere Pro / AE: Top menu -> Window -> Extensions -> Xdrop\n"
        guide_text += "• Headless Engine: Auto-starts when opened, auto-shuts down on close (0 CMD flashes)."

        lbl_guide = tk.Label(
            guide_box,
            text=guide_text,
            font=("Segoe UI", 9),
            fg=COLOR_TEXT,
            bg=COLOR_SUCCESS_BG,
            justify=tk.LEFT
        )
        lbl_guide.pack(anchor="w", pady=(4, 0))


def main():
    app = XdropGuiInstaller()
    app.mainloop()


if __name__ == "__main__":
    main()
