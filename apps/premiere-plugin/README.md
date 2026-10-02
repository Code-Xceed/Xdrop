# Xdrop for Adobe Premiere Pro & Adobe After Effects

This package is the unified Adobe CEP (Common Extensibility Platform) panel extension for **Adobe Premiere Pro** and **Adobe After Effects**.

It docks directly inside Premiere Pro and After Effects workspaces (**Window → Extensions → Xdrop**) and automatically imports downloaded media into your active project bin or folder.

---

## 1. Directory Structure

```text
apps/premiere-plugin/
├── CSXS/
│   └── manifest.xml       # Adobe CEP Extension Manifest (PPRO + AEFT)
├── jsx/
│   └── hostscript.jsx     # ExtendScript for Premiere Pro & After Effects project & bin importing
├── js/
│   └── CSInterface.js     # Adobe CEP bridge library
├── index.html             # Panel interface with WebSocket auto-import listener & status sync
└── README.md
```

---

## 2. Installation for Premiere Pro & After Effects

Run the automated installer script:
```powershell
powershell -ExecutionPolicy Bypass -File scripts\install-premiere-plugin.ps1
```

Or double-click `scripts\install-premiere-plugin.bat`.

This script:
1. Copies `apps/premiere-plugin` into `%APPDATA%\Adobe\CEP\extensions\com.xdrop.panel`.
2. Sets `PlayerDebugMode=1` in the Windows Registry (`HKCU\Software\Adobe\CSXS.*`) so Premiere Pro and After Effects load custom local extensions.

---

## 3. How to Use in Premiere Pro & After Effects

1. Start the Xdrop background engine (`npm run start:service` or `Xdrop.exe`).
2. Open **Adobe Premiere Pro** or **Adobe After Effects**.
3. Go to the top menu: **Window → Extensions → Xdrop**.
4. The Xdrop panel appears docked alongside your Project/Source/Composition windows.
5. Paste any supported URL (YouTube, Instagram, TikTok, X, Reddit, Pinterest, Vimeo, etc.) and click **Download**.
6. When the download finishes, ExtendScript immediately creates an `"Xdrop"` bin/folder (if not already existing) and imports the file directly into your active project!

