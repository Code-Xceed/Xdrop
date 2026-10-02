import os
from pathlib import Path
from fastapi import APIRouter, HTTPException
from xdrop.config import AppSettingsModel
from xdrop.database import get_settings_from_db, save_settings_to_db
from xdrop.resolve import install_resolve_script, is_resolve_script_installed
from xdrop.processor import get_ffmpeg_processor

router = APIRouter(prefix="/api/settings", tags=["Settings"])

@router.get("")
async def get_settings():
    """Retrieves current application settings."""
    db_settings = get_settings_from_db()
    settings = AppSettingsModel(**db_settings)
    d = settings.model_dump(by_alias=False)
    d.update(settings.model_dump(by_alias=True))
    return d

@router.put("")
async def update_settings(payload: dict):
    """Updates and persists application settings."""
    from xdrop.config import to_camel
    db_settings = get_settings_from_db()

    for k in list(payload.keys()):
        camel = to_camel(k)
        if camel != k and camel in payload:
            current_val = db_settings.get(k)
            if payload[k] != current_val:
                payload[camel] = payload[k]
            elif payload[camel] != current_val:
                payload[k] = payload[camel]

    new_settings = AppSettingsModel(**payload)
    save_settings_to_db(new_settings.model_dump(by_alias=False))
    d = new_settings.model_dump(by_alias=False)
    d.update(new_settings.model_dump(by_alias=True))
    return {"success": True, "settings": d}

def is_premiere_extension_installed() -> bool:
    appdata = os.getenv("APPDATA")
    if not appdata:
        return False
    manifest_new = Path(appdata) / "Adobe" / "CEP" / "extensions" / "com.xdrop.panel" / "CSXS" / "manifest.xml"
    manifest_legacy = Path(appdata) / "Adobe" / "CEP" / "extensions" / "com.xdrop.premiere" / "CSXS" / "manifest.xml"
    return manifest_new.is_file() or manifest_legacy.is_file()

def install_premiere_extension():
    import shutil
    appdata = os.getenv("APPDATA")
    if not appdata:
        return False, "APPDATA environment variable not found."
    dest_dir = Path(appdata) / "Adobe" / "CEP" / "extensions" / "com.xdrop.panel"
    legacy_dest = Path(appdata) / "Adobe" / "CEP" / "extensions" / "com.xdrop.premiere"
    
    cur = Path(__file__).resolve()
    candidates = [
        cur.parent.parent.parent.parent / "premiere-plugin",
        cur.parent.parent.parent.parent.parent / "apps" / "premiere-plugin",
        cur.parent.parent.parent / "premiere-plugin",
        Path.cwd() / "apps" / "premiere-plugin",
    ]
    src_dir = None
    for cand in candidates:
        if cand.is_dir() and (cand / "CSXS" / "manifest.xml").is_file():
            src_dir = cand
            break
            
    if not src_dir:
        return False, "Could not find premiere-plugin source directory."
        
    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src_dir, dest_dir, dirs_exist_ok=True)
        try:
            legacy_dest.mkdir(parents=True, exist_ok=True)
            shutil.copytree(src_dir, legacy_dest, dirs_exist_ok=True)
        except Exception:
            pass
        return True, f"Installed Xdrop Adobe extension to {dest_dir}"
    except Exception as e:
        return False, f"Failed to install Adobe extension: {str(e)}"

@router.get("/tools-status")
async def get_tools_status():
    """Returns availability of FFmpeg, DaVinci Resolve script, and Adobe extension."""
    db_settings = get_settings_from_db()
    current = AppSettingsModel(**db_settings)
    ffmpeg = get_ffmpeg_processor(current.ffmpeg_path)
    ff_ok, ff_info = ffmpeg.is_available()
    resolve_script_ok = is_resolve_script_installed()
    adobe_ext_ok = is_premiere_extension_installed()

    return {
        "ffmpeg": {
            "isAvailable": ff_ok,
            "path": ffmpeg.ffmpeg_path,
            "info": ff_info
        },
        "resolveScript": {
            "isInstalled": resolve_script_ok
        },
        "premiereExtension": {
            "isInstalled": adobe_ext_ok
        },
        "aftereffectsExtension": {
            "isInstalled": adobe_ext_ok
        }
    }

@router.post("/install-resolve-script")
async def trigger_install_resolve_script():
    """Installs the Xdrop launcher script into DaVinci Resolve."""
    success, msg = install_resolve_script()
    if not success:
        raise HTTPException(status_code=500, detail=msg)
    return {"success": True, "message": msg}

@router.post("/install-premiere-extension")
async def trigger_install_premiere_extension():
    """Installs the Xdrop panel extension into Adobe Premiere Pro."""
    success, msg = install_premiere_extension()
    if not success:
        raise HTTPException(status_code=500, detail=msg)
    return {"success": True, "message": msg}

@router.post("/install-aftereffects-extension")
async def trigger_install_aftereffects_extension():
    """Installs or syncs the Xdrop panel extension for Adobe After Effects."""
    success, msg = install_premiere_extension()
    if not success:
        raise HTTPException(status_code=500, detail=msg)
    return {"success": True, "message": "Synced extension for Adobe Premiere Pro & After Effects"}
