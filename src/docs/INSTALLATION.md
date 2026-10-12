# Xdrop Installation & Setup Guide

Xdrop provides an automated, zero-friction setup for video editors working across **DaVinci Resolve**, **Adobe Premiere Pro**, and **Adobe After Effects**.

---

## 1. Quick 1-Click Installation (End-Users)

### 🪟 Windows Setup (Standalone Executable)

1. **Double-click `XdropInstaller.exe`** (or `dist/XdropInstaller.exe`).
   - Deep-scans your PC across all local and external drives (`C:\`, `D:\`, `E:\`, `X:\`, etc.) and the Windows Registry (HKLM, HKCU, App Paths).
   - Auto-discovers every installed video editor: **DaVinci Resolve Studio & Free**, **Adobe Premiere Pro**, **Adobe After Effects**, **Adobe Audition**, **Blender**, **CapCut**, etc.
   - Automatically provisions and registers native extensions into each host editor.
   - Requires **no command line** and **no Python installation**.

*(Alternatively, run `setup.bat` for full Python environment and dependency synchronization)*

### 🍏 macOS / Linux Setup
1. Clone or download this repository.
2. In Terminal, run:
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```
*(Automatically verifies/installs Python 3, sets up dependencies, configures NLE scripts, and launches Xdrop)*

---

## 2. Accessing Xdrop in Your Editors

Once setup is complete, Xdrop is immediately available inside all your editing suites:

### 🎬 DaVinci Resolve (Free & Studio) — Native Fusion UI Lua Extension (`Xdrop.lua`)
- **Plugin Type**: Native Fusion `UIManager` Lua Plugin (matching the architecture of Snap Captions)
- **How to Open**: Top Menu → **Workspace → Scripts → Comp/Utility → Xdrop** (or inside Fusion page: **Script → Xdrop**)
- **Capabilities**:
  - Runs 100% inside DaVinci Resolve — **zero browser tabs, zero external terminals, zero electron processes**.
  - Direct Media Pool integration: dynamically fetches and selects active project bins.
  - Option to insert downloaded media directly onto the active timeline at the current playhead position.
  - One-click `+ Bins` button to auto-provision an organized `000_Xdrop Assets` bin hierarchy.

### 🎬 DaVinci Resolve Companion Starter Bin (`Xdrop - Starter Bin.drb`)
- **Format**: Native DaVinci Resolve Bin (`.drb` container)
- **Location**: `dist/Xdrop - Starter Bin.drb` (also deployed alongside `Xdrop.lua`)
- **How to Use**:
  - Double-click the `.drb` file or right-click anywhere in your DaVinci Resolve Media Pool → **Import Bin...** and choose `Xdrop - Starter Bin.drb`.
  - Instantly provisions color-coded media categories:
    - `000_Xdrop Assets` (Teal)
    - `01_Downloads` (Cyan)
    - `02_Video Clips` (Yellow)
    - `03_Music & SFX` (Green)
    - `04_Dialogue & Audio` (Orange)
    - `05_Proxies & Renders` (Pink)

### 🎬 DaVinci Resolve Studio (Native Docked Integration)
- **Plugin Type**: Blackmagic Workflow Integration (`WorkflowIntegration.node`)
- **How to Open**: Top Menu → **Workspace → Workflow Integrations → Xdrop**
- **Capabilities**: Directly docked inside the DaVinci UI. Automatically adds imported clips to your Media Pool and active timeline bin.

### 🎬 DaVinci Resolve Free & Studio (Utility Script in Desktop App Mode)
- **Plugin Type**: Native Python Utility Script launcher running in dedicated desktop app mode (zero browser tabs/address bars)
- **How to Open**: Top Menu → **Workspace → Scripts → Utility → Xdrop**
- **Capabilities**: Directly connects to the active DaVinci Resolve project via the Resolve scripting API.

### 🎞️ Adobe Premiere Pro (Native Docked Extension)
- **Plugin Type**: Adobe CEP & UXP Panel
- **How to Open**: Top Menu → **Window → Extensions → Xdrop**
- **Capabilities**: Dock the panel anywhere in your workspace (alongside Project Bins, Source Monitor, or Effects Controls). Downloads are instantly imported into your active project bin.

### 🎞️ Adobe After Effects (Native Docked Extension)
- **Plugin Type**: Adobe CEP & UXP Panel
- **How to Open**: Top Menu → **Window → Extensions → Xdrop**
- **Capabilities**: Dockable panel inside AE composition workspaces. Automatically imports downloads as project footage items.

### 🎙️ Adobe Audition (Native Docked Extension)
- **Plugin Type**: Adobe CEP Panel
- **How to Open**: Top Menu → **Window → Extensions → Xdrop**
- **Capabilities**: Dockable panel inside audio editing and multitrack workspaces. Automatically imports audio rips and music stems directly into the active session.

### 🧊 Blender (Video Sequence Editor Add-on)
- **Plugin Type**: Native Blender Add-on (`xdrop_blender_addon.zip`)
- **How to Open**: 
  1. Open the **Video Editing** workspace.
  2. Press **N** on your keyboard in the Sequencer to expand the sidebar.
  3. Click the **Xdrop** tab.
- **Manual Installation (if needed)**: Go to **Edit → Preferences → Add-ons → Install...**, choose `dist/xdrop_blender_addon.zip` in your Xdrop directory, and enable the checkbox.

### 🍏 Apple Final Cut Pro & Universal NLEs (CapCut, Sony Vegas, Avid)
- **Format**: FCPXML 1.11 Sidecar & Drag-and-Drop
- **How to Use**:
  - Every downloaded file automatically creates a companion `.fcpxml` sidecar.
  - In Final Cut Pro: **File → Import → XML...** and select the `.fcpxml` file.
  - Or simply drag-and-drop downloaded clips directly from the Xdrop UI into your timeline or media pool in any NLE.

---

## 3. Manual / Quick Extension Installer Command

If you ever need to reinstall or refresh extensions across all video editors without rerunning the full environment setup:
```cmd
python tools/install_all_extensions.py
```
This single command automatically updates DaVinci Resolve Studio workflow integrations, DaVinci utility scripts, Adobe CEP panels, Adobe UXP packages, and Blender add-ons.

---

## 3. DaVinci Resolve External Scripting Settings

In rare cases where DaVinci Resolve does not allow external Python scripts to connect:
1. Open DaVinci Resolve.
2. Go to **Preferences → General**.
3. Under **External scripting using**, ensure **Local** or **All Users** is selected.
4. Click **Save** and restart DaVinci Resolve.

---

## 4. Keeping Xdrop Up-to-Date

Social media platforms (YouTube, TikTok, Instagram, etc.) frequently update their stream delivery formats. Whenever an extractor fails or you want the latest features:
- **Windows**: Run `setup.bat` again.
- **macOS / Linux**: Run `./setup.sh` again.

This automatically updates all extractor engines, synchronizes NLE scripts, and launches Xdrop.
