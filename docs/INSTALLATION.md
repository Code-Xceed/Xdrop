# Xdrop Installation & Setup Guide

Xdrop provides an automated, zero-friction setup for video editors working across **DaVinci Resolve**, **Adobe Premiere Pro**, and **Adobe After Effects**.

---

## 1. Quick 1-Click Installation (End-Users)

### 🪟 Windows Setup
1. Clone or download this repository:
   ```cmd
   git clone https://github.com/Code-Xceed/Xdrop.git
   cd Xdrop
   ```
2. **Double-click `setup.bat`**.

That's all! `setup.bat` automatically:
- Checks for Python 3.9+ and silently installs official Python if missing (no admin rights required).
- Installs all Python dependencies.
- Embeds the pre-compiled UI bundle (no Node.js/npm required for end users).
- Detects or downloads portable FFmpeg.
- Probes GPU acceleration (NVIDIA NVENC, QuickSync, Apple ProRes).
- Detects installed editors and installs:
  - **DaVinci Resolve Utility Script**: `C:\ProgramData\Blackmagic Design\DaVinci Resolve\Fusion\Scripts\Utility\Xdrop.py`
  - **Adobe CEP Panel**: `%APPDATA%\Adobe\CEP\extensions\com.xdrop.panel`
  - **Adobe Registry Keys**: Enables `PlayerDebugMode=1` across CSXS versions 9–16.
- Configures default media directories (`Videos/Xdrop Assets`).
- Immediately launches Xdrop ready to work!

*(To launch Xdrop in the future, double-click `run.bat` or `setup.bat`)*

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

Once setup is complete, Xdrop is immediately available inside your editing suites:

### DaVinci Resolve
1. Open DaVinci Resolve and open any project.
2. Go to the top menu: **Workspace → Scripts → Utility → Xdrop**.
3. The Xdrop companion window opens, directly synced to your active project bin (`Xdrop`).

### Adobe Premiere Pro
1. Open Adobe Premiere Pro.
2. Go to the top menu: **Window → Extensions → Xdrop**.
3. Dock the panel anywhere in your workspace (alongside Project Bins, Source Monitor, etc.).
4. Downloaded assets automatically appear in the active project bin!

### Adobe After Effects
1. Open Adobe After Effects.
2. Go to the top menu: **Window → Extensions → Xdrop**.
3. Dock the panel in your workspace; media imports directly into the project panel.

### Standalone Companion / Web Browser
- Launch the floating desktop companion: `run.bat` or `python apps/desktop-service/xdrop/main.py --gui`
- Or open in any web browser: `http://localhost:8484`

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
