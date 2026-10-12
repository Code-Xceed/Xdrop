import re
from xdrop.providers.ytdlp_base import YtDlpBaseProvider

class PinterestProvider(YtDlpBaseProvider):
    """Platform provider for Pinterest video pins."""

    platform_id = "pinterest"
    platform_name = "Pinterest"

    def can_handle(self, url: str) -> bool:
        pattern = r"(?:https?://)?(?:(?:www\.)?pinterest\.(?:com|[a-z]{2,3}(?:\.[a-z]{2})?)/pin/|pin\.it/[a-zA-Z0-9]+)"
        return bool(re.search(pattern, url.strip(), re.IGNORECASE))
