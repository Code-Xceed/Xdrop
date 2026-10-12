from typing import Optional

from xdrop.adobe import AdobePanelBridge


class PremiereBridge(AdobePanelBridge):
    """Bridge for Adobe Premiere Pro integration and CEP communication."""

    editor_id = "premiere"
    product_name = "Adobe Premiere Pro"
    process_candidates = ("Adobe Premiere Pro.exe",)
    process_grep = "Adobe Premiere Pro"
    import_event = "PREMIERE_IMPORT_REQUEST"


_premiere_bridge_instance: Optional[PremiereBridge] = None


def get_premiere_bridge() -> PremiereBridge:
    global _premiere_bridge_instance
    if _premiere_bridge_instance is None:
        _premiere_bridge_instance = PremiereBridge()
    return _premiere_bridge_instance
