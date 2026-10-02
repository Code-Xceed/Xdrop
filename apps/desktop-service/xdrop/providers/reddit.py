import re
from xdrop.providers.ytdlp_base import YtDlpBaseProvider

class RedditProvider(YtDlpBaseProvider):
    """Platform provider for Reddit video and post clips."""

    platform_id = "reddit"
    platform_name = "Reddit"

    def can_handle(self, url: str) -> bool:
        pattern = r"(?:https?://)?(?:(?:www\.|old\.|new\.|m\.)?reddit\.com/(?:r/[^/]+/(?:comments|s)/|clip/)|v\.redd\.it/[a-zA-Z0-9]+|redd\.it/[a-zA-Z0-9]+)"
        return bool(re.search(pattern, url.strip(), re.IGNORECASE))
