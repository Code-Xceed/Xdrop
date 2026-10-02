# Xdrop - Install DaVinci Resolve Menu Script
$ErrorActionPreference = "Stop"

Write-Host "Installing Xdrop script to DaVinci Resolve..." -ForegroundColor Cyan

$resolveScriptsDir = "$env:PROGRAMDATA\Blackmagic Design\DaVinci Resolve\Fusion\Scripts\Utility"

if (-not (Test-Path $resolveScriptsDir)) {
    New-Item -ItemType Directory -Path $resolveScriptsDir -Force | Out-Null
}

$targetScript = Join-Path $resolveScriptsDir "Xdrop.py"
$legacyScript = Join-Path $resolveScriptsDir "ResolveFetch.py"

$pythonCode = @'
#!/usr/bin/env python
"""
Xdrop DaVinci Resolve Integration Launcher
Appears under Workspace -> Scripts -> Utility -> Xdrop
"""
import sys
import os
import webbrowser
import urllib.request
import subprocess

SERVICE_URL = "http://localhost:8484?host=resolve"

def is_service_running():
    try:
        req = urllib.request.urlopen(f"{SERVICE_URL}/api/health", timeout=1.5)
        return req.getcode() == 200
    except Exception:
        return False

def main():
    print("[Xdrop] Launching Xdrop from DaVinci Resolve...")
    if not is_service_running():
        print("[Xdrop] Starting Xdrop background service...")
        service_entry = os.getenv("XDROP_EXE") or os.getenv("RESOLVEFETCH_EXE") or "xdrop"
        try:
            subprocess.Popen([service_entry], shell=True)
        except Exception as e:
            print(f"[Xdrop] Note: {e}")

    print(f"[Xdrop] Opening user interface at: {SERVICE_URL}")
    webbrowser.open(SERVICE_URL)

if __name__ == "__main__":
    main()
'@

Set-Content -Path $targetScript -Value $pythonCode -Encoding UTF8
Set-Content -Path $legacyScript -Value $pythonCode -Encoding UTF8

Write-Host "Xdrop script successfully installed to: $targetScript" -ForegroundColor Green
Write-Host "You can now open DaVinci Resolve and find Xdrop under: Workspace -> Scripts -> Utility -> Xdrop" -ForegroundColor Yellow
