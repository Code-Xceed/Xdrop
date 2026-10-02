import os
import subprocess
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from xdrop.database import get_library_items, delete_library_item, get_db_connection
from xdrop.resolve import get_resolve_bridge
from xdrop.logger import app_logger

router = APIRouter(prefix="/api/library", tags=["Library"])

@router.get("")
async def list_library_assets(
    search: Optional[str] = Query(None),
    platform: Optional[str] = Query(None),
    media_type: Optional[str] = Query(None),
    resolve_imported: Optional[bool] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Retrieves previous downloaded assets with search and filtering."""
    items = get_library_items(
        search=search,
        platform=platform,
        media_type=media_type,
        resolve_imported=resolve_imported,
        limit=limit,
        offset=offset,
    )
    return items

@router.delete("/{asset_id}")
async def remove_library_asset(asset_id: str, delete_file: bool = Query(False)):
    """Deletes an asset record from database and optionally deletes disk file."""
    items = get_library_items(limit=1000)
    asset = next((a for a in items if a["id"] == asset_id), None)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found.")

    if delete_file:
        file_path = Path(asset["file_path"])
        if file_path.exists():
            try:
                file_path.unlink()
                app_logger.info(f"Deleted file from disk: {file_path}")
            except Exception as e:
                app_logger.warning(f"Failed to delete file from disk: {e}")

    success = delete_library_item(asset_id)
    return {"success": success, "id": asset_id}

@router.post("/{asset_id}/import")
async def import_library_asset(asset_id: str, target_bin: str = Query("Xdrop")):
    """Imports an existing library asset file into DaVinci Resolve."""
    items = get_library_items(limit=1000)
    asset = next((a for a in items if a["id"] == asset_id), None)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found.")

    file_path = asset["file_path"]
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=400, detail=f"File does not exist on disk: {file_path}")

    bridge = get_resolve_bridge()
    res = bridge.import_media([file_path], target_bin)

    if res.get("success"):
        with get_db_connection() as conn:
            conn.execute("UPDATE assets SET resolve_imported = 1 WHERE id = ?", (asset_id,))

    return res

@router.post("/{asset_id}/import-premiere")
async def import_library_asset_to_premiere(asset_id: str, target_bin: str = Query("Xdrop")):
    """Imports an existing library asset file into Adobe Premiere Pro."""
    from xdrop.premiere.bridge import get_premiere_bridge
    items = get_library_items(limit=1000)
    asset = next((a for a in items if a["id"] == asset_id), None)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found.")

    file_path = asset["file_path"]
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=400, detail=f"File does not exist on disk: {file_path}")

    bridge = get_premiere_bridge()
    res = await bridge.import_media_async(file_path, target_bin)

    if res.get("success"):
        with get_db_connection() as conn:
            conn.execute("UPDATE assets SET premiere_imported = 1 WHERE id = ?", (asset_id,))

    return res

@router.post("/{asset_id}/import-aftereffects")
async def import_library_asset_to_aftereffects(asset_id: str, target_bin: str = Query("Xdrop")):
    """Imports an existing library asset file into Adobe After Effects."""
    from xdrop.aftereffects.bridge import get_aftereffects_bridge
    items = get_library_items(limit=1000)
    asset = next((a for a in items if a["id"] == asset_id), None)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found.")

    file_path = asset["file_path"]
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=400, detail=f"File does not exist on disk: {file_path}")

    bridge = get_aftereffects_bridge()
    res = await bridge.import_media_async(file_path, target_bin)

    if res.get("success"):
        with get_db_connection() as conn:
            conn.execute("UPDATE assets SET aftereffects_imported = 1 WHERE id = ?", (asset_id,))

    return res

@router.post("/{asset_id}/reveal")
async def reveal_asset_in_explorer(asset_id: str):
    """Opens Windows Explorer highlighting the asset file."""
    items = get_library_items(limit=1000)
    asset = next((a for a in items if a["id"] == asset_id), None)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found.")

    file_path = Path(asset["file_path"]).resolve()
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found on disk: {file_path}")

    try:
        if os.name == "nt":
            subprocess.Popen(["explorer.exe", f"/select,{str(file_path)}"])
        else:
            subprocess.Popen(["xdg-open", str(file_path.parent)])
        return {"success": True, "message": "Revealed file in file explorer."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to open explorer: {e}")
