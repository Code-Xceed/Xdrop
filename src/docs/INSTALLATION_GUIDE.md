# Xdrop Standalone Installers & Complete User Guide

Welcome to **Xdrop** — the high-performance media import and downloading engine built specifically for professional video editors.

Xdrop offers dedicated standalone installers tailored to the exact extension architecture supported by each host application:

### Windows Installers
| Host Application | Dedicated Installer | Primary Extension Format | Secondary / Bonus |
| :--- | :--- | :--- | :--- |
| **DaVinci Resolve** (Free & Studio) | **`XdropInstaller-Resolve.exe`** | Native Fusion UI Script (`Xdrop.lua`) | Studio Workflow Integration + Starter Bin (`.drb`) |
| **Adobe Creative Cloud** (Premiere, AE, Audition) | **`XdropInstaller-Premiere.exe`** | Adobe CEP Docked Panel (`com.xdrop.panel`) | Modern UXP Package (`.ccx`) + Multi-Host JSX |
| **Universal / All Suites** | **`XdropSetup.exe`** | Modern Dark-Mode GUI Multi-Host Scanner | Provisions all detected editors in 1 click |

### macOS Launchers
| Host Application | Dedicated Launcher | Primary Extension Format | Launch Method |
| :--- | :--- | :--- | :--- |
| **Universal / All Suites** | **`XdropSetup.command`** | Full System Scanner & Installer | Double-click in Finder or `./setup_mac.sh` |
| **Adobe Creative Cloud** (Premiere, AE, Audition) | **`XdropSetup-Adobe.command`** | CEP Panel + CSXS PlayerDebugMode + Auto-Start | Double-click in Finder or `./setup_mac.sh --adobe` |
| **DaVinci Resolve** (Free & Studio) | **`XdropSetup-Resolve.command`** | Fusion Lua Script + Studio Plugin + Starter Bin | Double-click in Finder or `./setup_mac.sh --resolve` |

> [!NOTE]
> All installers are **completely standalone** (~11 MB self-contained executables). They do not require Git, Node.js, or an existing Python installation on the user's system.

---

## 1. DaVinci Resolve Installation Guide

### Supported Editions
- **DaVinci Resolve Studio** (Versions 17, 18, 19+)
- **DaVinci Resolve Free** (Versions 17, 18, 19+)

### Supported Extension Types
1. **Native Fusion UI Script (`Xdrop.lua`)**: Matches the architecture of tools like Snap Captions. Runs natively inside both Free and Studio editions with a clean native UI modal.
2. **DaVinci Resolve Companion Starter Bin (`Xdrop - Starter Bin.drb`)**: Pre-configured bin container with color-coded asset hierarchy (`000_Xdrop Assets`, `01_Downloads`, `02_Video Clips`, `03_Music & SFX`, etc.).
3. **Workflow Integration Plugin (`com.xdrop.resolve.workflowintegration`)**: Fully dockable native CEF panel available exclusively on DaVinci Resolve Studio.

---

### Step 1: Run the Dedicated DaVinci Installer
Double-click:
```text
XdropInstaller-Resolve.exe
```
*(Or from PowerShell/CMD: `.\XdropInstaller-Resolve.exe` or `python tools/installer_resolve.py`)*

