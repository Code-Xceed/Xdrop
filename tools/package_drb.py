#!/usr/bin/env python3
"""
Xdrop — DaVinci Resolve Bin (.drb) Companion Pack Generator.

Generates `Xdrop - Starter Bin.drb`, a native DaVinci Resolve Bin container that
imports a perfectly structured media organization hierarchy into DaVinci Resolve:
- 000_Xdrop Assets (Teal)
    ├── 01_Downloads (Cyan)
    ├── 02_Video Clips (Yellow)
    ├── 03_Music & SFX (Green)
    ├── 04_Dialogue & Audio (Orange)
    └── 05_Proxies & Renders (Pink)

DaVinci Resolve `.drb` files are standard ZIP containers holding:
  1. `project.xml` (Resolve project schema header)
  2. `MediaPool/Master/MpFolder.xml` (Root folder definition)
  3. `MediaPool/Master/<BinName>/MpFolder.xml` (Subfolder hierarchy)
"""

from __future__ import annotations

import sys
import uuid
import zipfile
from pathlib import Path
from typing import Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT_DIR = REPO_ROOT / "dist"
PLUGIN_OUT_DIR = REPO_ROOT / "apps" / "resolve-plugin"


def generate_guid() -> str:
    """Generates a random UUID formatted for DaVinci Resolve XML schema."""
    return str(uuid.uuid4())


def build_folder_xml(
    name: str,
    folder_id: str,
    parent_id: Optional[str] = None,
    pool_id: Optional[str] = None,
    color_tag: str = "FOLDER_COLOR_NONE",
) -> str:
    item_id = generate_guid()
    pool_tag = f" <MediaPool>{pool_id}</MediaPool>\n" if pool_id else ""
    parent_tag = f" <MpFolder>{parent_id}</MpFolder>\n" if parent_id else ""

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!--DbAppVer="19.1.1.0008" DbPrjVer="14"-->
<Sm2MpFolder DbId="{folder_id}">
 <FieldsBlob/>
 <Name>{name}</Name>
{parent_tag} <UniqueMediaPoolItemId>{item_id}</UniqueMediaPoolItemId>
 <MediaVec/>
{pool_tag} <Folded>false</Folded>
 <ColorTag>{color_tag}</ColorTag>
 <LockSysId/>
 <DbSavedTime>0</DbSavedTime>
</Sm2MpFolder>
"""


def build_project_xml(project_name: str, proj_id: str, pool_id: str, master_folder_id: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!--DbAppVer="19.1.1.0008" DbPrjVer="14"-->
<SM_Project DbId="{proj_id}">
 <ProjectName>{project_name}</ProjectName>
 <ProjectVersion>14</ProjectVersion>
 <MediaPool>
  <Sm2MediaPool DbId="{pool_id}">
   <FieldsBlob></FieldsBlob>
   <SmartFolderVec/>
   <StereoSource>2</StereoSource>
  </Sm2MediaPool>
 </MediaPool>
</SM_Project>
"""


def build_xdrop_starter_drb(output_path: Path) -> Path:
    """Builds the complete `Xdrop - Starter Bin.drb` file at `output_path`."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    proj_id = generate_guid()
    pool_id = generate_guid()
    master_id = generate_guid()
    xdrop_root_id = generate_guid()

    # Subfolders definition: (folder_name, color_tag)
    subfolders = [
        ("01_Downloads", "FOLDER_COLOR_CYAN"),
        ("02_Video Clips", "FOLDER_COLOR_YELLOW"),
        ("03_Music & SFX", "FOLDER_COLOR_GREEN"),
        ("04_Dialogue & Audio", "FOLDER_COLOR_ORANGE"),
        ("05_Proxies & Renders", "FOLDER_COLOR_PINK"),
    ]

    project_xml_str = build_project_xml("Xdrop Assets", proj_id, pool_id, master_id)
    master_xml_str = build_folder_xml("Master", master_id, pool_id=pool_id, color_tag="FOLDER_COLOR_NONE")
    xdrop_root_xml_str = build_folder_xml(
        "000_Xdrop Assets",
        xdrop_root_id,
        parent_id=master_id,
        color_tag="FOLDER_COLOR_TEAL",
    )

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        # Write project manifest
        zf.writestr("project.xml", project_xml_str)
        # Write Master bin
        zf.writestr("MediaPool/Master/MpFolder.xml", master_xml_str)
        # Write 000_Xdrop Assets root bin
        zf.writestr("MediaPool/Master/000_Xdrop Assets/MpFolder.xml", xdrop_root_xml_str)

        # Write sub-bins
        for sub_name, color in subfolders:
            sub_id = generate_guid()
            sub_xml = build_folder_xml(sub_name, sub_id, parent_id=xdrop_root_id, color_tag=color)
            arc_path = f"MediaPool/Master/000_Xdrop Assets/{sub_name}/MpFolder.xml"
            zf.writestr(arc_path, sub_xml)

    return output_path


def main():
    DEFAULT_OUT_DIR.mkdir(parents=True, exist_ok=True)
    PLUGIN_OUT_DIR.mkdir(parents=True, exist_ok=True)

    dist_file = DEFAULT_OUT_DIR / "Xdrop - Starter Bin.drb"
    plugin_file = PLUGIN_OUT_DIR / "Xdrop - Starter Bin.drb"

    build_xdrop_starter_drb(dist_file)
    build_xdrop_starter_drb(plugin_file)

    print(f"[+] Created DaVinci Resolve DRB pack: {dist_file}")
    print(f"[+] Synced to Resolve plugin directory: {plugin_file}")


if __name__ == "__main__":
    main()
