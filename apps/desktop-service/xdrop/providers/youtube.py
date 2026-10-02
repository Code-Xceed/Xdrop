import re
from xdrop.providers.ytdlp_base import YtDlpBaseProvider

class YouTubeProvider(YtDlpBaseProvider):
    """Platform provider for YouTube videos and shorts."""

    platform_id = "youtube"
    platform_name = "YouTube"

    def can_handle(self, url: str) -> bool:
        pattern = r"(?:https?://)?(?:(?:www\.|m\.|music\.)?youtube\.com/(?:watch\?|shorts/|embed/|live/|v/|clip/)|youtu\.be/)"
        return bool(re.search(pattern, url.strip(), re.IGNORECASE))
