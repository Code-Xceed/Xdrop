import re
from typing import Dict, Any, Optional
from xdrop.providers.ytdlp_base import YtDlpBaseProvider

class YouTubeProvider(YtDlpBaseProvider):
    """Platform provider for YouTube videos and shorts with robust 403 bypass."""

    platform_id = "youtube"
    platform_name = "YouTube"

    def can_handle(self, url: str) -> bool:
        pattern = r"(?:https?://)?(?:(?:www\.|m\.|music\.)?youtube\.com/(?:watch\?|shorts/|embed/|live/|v/|clip/)|youtu\.be/)"
        return bool(re.search(pattern, url.strip(), re.IGNORECASE))

    def _normalize_url(self, url: str) -> str:
        url = url.strip()
        if not (url.startswith("http://") or url.startswith("https://")):
            return "https://" + url
        return url

    def _get_ydl_opts(self, extra_opts: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        opts = super()._get_ydl_opts(extra_opts)
        # Allow full DASH and 4K stream extraction while preventing premature client throttling
        return opts

    def inspect(self, url: str):
        return super().inspect(self._normalize_url(url))

    def download(self, url: str, asset_id: str, output_template: str, progress_callback: Optional[Any] = None):
        return super().download(self._normalize_url(url), asset_id, output_template, progress_callback)
