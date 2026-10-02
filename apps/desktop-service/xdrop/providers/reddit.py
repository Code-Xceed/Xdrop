import re
from xdrop.providers.ytdlp_base import YtDlpBaseProvider

class RedditProvider(YtDlpBaseProvider):
    """Platform provider for Reddit video and post clips."""

    platform_id = "reddit"
    platform_name = "Reddit"

    def can_handle(self, url: str) -> bool:
        pattern = r"(https?://)?(www\.|old\.|new\.)?(reddit\.com/r/[^/]+/comments/|v\.redd\.it/)"
        return bool(re.search(pattern, url, re.IGNORECASE))
