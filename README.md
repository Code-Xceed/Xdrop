# Xdrop

> **Universal Social Media & Web Asset Importer for Video Editors**
> 
> *DaVinci Resolve • Adobe Premiere Pro • Adobe After Effects*
> 
> *Paste URL → Detect Platform → Inspect Assets → Download & Transcode → Instantly Drop into Active Editor Timelines & Bins.*

[![Build & Test](https://img.shields.io/badge/tests-31%20passed-brightgreen.svg)]()
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

## 4. Quick Start

### Running the Application

1. **Install Dependencies**:
   ```bash
   npm install
   ```

2. **Launch Desktop Service**:
   ```bash
   # Run background service (default port 8484):
   npm run start:service

   # Or run with native desktop companion window:
   npm run start:gui
   ```

3. **Start Web / Plugin UI (Development)**:
   ```bash
   npm run dev:ui
   ```

4. **Build Production UI**:
   ```bash
   npm run build:ui
   ```

5. **Run Full Test Suite**:
   ```bash
   npm test
   ```

---

## License

MIT License — see [LICENSE](LICENSE) for details.
