# Xdrop

> **Universal High-Performance Media Importer for Video Editors**  
> *DaVinci Resolve (Free & Studio) • Adobe Premiere Pro • Adobe After Effects • Adobe Audition*  
>  
> *Paste URL → Detect Platform → Inspect Quality → Download & Transcode → Instantly Drop into Timelines & Bins.*

[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-blue.svg)]()
[![Editors](https://img.shields.io/badge/editors-DaVinci%20Resolve%20%7C%20Premiere%20Pro%20%7C%20After%20Effects%20%7C%20Audition-purple.svg)]()
[![Tests](https://img.shields.io/badge/tests-110%20passed-brightgreen.svg)]()
[![License](https://img.shields.io/badge/license-MIT-purple.svg)](LICENSE)

---

## ⚡ Dedicated Standalone Setups

Xdrop provides dedicated, focused installers tailored specifically for each video editor ecosystem. Each installer features a dark studio GUI, multi-drive deep scanner, and custom installation folder support with zero admin/root requirements:

### 1. DaVinci Resolve (Free & Studio 18, 19, 20+)
| Platform | Dedicated Setup Method | Details |
| :--- | :--- | :--- |
| **Windows** | [**`XdropInstaller-Resolve.exe`**](XdropInstaller-Resolve.exe) *(or `setup_resolve.bat`)* | **Standalone Obsidian Studio GUI**<br>• Deep-scans all drives (`C:`, `D:`, `E:`) for DaVinci Resolve Free & Studio<br>• Custom folder selection ("Browse Custom Folder...")<br>• Deploys Native Fusion Comp Script (`Xdrop.lua`) & Starter Bin (`.drb`)<br>• Deploys Studio Workflow Integration docked panel (`WorkflowIntegration.node`)<br>• Provisions zero-flicker headless engine with auto-start |
| **macOS** | [**`XdropSetup-Resolve.command`**](XdropSetup-Resolve.command) *(or `./setup_mac.sh --resolve`)* | Installs Lua script to `~/Library/Application Support/.../Fusion/Scripts/Comp/`<br>Provisions starter bin, LaunchAgent daemon, and Studio Workflow Integration panel |
| **Linux** | `./setup_linux.sh --resolve` | Installs to `~/.local/share/DaVinciResolve/Fusion/Scripts/Comp/` |

### 2. Adobe Premiere Pro & Creative Cloud (CC 2020–2026+)
| Platform | Dedicated Setup Method | Details |
| :--- | :--- | :--- |
| **Windows** | [**`XdropInstaller-Premiere.exe`**](XdropInstaller-Premiere.exe) *(or `setup_premiere.bat`)* | **Standalone Creative Cloud Midnight GUI**<br>• Deep-scans all drives (`C:`, `D:`, `E:`) for Premiere, After Effects & Audition<br>• Custom CEP directory selection ("Browse Custom CEP Directory...")<br>• Deploys Native CEP Docked Panel (`com.xdrop.panel`)<br>• Configures Windows Registry `PlayerDebugMode` across CSXS 6..18 (no admin needed)<br>• Packages modern UXP bundles (`.ccx`) |
| **macOS** | [**`XdropSetup-Adobe.command`**](XdropSetup-Adobe.command) *(or `./setup_mac.sh --adobe`)* | Deploys CEP extension to `~/Library/Application Support/Adobe/CEP/extensions/`<br>Configures `defaults write com.adobe.CSXS.<ver> PlayerDebugMode 1`<br>Spawns silent background daemon |
| **Linux** | `./setup_linux.sh --adobe` | Configures local CEP / browser bridge |

> [!NOTE]
> **Setup Selector Menu**: Running [`setup.bat`](setup.bat) on Windows or [`setup_mac.sh`](setup_mac.sh) on macOS presents an interactive choice to launch either dedicated installer.

---

## 🎬 How to Launch Xdrop in Your Editors

### 1. DaVinci Resolve (Free & Studio)
1. Run [**`XdropInstaller-Resolve.exe`**](XdropInstaller-Resolve.exe) (or double-click `setup_resolve.bat`).
2. Launch DaVinci Resolve and open any project.
3. Access via top menu:
   - **DaVinci Resolve Free & Studio**: **Workspace → Scripts → Comp → Xdrop**  
     *(Launches the dedicated standalone Studio window with 100% zero-flicker background engine).*
   - **DaVinci Resolve Studio**: **Workspace → Workflow Integrations → Xdrop**  
     *(Opens the dockable Studio panel right alongside your Media Pool and Timeline).*
   - **Utility Launcher**: **Workspace → Scripts → Utility → Xdrop**.
4. **Starter Bins**: The installer pre-loads the canonical `000_Xdrop Assets` bin hierarchy (`01_Downloads`, `02_Video Clips`, `03_Music & SFX`, `04_Dialogue & Audio`, `05_Proxies & Renders`).

### 2. Adobe Premiere Pro (CC 2020–2026+)
1. Run [**`XdropInstaller-Premiere.exe`**](XdropInstaller-Premiere.exe) (or double-click `setup_premiere.bat`).
2. Launch Premiere Pro and open any project.
3. Open from top menu: **Window → Extensions → Xdrop**.
4. Drag and dock the panel anywhere in your workspace (next to Project Bins, Source Monitor, or Effect Controls).
5. Paste any URL and click **Download & Import**; media drops directly into your active project bin and timeline at the playhead.

### 3. Adobe After Effects & Audition
- Open from top menu: **Window → Extensions → Xdrop**.
- In **After Effects**: media automatically drops into the active project bin and composition.
- In **Audition**: audio rips drop straight into the active waveform or multitrack session.

---

## ✨ Robustness & Custom Installation Support

- **Multi-Drive Deep Scanning**: Automatically scans all connected drive roots (`C:`, `D:`, `E:`, `F:`, etc.) for standard and custom installation paths of DaVinci Resolve and Adobe Creative Cloud apps.
- **Custom Folder Installation**: Select "Custom Installation Folder" to deploy directly into custom drive letters, portable installations, or custom network/NAS paths.
- **Safe Cleanup**: Intelligently purges old or duplicate `ResolveFetch` files across all script roots while strictly preserving third-party scripts (e.g. Snap Captions, Reactor).
- **Registry Configuration without Elevation**: Configures `PlayerDebugMode = 1` for Adobe CSXS versions 6 through 18 under `HKCU`, requiring zero administrator privileges.
- **Zero-Flicker Headless Engine**: Launches via `pythonw.exe` and `start_engine.vbs` using `CREATE_NO_WINDOW`. Zero black command prompt windows or console flashes.
- **Self-Healing Background Daemon**: Listens on `http://127.0.0.1:8484`, automatically boots when an extension opens, and auto-quits on idle.
- **Universal Provider Support**: One-click downloads with best quality detection (4K/1080p/60fps) from YouTube, TikTok, Instagram, Twitter/X, Reddit, Vimeo, and direct media URLs.

---

## 📁 Repository Structure

```text
Xdrop/
├── XdropInstaller-Resolve.exe      # Dedicated DaVinci Resolve Windows Installer (Studio GUI)
├── XdropInstaller-Premiere.exe     # Dedicated Adobe Premiere Pro Windows Installer (CC GUI)
├── setup_resolve.bat               # 1-Click DaVinci Resolve Setup Script
├── setup_premiere.bat              # 1-Click Adobe Premiere Pro Setup Script
├── setup.bat                       # Interactive Setup Selector (Resolve vs Premiere)
├── run.bat                         # 1-Click Windows Background Engine Launcher
├── XdropSetup-Resolve.command      # Dedicated DaVinci Resolve macOS Launcher
├── XdropSetup-Adobe.command        # Dedicated Adobe Creative Cloud macOS Launcher
├── setup_mac.sh                    # macOS Dedicated Setup Script
├── setup_linux.sh                  # Linux Dedicated Setup Script
├── run.sh                          # macOS / Linux Launcher Script
├── version.json                    # Release version & update definition
├── requirements.txt                # Python dependencies
├── LICENSE                         # MIT License
├── README.md                       # Project overview & guide
└── src/                            # Clean source architecture
    ├── desktop-service/            # Headless Python backend engine & queue
    ├── resolve-plugin/             # Studio UI frontend (React/Vite) & Resolve scripts
    ├── premiere-plugin/            # Adobe CEP Panel & UXP Packages
    ├── resolve-workflow-integration# DaVinci Studio Workflow Integration
    ├── blender-addon/              # Blender Sequencer Add-on
    ├── browser-extension/          # Browser Companion Extension
    ├── tools/                      # Dedicated installers & packaging scripts
    ├── tests/                      # Automated test suite (110 passing tests)
    └── docs/                       # Technical documentation
```

---

## 📄 License

MIT License. Designed and built for professional video editors.
