"""
Xdrop Deep System & Editor Discovery Scanner.

Performs deep multi-vector scanning across Windows/macOS/Linux to discover all installed
video editing software and digital audio workstations (DAWs), regardless of whether they
were installed via standard installers, custom drives, Steam, portable folders, or user profiles.
"""

from __future__ import annotations

import os
import platform
import string
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set

if sys.platform == "win32":
    import winreg
else:
    winreg = None  # type: ignore


@dataclass
class DetectedEditor:
    """Represents a discovered video editing or audio workstation installation."""
    editor_id: str             # "resolve_studio", "resolve_free", "premiere", "aftereffects", "audition", "blender", "capcut", "vegas", "avid", "finalcut"
    name: str                  # Friendly display name
    vendor: str                # Software vendor
    version: str               # Discovered version or range
    install_dir: Optional[Path] = None
    executable_path: Optional[Path] = None
    detection_sources: List[str] = field(default_factory=list)
    extension_type: str = "Native Plugin / Extension"
    is_running: bool = False
    ready_for_extension: bool = True
    installed_extension_paths: List[Path] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return {
            "id": self.editor_id,
            "name": self.name,
            "vendor": self.vendor,
            "version": self.version,
            "installDir": str(self.install_dir) if self.install_dir else None,
            "executablePath": str(self.executable_path) if self.executable_path else None,
            "detectionSources": self.detection_sources,
            "extensionType": self.extension_type,
            "isRunning": self.is_running,
            "readyForExtension": self.ready_for_extension,
            "installedExtensionPaths": [str(p) for p in self.installed_extension_paths],
        }


@dataclass
class DeepScanReport:
    """Consolidated report produced by deep multi-vector system scanning."""
    system: str
    drives_scanned: List[str]
    editors: List[DetectedEditor]
    running_processes: List[str]
    total_found: int = 0

    def to_dict(self) -> Dict[str, object]:
        return {
            "system": self.system,
            "drivesScanned": self.drives_scanned,
            "totalFound": len(self.editors),
            "runningProcesses": self.running_processes,
            "editors": [e.to_dict() for e in self.editors],
        }


def get_available_drives() -> List[str]:
    """Finds all available local drive roots on Windows, or root / on Unix."""
    if sys.platform != "win32":
        return ["/"]

    drives: List[str] = []
    for letter in string.ascii_uppercase:
        drive_path = f"{letter}:\\"
        if os.path.exists(drive_path):
            drives.append(drive_path)
    return drives


def get_running_process_names() -> List[str]:
    """Queries active system processes to detect running editor processes with zero subprocesses."""
    try:
        from xdrop.process_util import get_running_process_names as win_proc_names
        return list(win_proc_names())
    except Exception:
        pass
    running: List[str] = []
    if sys.platform == "win32":
        try:
            output = subprocess.check_output(
                ["tasklist", "/FO", "CSV", "/NH"],
                text=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                stderr=subprocess.DEVNULL,
            )
            for line in output.splitlines():
                if line.strip():
                    parts = line.split(",")
                    if parts:
                        proc = parts[0].strip('"\r\n ')
                        if proc.endswith(".exe"):
                            running.append(proc.lower())
        except Exception:
            pass
    elif sys.platform == "darwin" or sys.platform.startswith("linux"):
        try:
            output = subprocess.check_output(
                ["ps", "-A", "-o", "comm="],
                text=True,
                stderr=subprocess.DEVNULL,
            )
            running = [os.path.basename(p.strip()).lower() for p in output.splitlines() if p.strip()]
        except Exception:
            pass
    return list(set(running))



