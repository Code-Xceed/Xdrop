from fastapi import APIRouter
from xdrop.resolve import get_resolve_bridge
from xdrop.premiere import get_premiere_bridge
from xdrop.aftereffects import get_aftereffects_bridge
from xdrop.database import get_settings_from_db

router = APIRouter(prefix="/api/editors", tags=["Editors"])

@router.get("/status")
async def get_editors_status():
    """Returns combined status of all supported video editing suites (DaVinci Resolve, Premiere Pro & After Effects)."""
    resolve_bridge = get_resolve_bridge()
    premiere_bridge = get_premiere_bridge()
    aftereffects_bridge = get_aftereffects_bridge()

    res_status = resolve_bridge.get_status()
    prem_status = premiere_bridge.get_status()
    ae_status = aftereffects_bridge.get_status()

    db_settings = get_settings_from_db()
    configured_default = db_settings.get("default_editor", "auto")

    # Determine currently active editor
    active_editor = "none"
    if configured_default == "aftereffects" and ae_status.get("isAvailable"):
        active_editor = "aftereffects"
    elif configured_default == "premiere" and prem_status.get("isAvailable"):
        active_editor = "premiere"
    elif configured_default == "resolve" and res_status.get("isAvailable"):
        active_editor = "resolve"
    else:
        # Auto-detection priority based on recent heartbeats / availability
        available_editors = []
        if ae_status.get("isAvailable"):
            available_editors.append(("aftereffects", aftereffects_bridge._last_heartbeat_time))
        if prem_status.get("isAvailable"):
            available_editors.append(("premiere", premiere_bridge._last_heartbeat_time))
        if res_status.get("isAvailable"):
            available_editors.append(("resolve", None))

        if not available_editors:
            active_editor = "none"
        elif len(available_editors) == 1:
            active_editor = available_editors[0][0]
        else:
            sorted_eds = sorted(available_editors, key=lambda x: x[1].timestamp() if x[1] else 0, reverse=True)
            active_editor = sorted_eds[0][0]

    return {
        "activeEditor": active_editor,
        "resolve": res_status,
        "premiere": prem_status,
        "aftereffects": ae_status
    }