#### What the installer does automatically:
1. **Targeted Discovery**: Scans your system and registers:
   - `%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Comp\`
   - `%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Workflow Integration Plugins\`
2. **Script Deployment**: Installs `Xdrop.lua` and copies `Xdrop - Starter Bin.drb`.
3. **Safe Cleaning**: Cleans any obsolete versions while strictly preserving third-party scripts (such as `Snap Captions.lua`).
4. **Studio Workflow Integration**: If Resolve Studio is present, installs the dockable Workflow Integration plugin.
5. **Headless Engine Registration**: Registers the background service using `pythonw.exe` and `start_engine.vbs` (guaranteeing **zero flashing terminal windows**).

---

### Step 2: Access Xdrop inside DaVinci Resolve

#### Option A: Native Comp Script (Recommended for Free & Studio)
1. Launch **DaVinci Resolve** and open any project.
2. In the top application menu bar, navigate to:
   ```text
   Workspace -> Scripts -> Comp -> Xdrop
   ```
   *(On the Fusion page, you can also click: `Script -> Xdrop`)*
3. The native dark-mode Xdrop window opens immediately.
4. **Key Features inside the Native Panel**:
   - **Target Bin Selector**: Auto-detects all bins in your active project.
   - **`+ Bins` Button**: 1-click creation of the canonical `000_Xdrop Assets` bin hierarchy.
   - **`Insert to Timeline` Checkbox**: Automatically drops the downloaded clip at your current playhead position on the active timeline.
   - **Format Selector**: Fast 1080p, 4K ProRes/DNxHR, or MP3/WAV audio-only rip.

#### Option B: Studio Docked Workflow Integration (Studio Only)
1. Open DaVinci Resolve Studio.
2. In the top application menu bar, navigate to:
   ```text
   Workspace -> Workflow Integrations -> Xdrop
   ```
3. A native docked panel appears inside DaVinci Resolve. You can dock it anywhere alongside your Media Pool or Inspector.

#### Option C: Importing the Companion Starter Bin
If you prefer starting projects with a ready-to-use bin hierarchy:
1. Open your DaVinci Resolve Media Pool.
2. Right-click inside the bin list and choose **Import Bin...**
3. Select `Xdrop - Starter Bin.drb` located in your Xdrop folder (or `%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Comp\`).
4. Instantly provisions organized, color-coded smart bins ready for drag-and-drop.

---

## 2. Adobe Premiere Pro Installation Guide

### Supported Adobe Applications
- **Adobe Premiere Pro** (2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026+)
- **Adobe After Effects** (2019 through 2026+)
- **Adobe Audition** (2019 through 2026+)

### Supported Extension Types
1. **Adobe CEP Extension (`com.xdrop.panel`)**: Supported natively across CC 2019 through CC 2026+. Fully dockable panel with JSX host scripting (`hostscript.jsx`).
2. **Modern UXP Package (`xdrop-uxp-premiere-1.0.0.ccx`)**: Adobe's modern Unified Extensibility Platform package installable directly via Creative Cloud Desktop.

---

### Step 1: Run the Dedicated Adobe Installer
Double-click:
```text
XdropInstaller-Premiere.exe
```
*(Or from PowerShell/CMD: `.\XdropInstaller-Premiere.exe` or `python tools/installer_premiere.py`)*

#### What the installer does automatically:
1. **CEP Directory Deployment**: Deploys the panel package to:
   ```text
   %APPDATA%\Adobe\CEP\extensions\com.xdrop.panel\
   ```
2. **PlayerDebugMode Registry Configuration**:
   - Automatically writes `PlayerDebugMode = "1"` into Windows Current User Registry (`HKCU\Software\Adobe\CSXS.*`) across versions CSXS.9, CSXS.10, CSXS.11, CSXS.12, CSXS.13, CSXS.14, CSXS.15, and CSXS.16.
   - **Requires zero administrator permissions** and allows Premiere Pro to load custom CEP extensions without code-signing friction.
3. **UXP Package Compilation**: Packages `dist/xdrop-uxp-premiere-1.0.0.ccx` for modern Creative Cloud environments.
4. **After Effects & Audition Support**: Registers the host IDs `PPRO`, `AEFT`, and `AUDT` in `CSXS/manifest.xml` so the panel is available across all three Adobe apps.
5. **Headless Engine Registration**: Registers the background service using `pythonw.exe` and `start_engine.vbs`.

---

### Step 2: Access Xdrop inside Adobe Premiere Pro

#### Option A: Adobe CEP Docked Panel (Instant)
1. Launch **Adobe Premiere Pro** and open a project.
2. In the top application menu bar, navigate to:
   ```text
   Window -> Extensions -> Xdrop
   ```
3. The Xdrop panel opens immediately.
4. Drag and drop the tab to dock it anywhere in your workspace:
   - Next to the **Project Panel / Bins**
   - In the **Source / Program Monitor** pane
   - Next to **Essential Graphics** or **Lumetri Color**
5. **Key Features inside the Premiere Panel**:
   - Paste any video link (YouTube, TikTok, Instagram, Twitter/X, Reddit, Vimeo, direct MP4/M3U8).
   - Click **Download & Import**.
   - Media is automatically imported into your active project bin `000_Xdrop Assets`.
   - If a sequence is active, the media can automatically insert at your playhead on Track V1/A1.

#### Option B: Modern UXP CCX Package (Alternative)
1. Locate `dist\xdrop-uxp-premiere-1.0.0.ccx` in your Xdrop folder.
2. Double-click the `.ccx` file.
3. Creative Cloud Desktop will ask to install the plugin. Click **Install**.
4. In Premiere Pro, access via **Plugins -> Xdrop**.

---

## 3. macOS Installation Guide

### Dedicated & 1-Click Setup Options on macOS
Choose the launcher tailored to your editing workflow:
- **Universal Multi-Host**: Double-click **`XdropSetup.command`** in Finder (or run `./setup_mac.sh`).
- **Adobe Creative Cloud Dedicated**: Double-click **`XdropSetup-Adobe.command`** in Finder (or run `./setup_mac.sh --adobe`).
- **DaVinci Resolve Dedicated**: Double-click **`XdropSetup-Resolve.command`** in Finder (or run `./setup_mac.sh --resolve`).

### What the installer provisions automatically:
1. **Adobe Creative Cloud (Premiere Pro, After Effects, Audition)**:
   - Deploys CEP extension to `~/Library/Application Support/Adobe/CEP/extensions/com.xdrop.panel/`.
   - Executes `defaults write com.adobe.CSXS.<ver> PlayerDebugMode 1` across CSXS versions 9..16 so the extension loads seamlessly without signing roadblocks.
   - Generates `config.json` with macOS background script paths (`~/.xdrop/start_engine.sh`, `~/.xdrop/run_engine.py`).
   - If the background engine is offline when Premiere Pro or After Effects opens, the CEP panel automatically launches the headless daemon on macOS without a terminal window.
2. **DaVinci Resolve (Free & Studio)**:
   - Deploys Lua script to `~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Comp/Xdrop.lua`.
   - Deploys Starter Bin (`Xdrop - Starter Bin.drb`) and Studio Workflow Integration plugin.
3. **Blender VSE Add-on**:
   - Deploys addon to `~/Library/Application Support/Blender/<ver>/scripts/addons/xdrop`.
4. **Background Engine & Zero Sudo**:
   - Deploys engine to `~/.xdrop/run_engine.py` and creates executable `~/.xdrop/start_engine.sh`.
   - Requires zero administrator permissions (`sudo`) — 100% user-space installation.

---

## 4. Linux Installation Guide

### 1-Click Setup on Linux
1. Open a terminal and run:
   ```bash
   ./setup_linux.sh
   ```
2. The installer provisions:
   - **DaVinci Resolve Comp Script**: `~/.local/share/DaVinciResolve/Fusion/Scripts/Comp/Xdrop.lua` and Starter Bin.
   - **Blender VSE Add-on**: `~/.config/blender/<ver>/scripts/addons/xdrop`.
   - **Background Autostart**: `~/.config/autostart/xdrop.desktop`.
   - **Zero Root Needed**: All installations are in the user directory and require zero `sudo` elevation.

---

## 5. Headless Background Engine Architecture

### Why No Terminal Windows or Flickering?
Older tools often spawn a `cmd.exe` or `python.exe` console window that flashes on your screen every time an operation runs or in recurring intervals. 

Xdrop eliminates this entirely using a dedicated three-tier silent launch architecture:
1. **Windowless Python (`pythonw.exe`)**:
   - Instead of standard `python.exe` (which creates a console window subsystem `IMAGE_SUBSYSTEM_WINDOWS_CUI`), Xdrop executes under `pythonw.exe` (`IMAGE_SUBSYSTEM_WINDOWS_GUI`).
2. **Hidden VBScript Wrapper (`start_engine.vbs`)**:
   - Uses Windows Script Host `WScript.Shell.Run` with `intWindowStyle = 0` (hidden) and `bWaitOnReturn = False`. This ensures zero console popups even during background restarts.
3. **Engine Health Check & Auto-Wakeup**:
   - When you click Xdrop inside DaVinci Resolve or Premiere Pro, the panel performs an async ping to:
     ```text
     http://127.0.0.1:8484/api/health
     ```
   - If the engine is already running, it connects in under 15ms.
   - If the engine is stopped, the panel silently triggers `start_engine.vbs` in the background and connects as soon as the port opens.

---

## 4. Verification & Testing

To verify that your installation is 100% operational before editing:

1. **Test Background Service**:
   Open your browser and visit:
   ```text
   http://127.0.0.1:8484/api/health
   ```
   You should see:
   ```json
   {
     "status": "healthy",
     "version": "1.0.0",
     "timestamp": "..."
   }
   ```

2. **Test NLE Integration**:
   - In **DaVinci Resolve**: Open `Workspace -> Scripts -> Comp -> Xdrop`, click `+ Bins`. Look at your Media Pool: the `000_Xdrop Assets` bin will appear instantly.
   - In **Premiere Pro**: Open `Window -> Extensions -> Xdrop`. Paste a short link and click `Download & Import`. The clip will immediately appear in your project bin.

---

## 5. Troubleshooting & Frequently Asked Questions

### DaVinci Resolve: Script Does Not Open or Shows Nothing
1. Open DaVinci Resolve.
2. Go to top menu: **Preferences -> General**.
3. Under **External scripting using**, ensure **Local** or **All Users** is selected.
4. Click **Save** and restart DaVinci Resolve.

### Adobe Premiere Pro: "Xdrop" Not Found in Window -> Extensions
1. Ensure Premiere Pro was completely closed when running `XdropInstaller-Premiere.exe`.
2. Check that the extension folder exists:
   - Press `Win + R`, paste: `%APPDATA%\Adobe\CEP\extensions\com.xdrop.panel` and press Enter.
   - If the folder is missing, rerun `XdropInstaller-Premiere.exe`.
3. Check the Windows Registry:
   - Press `Win + R`, type `regedit`.
   - Navigate to `HKEY_CURRENT_USER\Software\Adobe\CSXS.11` (or your CC version).
   - Ensure `PlayerDebugMode` is set to `"1"`.

### Antivirus False Positive
Some heuristic antivirus scanners flag custom standalone executables built with PyInstaller. `XdropInstaller-Resolve.exe` and `XdropInstaller-Premiere.exe` are completely open-source scripts packaged with standard Python runtimes. If prompted by Windows Defender SmartScreen:
- Click **More info**.
- Click **Run anyway**.
*(Alternatively, you can run the source scripts directly: `python tools/installer_resolve.py` or `python tools/installer_premiere.py`)*

---

## 6. Summary of Files Provided

| File Path | Description |
| :--- | :--- |
| `XdropInstaller-Resolve.exe` | **Dedicated Standalone Installer for DaVinci Resolve** |
| `XdropInstaller-Premiere.exe` | **Dedicated Standalone Installer for Adobe Premiere Pro** |
| `XdropInstaller.exe` | **Universal Master Installer (All Video Editors)** |
| `dist/Xdrop - Starter Bin.drb` | **DaVinci Resolve Companion Color-Coded Starter Bin** |
| `dist/xdrop-uxp-premiere-1.0.0.ccx` | **Modern Adobe Creative Cloud UXP Package** |
| `tools/installer_resolve.py` | Python source installer for DaVinci Resolve |
| `tools/installer_premiere.py` | Python source installer for Premiere Pro |
| `start_engine.vbs` | Silent zero-flicker background engine launcher |

---

## 7. Integrated Auto-Update Mechanism

Xdrop features a zero-friction auto-update engine directly connected to GitHub (`Code-Xceed/Xdrop`):

1. **Automatic Background Check**:
   - Every time Xdrop starts (and periodically every 4 hours), the background engine checks GitHub for newer releases.
   - Checks GitHub Releases and `https://raw.githubusercontent.com/Code-Xceed/Xdrop/master/version.json`.
2. **Universal Notification Prompt in All Editors**:
   - When an update is pushed, a non-intrusive update card appears inside the plugin UI across **DaVinci Resolve**, **Adobe Premiere Pro**, **Adobe After Effects**, and **Adobe Audition**.
   - Displays the new version number, release notes, and an **"Update Now"** button.
3. **1-Click Silent Deployment**:
   - Clicking **Update Now** silently downloads the update package, unpacks it into the engine directory, and automatically re-provisions extension files across DaVinci Resolve and Adobe Creative Cloud.
   - Real-time progress is streamed via WebSocket into an animated progress bar.
   - On completion, the interface reloads to run the newly updated version immediately.
4. **Manual Update Check**:
   - In any editor panel, navigate to **Settings → Updates & System** and click **Check for Updates** to verify or install updates on demand.
