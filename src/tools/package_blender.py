#!/usr/bin/env python3
"""
Packages and installs the Xdrop Blender VSE Addon.

Produces `dist/xdrop_blender_addon.zip` for installation via:
Blender -> Edit -> Preferences -> Add-ons -> Install...

Can also auto-install directly into discovered Blender versions on the machine.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import zipfile
from pathlib import Path
from typing import List

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = REPO_ROOT / "apps" / "blender-addon" / "xdrop_blender.py"
DEFAULT_OUT_DIR = REPO_ROOT / "dist"


def build_blender_addon_zip(
    source_file: Path = DEFAULT_SOURCE,
    out_dir: Path = DEFAULT_OUT_DIR,
) -> Path:
    """Creates an installable xdrop_blender_addon.zip file."""
    if not source_file.is_file():
        raise FileNotFoundError(f"Blender addon source not found at: {source_file}")

    out_dir.mkdir(parents=True, exist_ok=True)
    zip_path = out_dir / "xdrop_blender_addon.zip"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # Include as package folder
        zf.write(source_file, arcname="xdrop_blender/__init__.py")
        zf.write(source_file, arcname="xdrop_blender/xdrop_blender.py")

    return zip_path


def find_blender_addon_dirs() -> List[Path]:
    """Discovers Blender user scripts/addons directories across installed versions."""
    addon_dirs = []

    if sys.platform == "win32":
        blender_base = Path(os.path.expandvars(r"%APPDATA%\Blender Foundation\Blender"))
        if blender_base.is_dir():
            for version_dir in blender_base.iterdir():
                if version_dir.is_dir() and (version_dir.name[0].isdigit()):
                    addons = version_dir / "scripts" / "addons"
                    addon_dirs.append(addons)

    elif sys.platform == "darwin":
        blender_base = Path.home() / "Library" / "Application Support" / "Blender"
        if blender_base.is_dir():
            for version_dir in blender_base.iterdir():
                if version_dir.is_dir() and (version_dir.name[0].isdigit()):
                    addons = version_dir / "scripts" / "addons"
                    addon_dirs.append(addons)

    else:
        # Linux
        blender_base = Path.home() / ".config" / "blender"
        if blender_base.is_dir():
            for version_dir in blender_base.iterdir():
                if version_dir.is_dir() and (version_dir.name[0].isdigit()):
                    addons = version_dir / "scripts" / "addons"
                    addon_dirs.append(addons)

    return addon_dirs


def install_blender_addon(source_file: Path = DEFAULT_SOURCE) -> List[Path]:
    """Auto-installs the addon into all discovered Blender installations."""
    installed = []
    target_dirs = find_blender_addon_dirs()

    for addon_dir in target_dirs:
        try:
            addon_dir.mkdir(parents=True, exist_ok=True)
            target = addon_dir / "xdrop_blender.py"
            shutil.copy2(source_file, target)
            installed.append(target)
        except Exception:
            continue

    return installed


def main():
    parser = argparse.ArgumentParser(description="Package and install Xdrop Blender addon")
    parser.add_argument("--install", action="store_true", help="Auto-install to discovered Blender versions")
    args = parser.parse_args()

    zip_path = build_blender_addon_zip()
    print(f"[+] Built Blender Addon package: {zip_path}")

    if args.install:
        installed = install_blender_addon()
        if installed:
            for p in installed:
                print(f"[+] Installed directly into Blender: {p}")
        else:
            print("[i] No local Blender installation folders discovered. Package ready in dist/.")


if __name__ == "__main__":
    main()
