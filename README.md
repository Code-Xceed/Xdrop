# Xdrop

> **Universal High-Performance Media Importer for Video Editors**  
> *DaVinci Resolve • Adobe Premiere Pro • Adobe After Effects • Adobe Audition*  
>  
> *Paste URL → Detect Platform → Inspect Quality → Download & Transcode → Instantly Drop into Timelines & Bins.*

[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-blue.svg)]()
[![Editors](https://img.shields.io/badge/editors-DaVinci%20Resolve%20%7C%20Premiere%20Pro%20%7C%20After%20Effects%20%7C%20Audition%20%7C%20Blender-purple.svg)]()
[![Tests](https://img.shields.io/badge/tests-108%20passed-brightgreen.svg)]()
[![License](https://img.shields.io/badge/license-MIT-purple.svg)](LICENSE)

---

## ⚡ 1-Click Installers Across Operating Systems

Install Xdrop for your operating system without complex setup or administrator/root prompts:

### Windows
| Installer Executable | Target Host & Extension Architecture | Status |
| :--- | :--- | :--- |
| [**`XdropSetup.exe`**](XdropSetup.exe) | **Unified Modern GUI Setup (Recommended)**<br>• Full Dark-Mode GUI with auto-detection of all editors<br>• Configures DaVinci Resolve & Adobe Creative Cloud in 1 click<br>• Sets up zero-trace, on-demand headless engine | **Ready (`14 MB`)** |
| [**`XdropInstaller-Resolve.exe`**](XdropInstaller-Resolve.exe) | **DaVinci Resolve Dedicated (Free & Studio)**<br>• Native Fusion UI Comp Script (`Xdrop.lua`)<br>• Color-Coded Starter Bin (`Xdrop - Starter Bin.drb`)<br>• Studio Workflow Integration panel | **Ready (`11 MB`)** |
| [**`XdropInstaller-Premiere.exe`**](XdropInstaller-Premiere.exe) | **Adobe Creative Cloud Dedicated (CC 2019–2026+)**<br>• Premiere Pro CEP Docked Extension (`com.xdrop.panel`)<br>• Automated `PlayerDebugMode` Registry Setup<br>• After Effects & Audition Extension Panels<br>• Modern Creative Cloud UXP Bundle (`.ccx`) | **Ready (`11 MB`)** |

### macOS
| Launcher | Target Host & Architecture | Launch Method |
| :--- | :--- | :--- |
| [**`XdropSetup.command`**](XdropSetup.command) | **Universal macOS Installer**<br>• Configures all installed editors (DaVinci Resolve, Adobe CC, Blender)<br>• Sets up background daemon LaunchAgent | Double-click in Finder or `./setup_mac.sh` |
| [**`XdropSetup-Adobe.command`**](XdropSetup-Adobe.command) | **Adobe Creative Cloud Dedicated (Premiere, AE, Audition)**<br>• Deploys CEP extension to `~/Library/Application Support/Adobe/CEP/`<br>• Configures `defaults write com.adobe.CSXS.<ver> PlayerDebugMode 1`<br>• Auto-spawns background engine from inside CEP | Double-click in Finder or `./setup_mac.sh --adobe` |
| [**`XdropSetup-Resolve.command`**](XdropSetup-Resolve.command) | **DaVinci Resolve Dedicated (Free & Studio)**<br>• Installs Lua script to `~/Library/Application Support/.../Fusion/Scripts/Comp/`<br>• Provisions starter bin and Workflow Integration panel | Double-click in Finder or `./setup_mac.sh --resolve` |

- Zero `sudo` or administrator rights required — installs entirely in user space.
- Headless auto-start engine runs silently in background.

### Linux
- **Terminal Runner**: Run `./setup_linux.sh`
- Automatically configures DaVinci Resolve (`~/.local/share/DaVinciResolve/Fusion/Scripts/Comp/`), Blender VSE (`~/.config/blender/`), and desktop autostart (`~/.config/autostart/xdrop.desktop`). No root or sudo required.

📖 **For detailed instructions and FAQs, see the [Installation Guide](src/docs/INSTALLATION_GUIDE.md).**

---

## 🎬 How to Access Xdrop in Your Editors

### 1. DaVinci Resolve (Free & Studio)
1. Double-click [**`XdropInstaller-Resolve.exe`**](XdropInstaller-Resolve.exe).
2. Launch DaVinci Resolve and open any project.
3. Open from top menu: **Workspace → Scripts → Comp → Xdrop** *(or Script → Xdrop in Fusion)*.
4. *Studio users:* You can also open the docked panel via **Workspace → Workflow Integrations → Xdrop**.
5. *Starter Bins:* Right-click your Media Pool → **Import Bin...** and choose [`src/resolve-plugin/Xdrop - Starter Bin.drb`](src/resolve-plugin/Xdrop%20-%20Starter%20Bin.drb) for pre-organized, color-coded bins (`000_Xdrop Assets`, `01_Downloads`, etc.).

### 2. Adobe Premiere Pro (CC 2019–2026+)
1. Double-click [**`XdropInstaller-Premiere.exe`**](XdropInstaller-Premiere.exe).
2. Launch Premiere Pro and open any project.
3. Open from top menu: **Window → Extensions → Xdrop**.
4. Drag and dock the panel anywhere in your workspace (alongside Project Bins, Source Monitor, or Essential Graphics).
5. Paste any link and click **Download & Import**; clips drop directly into your active project bin and playhead sequence.

### 3. Adobe After Effects & Audition
- Open from top menu: **Window → Extensions → Xdrop**.
- In **After Effects**: media automatically drops into the active project bin and composition.
- In **Audition**: audio rips drop straight into the active waveform or multitrack session.

---

## ✨ Key Features

- **Direct NLE Bin & Timeline Insertion**: Automatically imports media into your active project bin (`000_Xdrop Assets`) and drops clips at the playhead position.
- **Zero-Flicker Headless Engine**: Runs silently under `pythonw.exe` via `start_engine.vbs` with `CREATE_NO_WINDOW` flags. Zero command prompt popups or terminal flashes.
- **Ultra-Fast Remuxing & Transcoding**:
  - **Stream Copy Remuxing**: <125ms with 0% quality loss.
  - **Hardware Acceleration**: NVIDIA NVENC, Intel QuickSync, and Apple VideoToolbox support.
  - **Broadcast Audio**: 48.0 kHz 16-bit PCM WAV and 192k AAC conversion.
  - **FastStart Header**: `moov` atom placement at file start for instant timeline scrubbing.
- **Universal Provider Support**: One-click downloads from YouTube, TikTok, Instagram, Twitter/X, Reddit, Vimeo, and direct media URLs (`.mp4`, `.mov`, `.wav`, `.mp3`).
- **1-Click Auto-Update System**: Integrated GitHub updater automatically notifies users of new releases inside any video editor, silently downloads & unpacks update packages, and provisions updated extensions without manual re-installation.
- **Color-Coded Starter Bins**: Pre-configured folder hierarchy for organized video editing workflows.
- **Apple FCPXML 1.11 Sidecars**: Companion `.fcpxml` sidecars generated for universal timeline drag-and-drop.

---

## 📁 Open-Source Repository Structure

```text
Xdrop/
├── XdropSetup.exe                  # Unified Multi-Host Windows Installer (GUI + Auto-Detection)
├── XdropInstaller-Resolve.exe      # Dedicated DaVinci Resolve Windows Installer
├── XdropInstaller-Premiere.exe     # Dedicated Adobe Creative Cloud Windows Installer
├── setup.bat                       # Automated 1-Click Windows Setup (Python + Deps + Extensions)
├── run.bat                         # 1-Click Windows Launcher
├── XdropSetup.command              # Unified Multi-Host macOS Double-Click Launcher
├── XdropSetup-Resolve.command      # Dedicated DaVinci Resolve macOS Launcher
├── XdropSetup-Adobe.command        # Dedicated Adobe Creative Cloud macOS Launcher
├── setup_mac.sh                    # macOS Terminal Setup Script
├── setup_linux.sh                  # Linux Terminal Setup Script
├── run.sh                          # macOS / Linux Launcher Script
├── version.json                    # Release version & update definition
├── requirements.txt                # Python dependencies
├── LICENSE                         # MIT License
├── README.md                       # Project overview & guide
└── src/                            # Clean open-source implementation
    ├── desktop-service/            # Headless Python backend engine & queue
    ├── resolve-plugin/             # Studio UI frontend (React/Vite) & Resolve scripts
    ├── premiere-plugin/            # Adobe CEP Panel & UXP Packages
    ├── resolve-workflow-integration# DaVinci Studio Workflow Integration
    ├── blender-addon/              # Blender Sequencer Add-on
    ├── browser-extension/          # Browser Companion Extension
    ├── tools/                      # Build & packaging scripts
    ├── tests/                      # Automated test suite (108 passing tests)
    └── docs/                       # Technical documentation
```

---

## 📄 License

MIT License. Designed and built for professional video editors.
