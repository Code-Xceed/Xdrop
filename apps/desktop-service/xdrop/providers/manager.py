from typing import List, Optional, Dict, Any
from xdrop.providers.base import PlatformProvider, MediaInfoModel
from xdrop.providers.direct import DirectMediaProvider
from xdrop.providers.youtube import YouTubeProvider
from xdrop.providers.instagram import InstagramProvider
from xdrop.providers.x_twitter import XTwitterProvider
from xdrop.providers.reddit import RedditProvider
from xdrop.providers.tiktok import TikTokProvider
from xdrop.providers.facebook import FacebookProvider
from xdrop.providers.pinterest import PinterestProvider
from xdrop.providers.vimeo import VimeoProvider
from xdrop.providers.generic import GenericWebMediaProvider
from xdrop.logger import app_logger, errors_logger

class ProviderManager:
    """Manages platform providers, URL detection, routing, and lifecycle."""

    def __init__(self):
        self._providers: List[PlatformProvider] = []
        self._register_default_providers()

    def _register_default_providers(self) -> None:
        # Direct file extension check runs first for speed and certainty
        self._providers.append(DirectMediaProvider())
        # Specific social media platform providers
        self._providers.append(YouTubeProvider())
        self._providers.append(InstagramProvider())
        self._providers.append(XTwitterProvider())
        self._providers.append(RedditProvider())
        self._providers.append(TikTokProvider())
        self._providers.append(FacebookProvider())
        self._providers.append(PinterestProvider())
        self._providers.append(VimeoProvider())
        # Generic fallback
        self._providers.append(GenericWebMediaProvider())

    def get_providers(self) -> List[PlatformProvider]:
        return self._providers

    def get_provider_by_id(self, platform_id: str) -> Optional[PlatformProvider]:
        for p in self._providers:
            if p.platform_id == platform_id:
                return p
        return None

    def find_provider_for_url(self, url: str) -> Optional[PlatformProvider]:
        """Finds the first enabled provider capable of handling the URL."""
        clean_url = url.strip()
        for provider in self._providers:
            if provider.enabled and provider.can_handle(clean_url):
                return provider
        return None

    def inspect_url(self, url: str) -> MediaInfoModel:
        """Inspects media URL using the matching provider."""
        provider = self.find_provider_for_url(url)
        if not provider:
            raise ValueError(f"No compatible provider found for URL: {url}")
        app_logger.info(f"Inspecting URL using provider '{provider.platform_name}': {url}")
        return provider.inspect(url)

    def set_provider_enabled(self, platform_id: str, enabled: bool) -> bool:
        provider = self.get_provider_by_id(platform_id)
        if provider:
            provider.enabled = enabled
            return True
        return False

_manager_instance: Optional[ProviderManager] = None

def get_provider_manager() -> ProviderManager:
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = ProviderManager()
    return _manager_instance
