import re
from xdrop.providers.ytdlp_base import YtDlpBaseProvider

class XTwitterProvider(YtDlpBaseProvider):
    """Platform provider for X (Twitter) public video posts."""

    platform_id = "x"
    platform_name = "X (Twitter)"

    def can_handle(self, url: str) -> bool:
        pattern = r"(https?://)?(www\.)?(twitter\.com|x\.com)/[^/]+/status/\d+"
        return bool(re.search(pattern, url, re.IGNORECASE))
