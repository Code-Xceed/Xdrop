import sys
import os
import subprocess
from typing import Union, List, Set, Optional

if sys.platform == "win32":
    import ctypes
    import ctypes.wintypes

    TH32CS_SNAPPROCESS = 0x00000002

    class PROCESSENTRY32(ctypes.Structure):
        _fields_ = [
            ("dwSize", ctypes.wintypes.DWORD),
            ("cntUsage", ctypes.wintypes.DWORD),
            ("th32ProcessID", ctypes.wintypes.DWORD),
            ("th32DefaultHeapID", ctypes.c_void_p),
            ("th32ModuleID", ctypes.wintypes.DWORD),
            ("cntThreads", ctypes.wintypes.DWORD),
            ("th32ParentProcessID", ctypes.wintypes.DWORD),
            ("pcPriClassBase", ctypes.c_long),
            ("dwFlags", ctypes.wintypes.DWORD),
            ("szExeFile", ctypes.c_char * 260)
        ]

    def get_running_process_names() -> Set[str]:
        """Returns set of all running process names in lower-case with zero subprocess spawns."""
        names: Set[str] = set()
        h = ctypes.windll.kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
        if h == -1:
            return names
        try:
            pe = PROCESSENTRY32()
            pe.dwSize = ctypes.sizeof(PROCESSENTRY32)
            if ctypes.windll.kernel32.Process32First(h, ctypes.byref(pe)):
                while True:
                    name = pe.szExeFile.decode("ascii", "ignore").strip().lower()
                    if name:
                        names.add(name)
                    if not ctypes.windll.kernel32.Process32Next(h, ctypes.byref(pe)):
                        break
        finally:
            ctypes.windll.kernel32.CloseHandle(h)
        return names

    def is_process_running(target_names: Union[str, List[str]]) -> bool:
        """Checks if any target executable is running without spawning tasklist or console windows."""
        if isinstance(target_names, str):
            targets = [target_names.lower()]
        else:
            targets = [t.lower() for t in target_names]
        running = get_running_process_names()
        return any(t in running for t in targets)

    def install_silent_subprocess_hook() -> None:
        """Globally hooks subprocess.Popen on Windows to ensure CREATE_NO_WINDOW and SW_HIDE are always active.
        
        This permanently eliminates CMD flashes/flickering from any subprocess (ffmpeg, yt-dlp, git, etc).
        """
        _orig_init = subprocess.Popen.__init__

        def _silent_init(self, *args, **kwargs):
            creationflags = kwargs.get("creationflags", 0)
            creationflags |= subprocess.CREATE_NO_WINDOW
            kwargs["creationflags"] = creationflags

            startupinfo = kwargs.get("startupinfo")
            if startupinfo is None:
                startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0  # SW_HIDE
            kwargs["startupinfo"] = startupinfo

            _orig_init(self, *args, **kwargs)

        subprocess.Popen.__init__ = _silent_init

else:
    def is_process_running(target_names: Union[str, List[str]]) -> bool:
        if isinstance(target_names, str):
            targets = [target_names]
        else:
            targets = target_names
        for t in targets:
            try:
                res = subprocess.run(["pgrep", "-f", t], capture_output=True, timeout=2.0)
                if res.returncode == 0:
                    return True
            except Exception:
                pass
        return False

    def install_silent_subprocess_hook() -> None:
        pass
