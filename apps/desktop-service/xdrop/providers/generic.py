from xdrop.providers.ytdlp_base import YtDlpBaseProvider

class GenericWebMediaProvider(YtDlpBaseProvider):
    """Fallback provider for web platforms supported by standard extractor."""

    platform_id = "generic"
    platform_name = "Web Media"

    def can_handle(self, url: str) -> bool:
        # Fallback catches valid http/https URLs not captured by others
        return url.startswith("http://") or url.startswith("https://")
