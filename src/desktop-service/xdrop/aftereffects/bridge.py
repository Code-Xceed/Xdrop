from typing import Optional

from xdrop.adobe import AdobePanelBridge


class AfterEffectsBridge(AdobePanelBridge):
    """Bridge for Adobe After Effects integration and CEP communication."""

    editor_id = "aftereffects"
    product_name = "Adobe After Effects"
    # After Effects ships as AfterFX.exe on Windows; on macOS it runs as After Effects or Adobe After Effects.
    process_candidates = ("AfterFX.exe", "After Effects.exe", "Adobe After Effects", "After Effects")
    process_grep = "After Effects"
    import_event = "AFTEREFFECTS_IMPORT_REQUEST"


_aftereffects_bridge_instance: Optional[AfterEffectsBridge] = None


def get_aftereffects_bridge() -> AfterEffectsBridge:
    global _aftereffects_bridge_instance
    if _aftereffects_bridge_instance is None:
        _aftereffects_bridge_instance = AfterEffectsBridge()
    return _aftereffects_bridge_instance
