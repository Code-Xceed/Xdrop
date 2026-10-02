# Xdrop Installation & Setup Guide

Xdrop is designed to provide a friction-free setup for video editors working inside DaVinci Resolve.

---

## 1. Quick Installation for End-Users

1. **Download & Run Installer**:
   Run the generated `Xdrop-Installer-v1.0.0.exe` (built via Inno Setup).
   The installer automatically:
   - Installs the backend runtime and web interface.
   - Installs the `Xdrop.py` launcher script into DaVinci Resolve's Scripts directory.
   - Creates a Desktop and Start Menu shortcut.

2. **Open DaVinci Resolve**:
   Start DaVinci Resolve and open any project.

3. **Open Xdrop**:
   Go to the top menu in DaVinci Resolve:
   **Workspace → Scripts → Utility → Xdrop**
   The Xdrop interface will open immediately.

---

## 2. Portable / Manual Setup

If you prefer running Xdrop from source or a portable directory:

1. **Install Menu Script**:
   Run the PowerShell helper:
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\install-resolve-script.ps1
   ```
   Or double-click `scripts\install-resolve-script.bat`.

2. **Start the Companion Service**:
   Double-click `scripts\start-gui.bat` (to launch with a native desktop window) or `scripts\start-service.bat` (to run in background).

---

## 3. Configuring DaVinci Resolve External Scripting

In rare cases where DaVinci Resolve does not allow external Python scripts to query it:
1. Open DaVinci Resolve.
2. Go to **Preferences → General**.
3. Under **External scripting using**, ensure **Local** or **All Users** is selected.
4. Click **Save** and restart DaVinci Resolve.

---

## 4. Configuring FFmpeg

Xdrop automatically detects FFmpeg if it is installed in standard locations (including Chocolatey, Scoop, ShareX, or system PATH).
If you have a custom FFmpeg binary:
1. Open Xdrop.
2. Go to the **Settings** tab.
3. In the **FFmpeg Executable Path** field, enter the full path to `ffmpeg.exe`.
4. Click **Save Settings**.
