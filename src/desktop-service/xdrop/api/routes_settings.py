import subprocess
import sys
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from xdrop.config import AppSettingsModel
from xdrop.database import get_settings_from_db, save_settings_to_db
from xdrop.integrations import (
    SUPPORTED_HOSTS,
    SYSTEM_SCOPE,
    USER_SCOPE,
    cep_panel_status,
    install_integrations,
    integrations_status,
    resolve_script_status,
)
from xdrop.processor import get_ffmpeg_processor

router = APIRouter(prefix="/api/settings", tags=["Settings"])


class InstallRequest(BaseModel):
    """Body of the one-click install endpoint.

    Both fields are optional: the panel sends `{}` for "install everything, per-user, no
    admin", which is the default the product promises.
    """

    hosts: Optional[List[str]] = Field(
        default=None,
        description=f"Subset of {list(SUPPORTED_HOSTS)}. Omit to install every host.",
    )
    scope: str = Field(
        default=USER_SCOPE,
        description=(
            "'user' installs into the current user's folders and needs no administrator "
            "rights; 'system' writes shared folders and normally needs elevation."
        ),
    )


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


# --- Integrations ---------------------------------------------------------------------
#
# Installs are per-user by default, so no step here needs administrator rights and none of
# them can raise a UAC prompt. See xdrop/integrations/__init__.py for the design.


@router.get("/integrations")
async def get_integrations_status():
    """Reports every host integration: installed or not, the exact paths checked, and where
    the next install would write."""
    return integrations_status()


@router.post("/integrations/install")
async def trigger_install_integrations(request: InstallRequest = InstallRequest()):
    """Installs the requested hosts (all of them by default) for the current user.

    Returns per-host results. A failure on one host does not roll back or block the others,
    and `success` is true only when every requested host succeeded. The HTTP status stays 200
    in that case on purpose: the panel renders the per-host messages, so a 500 would hide the
    useful detail behind a single error string.
    """
    if request.scope not in (USER_SCOPE, SYSTEM_SCOPE):
        raise HTTPException(status_code=400, detail=f"Unknown scope '{request.scope}'.")

    return install_integrations(hosts=request.hosts, scope=request.scope)


@router.get("/tools-status")
async def get_tools_status():
    """Returns availability of FFmpeg, the Resolve script, and the Adobe panel.

    Kept in its original shape for the existing panel, with two additions: the Resolve entry
    now reports *which* folder matched, and the Adobe entry reports whether the hosts can
    actually load the panel (`playerDebugMode`), because files being present is not the same
    as the panel appearing in the menu.
    """
    db_settings = get_settings_from_db()
    current = AppSettingsModel(**db_settings)
    ffmpeg = get_ffmpeg_processor(current.ffmpeg_path)
    ff_ok, ff_info = ffmpeg.is_available()

    resolve = resolve_script_status()
    adobe = cep_panel_status()

    return {
        "ffmpeg": {
            "isAvailable": ff_ok,
            "path": ffmpeg.ffmpeg_path,
            "info": ff_info
        },
        "resolveScript": {
            "isInstalled": resolve["installed"],
            "path": resolve["path"],
            "scope": resolve["scope"],
            "locations": resolve["locations"],
            "notes": resolve["notes"],
        },
        "premiereExtension": {
            "isInstalled": adobe["installed"],
            "path": adobe["path"],
            "playerDebugMode": adobe["playerDebugMode"],
            "notes": adobe["notes"],
        },
        "aftereffectsExtension": {
            "isInstalled": adobe["installed"],
            "path": adobe["path"],
            "playerDebugMode": adobe["playerDebugMode"],
            "notes": adobe["notes"],
        }
    }


def install_premiere_extension() -> tuple[bool, str]:
    """Legacy wrapper: installs the shared Adobe CEP panel. Returns (ok, message)."""
    result = install_integrations(hosts=["premiere", "aftereffects"])
    adobe = next((r for r in result["results"] if r["host"] == "adobe"), None)
    if adobe is None:
        return False, result["message"]
    return bool(adobe["ok"]), str(adobe["message"])


@router.post("/install-resolve-script")
async def trigger_install_resolve_script():
    """Installs the Xdrop launcher script into DaVinci Resolve, for the current user."""
    result = install_integrations(hosts=["resolve"])
    status = result["results"][0]["ok"] if result["results"] else False
    if not status:
        detail = result["results"][0]["message"] if result["results"] else result["message"]
        raise HTTPException(status_code=500, detail=detail)
    return {"success": True, "message": result["results"][0]["message"], "status": result["status"]}


@router.post("/install-premiere-extension")
async def trigger_install_premiere_extension():
    """Installs the Xdrop panel extension for Adobe Premiere Pro (and After Effects)."""
    success, message = install_premiere_extension()
    if not success:
        raise HTTPException(status_code=500, detail=message)
    return {"success": True, "message": message, "status": integrations_status()}


@router.post("/install-aftereffects-extension")
async def trigger_install_aftereffects_extension():
    """Installs the same panel for Adobe After Effects (one CEP bundle serves both hosts)."""
    success, message = install_premiere_extension()
    if not success:
        raise HTTPException(status_code=500, detail=message)
    return {
        "success": True,
        "message": message,
        "status": integrations_status()
    }


@router.get("/system-info")
async def get_system_info():
    """Returns system diagnostic information including Python, yt-dlp, FFmpeg versions and OS."""
    import platform
    import yt_dlp

    db_settings = get_settings_from_db()
    current = AppSettingsModel(**db_settings)
    ffmpeg = get_ffmpeg_processor(current.ffmpeg_path)
    ff_ok, ff_info = ffmpeg.is_available()

    return {
        "python": {
            "version": platform.python_version(),
            "executable": sys.executable,
            "is64bit": sys.maxsize > 2**32
        },
        "ytdlp": {
            "version": getattr(yt_dlp.version, "__version__", "unknown")
        },
        "ffmpeg": {
            "isAvailable": ff_ok,
            "path": ffmpeg.ffmpeg_path,
            "info": ff_info
        },
        "os": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine()
        },
        "editors": {
            "resolveInstalled": resolve_script_status()["installed"],
            "adobeInstalled": cep_panel_status()["installed"]
        }
    }


@router.post("/update-ytdlp")
async def trigger_update_ytdlp():
    """Updates yt-dlp to the latest upstream release via pip."""
    import yt_dlp

    old_version = getattr(yt_dlp.version, "__version__", "unknown")
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"],
            capture_output=True,
            text=True,
            timeout=60.0
        )
        if proc.returncode != 0:
            return {
                "success": False,
                "error": proc.stderr or proc.stdout,
                "currentVersion": old_version
            }

        import importlib
        importlib.reload(yt_dlp)
        new_version = getattr(yt_dlp.version, "__version__", old_version)
        return {
            "success": True,
            "oldVersion": old_version,
            "newVersion": new_version,
            "message": f"yt-dlp updated successfully from {old_version} to {new_version}."
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "currentVersion": old_version
        }
