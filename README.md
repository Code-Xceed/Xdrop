# Xdrop

> **Universal Social Media & Web Asset Importer for Video Editors**
> 
> *DaVinci Resolve • Adobe Premiere Pro • Adobe After Effects*
> 
> *Paste URL → Detect Platform → Inspect Assets → Download & Transcode → Instantly Drop into Active Editor Timelines & Bins.*

[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS-blue.svg)]()
[![Editors](https://img.shields.io/badge/editors-Resolve%20%7C%20Premiere%20%7C%20After%20Effects-purple.svg)]()
[![License](https://img.shields.io/badge/license-MIT-purple.svg)](LICENSE)

---

## 1. Overview

Video editors constantly jump between browsers, ad-heavy downloader websites, download folders, FFmpeg conversion scripts, and their NLE just to import reference clips, background music, or social media assets.

**Xdrop** eliminates this context switching by providing a native, cross-editor companion utility that runs alongside **DaVinci Resolve**, **Adobe Premiere Pro**, and **Adobe After Effects**, interfacing directly with project bins and timelines.

---

## 2. Key Features

- **Multi-Editor Integration**:
  - **DaVinci Resolve**: Directly communicates via the official `DaVinciResolveScript` API to inspect active projects and drop media into target bins (`Xdrop`). Installed under `Workspace → Scripts → Utility → Xdrop`.
  - **Adobe Premiere Pro**: Native CEP dockable panel via ExtendScript (`hostscript.jsx`), automating bin creation and media pool imports.
  - **Adobe After Effects**: Unified Adobe CEP panel targeting active compositions (`CompItem`) and project folders.
- **Auto-Detection & Smart Adapting**: Automatically senses which editor is active and adapts UI badges and action highlights (DaVinci Crimson, Premiere Cyan, After Effects Cyber-Violet).
- **Modular Provider Architecture**: Cleanly separated platform provider interfaces for **YouTube, Instagram, X (Twitter), TikTok, Reddit, Vimeo, Facebook, Pinterest**, and **Direct Media URLs** (`.mp4`, `.mov`, `.wav`, `.mp3`, `.png`, etc.).
- **Neo-Brutalist High-Density UI**: Dark, compact, responsive interface built with React 18, TypeScript, and Vite. Designed to dock down to `<340px` inside Premiere/AE or run as a standalone companion.
- **Real-Time Asynchronous Queue**: Non-blocking concurrent download engine with live speed (`MB/s`), accurate progress (`%`), and `ETA`.
- **Integrated FFmpeg Processing**: Fast remuxing, ProRes MOV / H.264 MP4 transcoding, high-fidelity WAV audio extraction, frame thumbnail capture, and proxy generation.
- **Local Asset Library**: Built-in SQLite database tracking all imported assets with search, filtering, and one-click "Import Again" or "Reveal in Explorer".
- **Project-Aware Organization**: Dynamic directory templates such as `{project}/{platform}/{mediaType}/{title}_{quality}`.

---

## 3. Architecture

```text
┌────────────────────────────────────────────────────────┐
│                   NLE Applications                     │
│  DaVinci Resolve  │  Premiere Pro  │  After Effects    │
│  (Utility Script) │   (CEP Panel)  │   (CEP Panel)     │
│                                                        │
│  ┌──────────────────────────────────────────────────┐  │
│  │                     Xdrop UI                     │  │
│  │                React + TypeScript                │  │
│  └────────────────────────┬─────────────────────────┘  │
└───────────────────────────┼────────────────────────────┘
                            │ Local HTTP / WebSocket (:8484)
                            ▼
┌────────────────────────────────────────────────────────┐
│                 Xdrop Desktop Service                  │
│                                                        │
│  ┌────────────────────┐      ┌──────────────────────┐  │
│  │  Provider Manager  │      │ Async Download Queue │  │
│  │  (YouTube, X, IG)  │      │  (Workers & SQLite)  │  │
│  └────────────────────┘      └──────────────────────┘  │
│                                                        │
│  ┌────────────────────┐      ┌──────────────────────┐  │
│  │  FFmpeg Processor  │      │ Multi-Editor Bridges │  │
│  │ (Transcode/Audio)  │      │(Resolve/Premiere/AE) │  │
│  └────────────────────┘      └──────────────────────┘  │
└───────────────────────────┬────────────────────────────┘
                            │
               ┌─────────────┴─────────────┐
               ▼                           ▼
      Local Asset Library          Editor Project Bins
    (C:/.../Xdrop Assets)          (Active Project Bin)
```

---

## 4. Quick Start (The Only File You Need)

Xdrop includes a fully automated 1-click installer that sets up everything from scratch on any computer.

### 🪟 Windows Users (Single File Setup)
1. Download or clone this repository.
2. **Double-click `setup.bat`**.

That's it! `setup.bat` will:
- ✅ Auto-install Python silently if it is not installed on your PC (no admin rights needed).
- ✅ Auto-install all required libraries and dependencies.
- ✅ Auto-detect and configure **FFmpeg** and GPU hardware acceleration.
- ✅ Auto-detect and install extensions for **DaVinci Resolve**, **Adobe Premiere Pro**, and **Adobe After Effects**.
- ✅ **Immediately launch Xdrop on your screen, 100% ready to work!**

*(To launch Xdrop in the future, simply double-click `run.bat` or `setup.bat`)*

### 🍏 macOS / Linux Users
1. Download or clone this repository.
2. Run:
   ```bash
   ./setup.sh
   ```
*(Automatically installs dependencies, configures editors, and launches Xdrop)*

---

## 5. Using Xdrop in Your Editors

Once setup is complete, Xdrop is directly integrated into your editing suites:

- **DaVinci Resolve**:
  - In Resolve's top menu bar, click: **Workspace** → **Scripts** → **Utility** → **Xdrop**.
  - Dropdowns and auto-import features drop downloaded files straight into your active project bin!
- **Adobe Premiere Pro**:
  - In Premiere's top menu bar, click: **Window** → **Extensions** → **Xdrop**.
  - The dockable CEP panel automatically syncs with Premiere's media bin.
- **Adobe After Effects**:
  - In After Effects' top menu bar, click: **Window** → **Extensions** → **Xdrop**.
  - Imported assets are automatically placed into the project panel and composition target.
- **Standalone Companion / Web Browser**:
  - Open `http://localhost:8484` in any web browser, or launch with the `--gui` flag for the floating desktop window.

---

## 6. Keeping Up-to-Date

Social media platforms (YouTube, Instagram, TikTok, etc.) frequently update their video delivery formats. If downloads ever stop working or if you want the latest features, simply **run `setup.bat` again** (or `./setup.sh`). It automatically fetches updates, upgrades extractor engines, and launches.

---

## 7. Developer Setup (Contributing)

For developers looking to customize the React UI or add platform providers:

1. **Install Dependencies**:
   ```bash
   npm install
   pip install -r requirements.txt
   ```

2. **Start Development Frontend**:
   ```bash
   npm run dev:ui
   ```

3. **Start Desktop Service**:
   ```bash
   npm run start:service   # Background headless service
   npm run start:gui       # With floating desktop window
   ```

4. **Build Production Bundle**:
   ```bash
   npm run build:ui
   ```

---

## License

MIT License — see [LICENSE](LICENSE) for details.
