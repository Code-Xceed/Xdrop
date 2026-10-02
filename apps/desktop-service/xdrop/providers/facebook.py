import re
from xdrop.providers.ytdlp_base import YtDlpBaseProvider

class FacebookProvider(YtDlpBaseProvider):
    """Platform provider for Facebook public video posts and reels."""

    platform_id = "facebook"
    platform_name = "Facebook"

    def can_handle(self, url: str) -> bool:
        pattern = r"(https?://)?(www\.|m\.|fb\.)?(facebook\.com/(watch|reel|.+/videos)|fb\.watch/)"
        return bool(re.search(pattern, url, re.IGNORECASE))
