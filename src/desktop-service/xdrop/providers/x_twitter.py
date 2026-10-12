import re
from xdrop.providers.ytdlp_base import YtDlpBaseProvider

class XTwitterProvider(YtDlpBaseProvider):
    """Platform provider for X (Twitter) public video posts."""

    platform_id = "x"
    platform_name = "X (Twitter)"

    def can_handle(self, url: str) -> bool:
        pattern = r"(?:https?://)?(?:(?:www\.|mobile\.)?(?:twitter\.com|x\.com)/(?:[^/]+/status/\d+|i/status/\d+)|t\.co/[a-zA-Z0-9]+)"
        return bool(re.search(pattern, url.strip(), re.IGNORECASE))
