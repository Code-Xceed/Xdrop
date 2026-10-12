import re
from xdrop.providers.ytdlp_base import YtDlpBaseProvider

class InstagramProvider(YtDlpBaseProvider):
    """Platform provider for Instagram public reels and posts."""

    platform_id = "instagram"
    platform_name = "Instagram"

    def can_handle(self, url: str) -> bool:
        pattern = r"(?:https?://)?(?:(?:www\.|m\.)?instagram\.com|instagr\.am)/(?:reel|reels|p|tv|stories|share)/"
        return bool(re.search(pattern, url.strip(), re.IGNORECASE))
