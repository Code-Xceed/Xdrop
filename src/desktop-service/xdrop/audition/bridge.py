from typing import Optional

from xdrop.adobe import AdobePanelBridge


class AuditionBridge(AdobePanelBridge):
    """Bridge for Adobe Audition integration and CEP communication."""

    editor_id = "audition"
    product_name = "Adobe Audition"
    process_candidates = ("Adobe Audition.exe", "Audition.exe", "Adobe Audition", "Audition")
    process_grep = "Adobe Audition"
    import_event = "AUDITION_IMPORT_REQUEST"


_audition_bridge_instance: Optional[AuditionBridge] = None


def get_audition_bridge() -> AuditionBridge:
    global _audition_bridge_instance
    if _audition_bridge_instance is None:
        _audition_bridge_instance = AuditionBridge()
    return _audition_bridge_instance
