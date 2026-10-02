# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import os

block_cipher = None

project_root = Path(os.getcwd())
service_dir = project_root / "apps" / "desktop-service"
frontend_dist = project_root / "apps" / "resolve-plugin" / "dist"

datas = []
if frontend_dist.exists():
    datas.append((str(frontend_dist), "apps/resolve-plugin/dist"))

hiddenimports = [
    "uvicorn",
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "fastapi",
    "pydantic",
    "sqlite3",
    "yt_dlp",
    "pywebview",
    "httpx",
    "multiprocessing",
    "xdrop",
]

a = Analysis(
    [str(service_dir / "xdrop" / "main.py")],
    pathex=[str(service_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Xdrop",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Xdrop",
)
