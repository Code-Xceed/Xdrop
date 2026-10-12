# Xdrop DaVinci Resolve Studio Workflow Integration

Native docked panel for **DaVinci Resolve Studio** (versions 17, 18, and 19+).

## Overview

Unlike the free edition of DaVinci Resolve which uses Python scripting and workspace launch menus, **DaVinci Resolve Studio** includes native support for docked Workflow Integration panels via its Electron-based plugin system.

When installed, Xdrop appears directly in the DaVinci Resolve Studio interface under:
**Workspace → Workflow Integrations → Xdrop**

## Installation Locations

DaVinci Resolve Studio automatically discovers plugins installed in:

- **Windows:**
  - Per-User (Recommended): `%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Workflow Integration Plugins\com.xdrop.resolve.workflowintegration\`
  - All Users (Admin): `%PROGRAMDATA%\Blackmagic Design\DaVinci Resolve\Support\Workflow Integration Plugins\com.xdrop.resolve.workflowintegration\`
- **macOS:**
  - Per-User: `~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Workflow Integration Plugins/com.xdrop.resolve.workflowintegration/`
  - System-wide: `/Library/Application Support/Blackmagic Design/DaVinci Resolve/Workflow Integration Plugins/com.xdrop.resolve.workflowintegration/`
- **Linux:**
  - Per-User: `~/.local/share/DaVinciResolve/Workflow Integration Plugins/com.xdrop.resolve.workflowintegration/`
  - System-wide: `/opt/resolve/Workflow Integration Plugins/com.xdrop.resolve.workflowintegration/`

## Plugin Structure

```
apps/resolve-workflow-integration/
├── manifest.xml       # DaVinci Resolve Studio plugin manifest
├── package.json       # Electron package metadata
├── main.js            # Standalone Electron runner & window config
├── index.html         # Native Resolve Studio bridge & docked web UI
└── README.md
```

## How It Works

1. **Native Bridge (`WorkflowIntegration.node`):**
   When opened inside Resolve Studio, the panel calls `WorkflowIntegration.Initialize('com.xdrop.resolve.workflowintegration')` to obtain the direct `Resolve` object.
2. **Real-time Status:**
   Displays current project name and media pool status in the header bar.
3. **Companion Service Connection:**
   Connects to the local Xdrop service (`http://127.0.0.1:2026` or `http://127.0.0.1:8484`) to handle downloads, transcodes, and bin imports automatically.
