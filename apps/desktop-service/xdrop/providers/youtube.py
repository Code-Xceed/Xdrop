import re
from xdrop.providers.ytdlp_base import YtDlpBaseProvider

class YouTubeProvider(YtDlpBaseProvider):
    """Platform provider for YouTube videos and shorts."""

    platform_id = "youtube"
    platform_name = "YouTube"

    def can_handle(self, url: str) -> bool:
        pattern = r"(https?://)?(www\.|m\.)?(youtube\.com/(watch\?v=|shorts/|embed/)|youtu\.be/)"
        return bool(re.search(pattern, url, re.IGNORECASE))
