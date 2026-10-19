"""
Desktop App Window Launcher for Xdrop.

Ensures Xdrop launches as a native frameless desktop application window rather than
opening as a generic website tab inside a web browser with URL bar and bookmarks.

Priority:
1. Native pywebview (WebKit/WebView2 native window)
2. Chromium standalone App Mode (--app=http://...) via Microsoft Edge / Google Chrome / Brave
3. Fallback to system default browser only when no standalone window provider exists.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path
from typing import List, Optional


def find_app_mode_browsers() -> List[str]:
    """Finds installed Chromium-based browser executables that support --app mode."""
    candidates = []

    if sys.platform == "win32":
        known_windows_paths = [
            # Microsoft Edge (present on all modern Windows installations)
            os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
            os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
            os.path.expandvars(r"%LocalAppData%\Microsoft\Edge\Application\msedge.exe"),
            # Google Chrome
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
            # Brave Browser
            os.path.expandvars(r"%ProgramFiles%\BraveSoftware\Brave-Browser\Application\brave.exe"),
            os.path.expandvars(r"%LocalAppData%\BraveSoftware\Brave-Browser\Application\brave.exe"),
        ]
        for path in known_windows_paths:
            if path and os.path.isfile(path) and path not in candidates:
                candidates.append(path)

        for name in ("msedge", "chrome", "brave"):
            found = shutil.which(name)
            if found and found not in candidates:
                candidates.append(found)

    elif sys.platform == "darwin":
        mac_apps = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
            os.path.expanduser("~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
        ]
        for path in mac_apps:
            if os.path.isfile(path) and path not in candidates:
                candidates.append(path)

    else:
        # Linux
        for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge", "brave"):
            found = shutil.which(name)
            if found and found not in candidates:
                candidates.append(found)

    return candidates


def launch_app_window(
    url: str,
    title: str = "Xdrop",
    width: int = 390,
    height: int = 640,
    wait: bool = False,
) -> bool:
    """
    Launches the URL in a dedicated, standalone desktop application window.
    Strips browser chrome (URL bar, tabs, bookmarks) so it behaves like a true extension/tool.
    """
    # 1. Attempt pywebview if installed
    try:
        import webview
        window = webview.create_window(
            title=title,
            url=url,
            width=width,
            height=height,
            min_size=(340, 500),
            background_color="#090a0f"
        )
        webview.start()
        return True
    except Exception:
        pass

    # 2. Attempt Chromium standalone App Mode
    browsers = find_app_mode_browsers()
    for browser in browsers:
        try:
            args = [
                browser,
                f"--app={url}",
                f"--window-size={width},{height}",
                "--app-id=Xdrop",
                "--disable-features=Translate",
                "--disable-default-apps",
            ]
            flags = 0
            if sys.platform == "win32":
                if hasattr(subprocess, "CREATE_NO_WINDOW"):
                    flags |= subprocess.CREATE_NO_WINDOW
                if hasattr(subprocess, "DETACHED_PROCESS"):
                    flags |= subprocess.DETACHED_PROCESS

            proc = subprocess.Popen(
                args,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=flags if sys.platform == "win32" else 0,
                start_new_session=sys.platform != "win32",
            )
            if wait:
                proc.wait()
            return True
        except Exception:
            continue

    # 3. Fallback only if no standalone window mechanism is available
    try:
        webbrowser.open(url)
        return True
    except Exception:
        return False
