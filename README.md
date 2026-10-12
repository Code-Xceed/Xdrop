# Xdrop

> **Universal High-Performance Media Importer for Video Editors**  
> *DaVinci Resolve • Adobe Premiere Pro • Adobe After Effects • Adobe Audition*  
>  
> *Paste URL → Detect Platform → Inspect Quality → Download & Transcode → Instantly Drop into Timelines & Bins.*

[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS-blue.svg)]()
[![Editors](https://img.shields.io/badge/editors-DaVinci%20Resolve%20%7C%20Premiere%20Pro%20%7C%20After%20Effects-purple.svg)]()
[![Tests](https://img.shields.io/badge/tests-88%20passed-brightgreen.svg)]()
[![License](https://img.shields.io/badge/license-MIT-purple.svg)](LICENSE)

---

## ⚡ 1-Click Standalone Installers

Xdrop provides dedicated standalone executables tailored to each editor's extension architecture. **No Python, Git, or command-line setup is required.**

| Installer Executable | Target Host & Extension Architecture | Status |
| :--- | :--- | :--- |
| [**`XdropInstaller-Resolve.exe`**](XdropInstaller-Resolve.exe) | **DaVinci Resolve (Free & Studio)**<br>• Native Fusion UI Comp Script (`Xdrop.lua`)<br>• Color-Coded Starter Bin (`Xdrop - Starter Bin.drb`)<br>• Studio Workflow Integration panel | **Ready (`11 MB`)** |
| [**`XdropInstaller-Premiere.exe`**](XdropInstaller-Premiere.exe) | **Adobe Creative Cloud (CC 2019–2026+)**<br>• Premiere Pro CEP Docked Extension (`com.xdrop.panel`)<br>• Automated `PlayerDebugMode` Registry Setup<br>• After Effects & Audition Extension Panels<br>• Modern Creative Cloud UXP Bundle (`.ccx`) | **Ready (`11 MB`)** |
| [**`XdropInstaller.exe`**](XdropInstaller.exe) | **Universal Master Installer**<br>• Full system scanner provisioning all detected editors in 1 click | **Ready (`11 MB`)** |

📖 **For detailed instructions and FAQs, see the complete [Installation & User Guide](docs/INSTALLATION_GUIDE.md).**

---

## 🎬 How to Access Xdrop in Your Editors

### 1. DaVinci Resolve (Free & Studio)
1. Run [`XdropInstaller-Resolve.exe`](XdropInstaller-Resolve.exe).
2. Launch DaVinci Resolve and open any project.
3. Open from top menu: **Workspace → Scripts → Comp → Xdrop** *(or Script → Xdrop in Fusion)*.
4. *Studio users:* You can also open the docked panel via **Workspace → Workflow Integrations → Xdrop**.
5. *Starter Bins:* Right-click your Media Pool → **Import Bin...** and choose [`dist/Xdrop - Starter Bin.drb`](dist/Xdrop%20-%20Starter%20Bin.drb) for pre-organized, color-coded bins (`000_Xdrop Assets`, `01_Downloads`, etc.).

### 2. Adobe Premiere Pro (CC 2019–2026+)
1. Run [`XdropInstaller-Premiere.exe`](XdropInstaller-Premiere.exe).
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
- **Color-Coded Starter Bins**: Pre-configured folder hierarchy for organized video editing workflows.
- **Apple FCPXML 1.11 Sidecars**: Companion `.fcpxml` sidecars generated for universal timeline drag-and-drop.

---

## 🛠️ Developer Setup & Script Automation

If you prefer building or running from source:

### Windows:
```cmd
setup.bat
```
*(Automatically verifies Python, installs dependencies, configures editor extensions, and starts the service)*

### macOS / Linux:
```bash
chmod +x setup.sh
./setup.sh
```

### Running the Test Suite:
```bash
python -m pytest -q
```
*(Runs all 88 unit, integration, packaging, and installer tests)*

### Running the Performance Benchmark:
```bash
python tools/benchmark_media_pipeline.py
```

---

## 📁 Repository Structure

```text
Xdrop/
├── XdropInstaller-Resolve.exe      # Standalone installer for DaVinci Resolve
├── XdropInstaller-Premiere.exe     # Standalone installer for Adobe Creative Cloud
├── XdropInstaller.exe              # Universal multi-editor master installer
├── setup.bat                       # Automated 1-click developer setup
├── start_engine.vbs                # Silent zero-flicker background engine launcher
├── apps/
│   ├── desktop-service/            # FastAPI background engine & download queue
│   ├── resolve-plugin/             # Native DaVinci Resolve Lua UI (Xdrop.lua) & UI
│   ├── resolve-workflow-integration# Studio Workflow Integration docked panel
│   ├── premiere-plugin/            # Adobe CEP panel & modern UXP CCX package
│   ├── blender-addon/              # Blender Sequencer Add-on
│   └── browser-extension/          # Companion browser extension
├── dist/                           # Production builds, DRB starter bins & CCX packages
├── docs/                           # Full guides (INSTALLATION_GUIDE.md, API.md, etc.)
├── tests/                          # Automated test suite (88 passing tests)
└── tools/                          # Packaging, benchmarking, and installer source scripts
```

---

## 📄 License

MIT License. Designed and built for professional video editors.
