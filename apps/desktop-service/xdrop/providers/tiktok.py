import re
from xdrop.providers.ytdlp_base import YtDlpBaseProvider

class TikTokProvider(YtDlpBaseProvider):
    """Platform provider for TikTok public videos."""

    platform_id = "tiktok"
    platform_name = "TikTok"

    def can_handle(self, url: str) -> bool:
        pattern = r"(https?://)?(www\.|vm\.|vt\.)?tiktok\.com/"
        return bool(re.search(pattern, url, re.IGNORECASE))