class DeepEditorScanner:
    """Deep multi-vector editor scanner searching across Registry, Drives, and AppData."""

    def __init__(self) -> None:
        self.drives = get_available_drives()
        self.running_processes = get_running_process_names()

    def scan(self) -> DeepScanReport:
        found_map: Dict[str, DetectedEditor] = {}

        if sys.platform == "win32":
            self._scan_windows_registry_uninstall(found_map)
            self._scan_windows_registry_app_paths(found_map)
            self._scan_windows_registry_vendor_keys(found_map)
            self._scan_windows_drives_and_filesystem(found_map)
            self._scan_windows_user_profiles(found_map)
        elif sys.platform == "darwin":
            self._scan_macos_applications(found_map)
        else:
            self._scan_linux_applications(found_map)

        # Mark process running states
        for editor in found_map.values():
            if editor.executable_path:
                exe_name = editor.executable_path.name.lower()
                if exe_name in self.running_processes:
                    editor.is_running = True
            elif editor.editor_id in ("premiere", "aftereffects", "audition"):
                for p in self.running_processes:
                    if "premiere" in p or "afterfx" in p or "audition" in p:
                        editor.is_running = True
                        break
            elif "resolve" in editor.editor_id:
                if "resolve.exe" in self.running_processes:
                    editor.is_running = True
            elif editor.editor_id == "blender":
                if "blender.exe" in self.running_processes or "blender" in self.running_processes:
                    editor.is_running = True

        editors_list = sorted(list(found_map.values()), key=lambda e: e.name)
        return DeepScanReport(
            system=platform.system(),
            drives_scanned=self.drives,
            editors=editors_list,
            running_processes=self.running_processes,
            total_found=len(editors_list),
        )

    # --- Windows Registry Scanners ----------------------------------------------------

    def _scan_windows_registry_uninstall(self, found: Dict[str, DetectedEditor]) -> None:
        if not winreg:
            return

        roots = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall", winreg.KEY_WOW64_64KEY, "HKLM 64-bit"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall", winreg.KEY_WOW64_32KEY, "HKLM 32-bit"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall", 0, "HKCU"),
        ]

        for hkey, subkey, access_flag, label in roots:
            try:
                flags = winreg.KEY_READ | access_flag if access_flag else winreg.KEY_READ
                with winreg.OpenKey(hkey, subkey, 0, flags) as key:
                    count = winreg.QueryInfoKey(key)[0]
                    for i in range(count):
                        try:
                            key_name = winreg.EnumKey(key, i)
                            with winreg.OpenKey(key, key_name, 0, flags) as sub:
                                self._evaluate_uninstall_key(sub, label, found)
                        except Exception:
                            continue
            except Exception:
                continue

    def _evaluate_uninstall_key(self, key, label: str, found: Dict[str, DetectedEditor]) -> None:
        def get_val(name: str) -> str:
            try:
                val, _ = winreg.QueryValueEx(key, name)
                return str(val) if val else ""
            except Exception:
                return ""

        display_name = get_val("DisplayName")
        if not display_name:
            return

        name_lower = display_name.lower()
        version = get_val("DisplayVersion") or "Unknown"
        location = get_val("InstallLocation")
        icon = get_val("DisplayIcon")

        exe_path: Optional[Path] = None
        if icon and icon.lower().endswith(".exe") and os.path.isfile(icon):
            exe_path = Path(icon)
        elif location:
            loc_path = Path(location)
            if loc_path.is_dir():
                for candidate in loc_path.glob("*.exe"):
                    if any(term in candidate.name.lower() for term in ["resolve", "premiere", "afterfx", "audition", "blender"]):
                        exe_path = candidate
                        break

        install_dir = Path(location) if location and os.path.isdir(location) else None

        # 1. DaVinci Resolve
        if "davinci resolve" in name_lower and "control panels" not in name_lower and "renderer" not in name_lower:
            is_studio = "studio" in name_lower
            self._upsert_editor(
                found,
                editor_id="resolve",
                name="DaVinci Resolve Studio" if is_studio else "DaVinci Resolve",
                vendor="Blackmagic Design",
                version=version,
                install_dir=install_dir,
                executable_path=exe_path or Path("C:/Program Files/Blackmagic Design/DaVinci Resolve/Resolve.exe"),
                detection_source=f"Registry ({label})",
                extension_type="Workflow Integration (Studio Dock) & Python Utility Script",
            )

        # 2. Adobe Premiere Pro
        elif "adobe premiere pro" in name_lower:
            self._upsert_editor(
                found,
                editor_id="premiere",
                name=display_name,
                vendor="Adobe",
                version=version,
                install_dir=install_dir,
                executable_path=exe_path,
                detection_source=f"Registry ({label})",
                extension_type="CEP & UXP Docked Panel",
            )

        # 3. Adobe After Effects
        elif "adobe after effects" in name_lower:
            self._upsert_editor(
                found,
                editor_id="aftereffects",
                name=display_name,
                vendor="Adobe",
                version=version,
                install_dir=install_dir,
                executable_path=exe_path,
                detection_source=f"Registry ({label})",
                extension_type="CEP & UXP Docked Panel",
            )

        # 4. Adobe Audition
        elif "adobe audition" in name_lower:
            self._upsert_editor(
                found,
                editor_id="audition",
                name=display_name,
                vendor="Adobe",
                version=version,
                install_dir=install_dir,
                executable_path=exe_path,
                detection_source=f"Registry ({label})",
                extension_type="CEP Docked Panel",
            )

        # 5. Blender
        elif "blender" in name_lower:
            self._upsert_editor(
                found,
                editor_id="blender",
                name=display_name,
                vendor="Blender Foundation",
                version=version,
                install_dir=install_dir,
                executable_path=exe_path,
                detection_source=f"Registry ({label})",
                extension_type="Sequencer Add-on (N-Panel)",
            )

        # 6. CapCut
        elif "capcut" in name_lower:
            self._upsert_editor(
                found,
                editor_id="capcut",
                name="CapCut Desktop",
                vendor="ByteDance",
                version=version,
                install_dir=install_dir,
                executable_path=exe_path,
                detection_source=f"Registry ({label})",
                extension_type="Timeline Drag-and-Drop & Watch Folder",
            )

    def _scan_windows_registry_app_paths(self, found: Dict[str, DetectedEditor]) -> None:
        if not winreg:
            return

        app_paths_map = {
            "resolve.exe": ("resolve", "DaVinci Resolve", "Blackmagic Design", "Workflow Integration / Script"),
            "adobe premiere pro.exe": ("premiere", "Adobe Premiere Pro", "Adobe", "CEP & UXP Docked Panel"),
            "afterfx.exe": ("aftereffects", "Adobe After Effects", "Adobe", "CEP & UXP Docked Panel"),
            "adobe audition.exe": ("audition", "Adobe Audition", "Adobe", "CEP Docked Panel"),
            "blender.exe": ("blender", "Blender VSE", "Blender Foundation", "Sequencer Add-on (N-Panel)"),
            "capcut.exe": ("capcut", "CapCut Desktop", "ByteDance", "Timeline Drag-and-Drop"),
        }

        roots = [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]
        sub = r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"

        for hkey in roots:
            try:
                with winreg.OpenKey(hkey, sub) as key:
                    for exe_key, (eid, ename, vendor, ext_type) in app_paths_map.items():
                        try:
                            with winreg.OpenKey(key, exe_key) as item_key:
                                exe_val, _ = winreg.QueryValueEx(item_key, "")
                                if exe_val and os.path.isfile(exe_val):
                                    exe_path = Path(exe_val)
                                    self._upsert_editor(
                                        found,
                                        editor_id=eid,
                                        name=ename,
                                        vendor=vendor,
                                        version="Auto-detected",
                                        install_dir=exe_path.parent,
                                        executable_path=exe_path,
                                        detection_source="Registry (App Paths)",
                                        extension_type=ext_type,
                                    )
                        except Exception:
                            continue
            except Exception:
                continue

    def _scan_windows_registry_vendor_keys(self, found: Dict[str, DetectedEditor]) -> None:
        if not winreg:
            return

        # 1. Blackmagic Design
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Blackmagic Design\DaVinci Resolve") as k:
                ver, _ = winreg.QueryValueEx(k, "Version")
                self._upsert_editor(
                    found,
                    editor_id="resolve",
                    name="DaVinci Resolve",
                    vendor="Blackmagic Design",
                    version=str(ver),
                    install_dir=Path("C:/Program Files/Blackmagic Design/DaVinci Resolve"),
                    executable_path=Path("C:/Program Files/Blackmagic Design/DaVinci Resolve/Resolve.exe"),
                    detection_source="Registry (Blackmagic Key)",
                    extension_type="Workflow Integration (Studio Dock) & Python Utility Script",
                )
        except Exception:
            pass

        # 2. Adobe User Keys (Premiere Pro, After Effects, Audition)
        for sub_name, eid, ename, ext_type in [
            (r"SOFTWARE\Adobe\Premiere Pro", "premiere", "Adobe Premiere Pro", "CEP & UXP Docked Panel"),
            (r"SOFTWARE\Adobe\After Effects", "aftereffects", "Adobe After Effects", "CEP & UXP Docked Panel"),
            (r"SOFTWARE\Adobe\Audition", "audition", "Adobe Audition", "CEP Docked Panel"),
        ]:
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_name) as k:
                    count = winreg.QueryInfoKey(k)[0]
                    versions = [winreg.EnumKey(k, i) for i in range(count) if winreg.EnumKey(k, i) != "AppStates"]
                    ver_str = ", ".join(versions) if versions else "Installed"
                    self._upsert_editor(
                        found,
                        editor_id=eid,
                        name=ename,
                        vendor="Adobe",
                        version=ver_str,
                        install_dir=None,
                        executable_path=None,
                        detection_source="Registry (Adobe User Key)",
                        extension_type=ext_type,
                    )
            except Exception:
                pass

    def _scan_windows_drives_and_filesystem(self, found: Dict[str, DetectedEditor]) -> None:
        search_patterns = [
            # DaVinci Resolve
            ("Program Files/Blackmagic Design/DaVinci Resolve/Resolve.exe", "resolve", "DaVinci Resolve", "Blackmagic Design", "Workflow Integration (Studio Dock) & Python Utility Script"),
            # Adobe Standard
            ("Program Files/Adobe/Adobe Premiere Pro*/Adobe Premiere Pro.exe", "premiere", "Adobe Premiere Pro", "Adobe", "CEP & UXP Docked Panel"),
            ("Program Files/Adobe/Adobe After Effects*/Support Files/AfterFX.exe", "aftereffects", "Adobe After Effects", "Adobe", "CEP & UXP Docked Panel"),
            ("Program Files/Adobe/Adobe Audition*/Adobe Audition.exe", "audition", "Adobe Audition", "Adobe", "CEP Docked Panel"),
            # Blender Standard & Steam
            ("Program Files/Blender Foundation/Blender*/blender.exe", "blender", "Blender VSE", "Blender Foundation", "Sequencer Add-on (N-Panel)"),
            ("SteamLibrary/steamapps/common/Blender/blender.exe", "blender", "Blender VSE (Steam)", "Blender Foundation", "Sequencer Add-on (N-Panel)"),
            ("Program Files (x86)/Steam/steamapps/common/Blender/blender.exe", "blender", "Blender VSE (Steam)", "Blender Foundation", "Sequencer Add-on (N-Panel)"),
        ]

        for drive in self.drives:
            drive_path = Path(drive)
            for pattern, eid, ename, vendor, ext_type in search_patterns:
                try:
                    for match in drive_path.glob(pattern):
                        if match.is_file():
                            self._upsert_editor(
                                found,
                                editor_id=eid,
                                name=ename,
                                vendor=vendor,
                                version="Discovered on Drive",
                                install_dir=match.parent,
                                executable_path=match,
                                detection_source=f"Filesystem ({drive})",
                                extension_type=ext_type,
                            )
                except Exception:
                    continue

    def _scan_windows_user_profiles(self, found: Dict[str, DetectedEditor]) -> None:
        appdata = Path(os.environ.get("APPDATA", ""))
        local_appdata = Path(os.environ.get("LOCALAPPDATA", ""))

        # 1. Blender User Profiles
        blender_root = appdata / "Blender Foundation" / "Blender"
        if blender_root.is_dir():
            for ver_dir in blender_root.iterdir():
                if ver_dir.is_dir() and ver_dir.name[0].isdigit():
                    self._upsert_editor(
                        found,
                        editor_id="blender",
                        name=f"Blender {ver_dir.name}",
                        vendor="Blender Foundation",
                        version=ver_dir.name,
                        install_dir=ver_dir,
                        executable_path=None,
                        detection_source="User Profile (%APPDATA%)",
                        extension_type="Sequencer Add-on (N-Panel)",
                    )

        # 2. CapCut Desktop in LocalAppData
        capcut_dir = local_appdata / "CapCut" / "Apps"
        if capcut_dir.is_dir():
            for candidate in capcut_dir.glob("**/CapCut.exe"):
                if candidate.is_file():
                    self._upsert_editor(
                        found,
                        editor_id="capcut",
                        name="CapCut Desktop",
                        vendor="ByteDance",
                        version="User Install",
                        install_dir=candidate.parent,
                        executable_path=candidate,
                        detection_source="User Profile (%LOCALAPPDATA%)",
                        extension_type="Timeline Drag-and-Drop",
                    )
                    break

        # 3. DaVinci Resolve Support Directory
        resolve_support = appdata / "Blackmagic Design" / "DaVinci Resolve" / "Support"
        if resolve_support.is_dir() and "resolve" not in found:
            self._upsert_editor(
                found,
                editor_id="resolve",
                name="DaVinci Resolve",
                vendor="Blackmagic Design",
                version="Installed (Support Profile)",
                install_dir=resolve_support,
                executable_path=None,
                detection_source="User Profile (%APPDATA%)",
                extension_type="Workflow Integration (Studio Dock) & Python Utility Script",
            )

    # --- macOS Applications Scanner ---------------------------------------------------

    def _scan_macos_applications(self, found: Dict[str, DetectedEditor]) -> None:
        app_dirs = [Path("/Applications"), Path.home() / "Applications"]
        macos_apps = [
            ("DaVinci Resolve/DaVinci Resolve.app", "resolve_studio", "DaVinci Resolve", "Blackmagic Design", "Workflow Integration / Python Script"),
            ("DaVinci Resolve Studio/DaVinci Resolve.app", "resolve_studio", "DaVinci Resolve Studio", "Blackmagic Design", "Workflow Integration / Python Script"),
            ("Adobe Premiere Pro*/Adobe Premiere Pro*.app", "premiere", "Adobe Premiere Pro", "Adobe", "CEP & UXP Docked Panel"),
            ("Adobe After Effects*/Adobe After Effects*.app", "aftereffects", "Adobe After Effects", "Adobe", "CEP & UXP Docked Panel"),
            ("Adobe Audition*/Adobe Audition*.app", "audition", "Adobe Audition", "Adobe", "CEP Docked Panel"),
            ("Blender.app", "blender", "Blender VSE", "Blender Foundation", "Sequencer Add-on (N-Panel)"),
            ("Final Cut Pro.app", "finalcut", "Apple Final Cut Pro", "Apple Inc.", "FCPXML 1.11 / Universal Drag-and-Drop"),
            ("CapCut.app", "capcut", "CapCut Desktop", "ByteDance", "Timeline Drag-and-Drop"),
        ]

        for base in app_dirs:
            if not base.is_dir():
                continue
            for pattern, eid, ename, vendor, ext_type in macos_apps:
                for match in base.glob(pattern):
                    if match.is_dir():
                        self._upsert_editor(
                            found,
                            editor_id=eid,
                            name=ename,
                            vendor=vendor,
                            version="macOS Application",
                            install_dir=match,
                            executable_path=match / "Contents" / "MacOS" / match.stem,
                            detection_source=f"Application Bundle ({match})",
                            extension_type=ext_type,
                        )

    # --- Linux Applications Scanner ---------------------------------------------------

    def _scan_linux_applications(self, found: Dict[str, DetectedEditor]) -> None:
        linux_binaries = [
            ("/opt/resolve/bin/resolve", "resolve_studio", "DaVinci Resolve", "Blackmagic Design", "Python Utility Script"),
            ("/usr/bin/blender", "blender", "Blender VSE", "Blender Foundation", "Sequencer Add-on"),
            ("/usr/local/bin/blender", "blender", "Blender VSE", "Blender Foundation", "Sequencer Add-on"),
        ]
        for path_str, eid, ename, vendor, ext_type in linux_binaries:
            p = Path(path_str)
            if p.is_file():
                self._upsert_editor(
                    found,
                    editor_id=eid,
                    name=ename,
                    vendor=vendor,
                    version="Linux Package",
                    install_dir=p.parent,
                    executable_path=p,
                    detection_source=f"Binary Path ({p})",
                    extension_type=ext_type,
                )

    # --- Internal Helpers -------------------------------------------------------------

    def _upsert_editor(
        self,
        found: Dict[str, DetectedEditor],
        editor_id: str,
        name: str,
        vendor: str,
        version: str,
        install_dir: Optional[Path],
        executable_path: Optional[Path],
        detection_source: str,
        extension_type: str,
    ) -> None:
        if editor_id in found:
            existing = found[editor_id]
            if detection_source not in existing.detection_sources:
                existing.detection_sources.append(detection_source)
            if not existing.executable_path and executable_path:
                existing.executable_path = executable_path
            if not existing.install_dir and install_dir:
                existing.install_dir = install_dir
            if version and version != "Unknown":
                if existing.version in ("Unknown", "Auto-detected") or len(version) > len(existing.version):
                    existing.version = version
            if "Studio" in name and "Studio" not in existing.name:
                existing.name = name
        else:
            found[editor_id] = DetectedEditor(
                editor_id=editor_id,
                name=name,
                vendor=vendor,
                version=version,
                install_dir=install_dir,
                executable_path=executable_path,
                detection_sources=[detection_source],
                extension_type=extension_type,
            )


def run_scanner() -> DeepScanReport:
    """Convenience helper to run deep scanner and return results."""
    scanner = DeepEditorScanner()
    return scanner.scan()


if __name__ == "__main__":
    report = run_scanner()
    print(f"Deep Scan completed. Found {report.total_found} supported editor(s) on {report.system}:")
    for ed in report.editors:
        print(f"  [+] {ed.name} ({ed.vendor}) - Version: {ed.version}")
        print(f"      Executable: {ed.executable_path}")
        print(f"      Extension Type: {ed.extension_type}")
        print(f"      Detected via: {', '.join(ed.detection_sources)}")
        print(f"      Currently Running: {'YES' if ed.is_running else 'NO'}")
