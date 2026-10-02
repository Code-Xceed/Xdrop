import re
from xdrop.providers.ytdlp_base import YtDlpBaseProvider

class PinterestProvider(YtDlpBaseProvider):
    """Platform provider for Pinterest video pins."""

    platform_id = "pinterest"
    platform_name = "Pinterest"

    def can_handle(self, url: str) -> bool:
        pattern = r"(https?://)?(www\.|pin\.)?pinterest\.(com|it|de|co\.uk|ca)/pin/"
        return bool(re.search(pattern, url, re.IGNORECASE))
