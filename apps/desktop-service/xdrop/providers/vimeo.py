import re
from xdrop.providers.ytdlp_base import YtDlpBaseProvider

class VimeoProvider(YtDlpBaseProvider):
    """Platform provider for Vimeo public videos."""

    platform_id = "vimeo"
    platform_name = "Vimeo"

    def can_handle(self, url: str) -> bool:
        pattern = r"(https?://)?(www\.|player\.)?vimeo\.com/(\d+|video/\d+)"
        return bool(re.search(pattern, url, re.IGNORECASE))
