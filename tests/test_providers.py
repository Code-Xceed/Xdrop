import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "apps", "desktop-service")))

from xdrop.providers import get_provider_manager
from xdrop.providers.youtube import YouTubeProvider
from xdrop.providers.instagram import InstagramProvider
from xdrop.providers.x_twitter import XTwitterProvider
from xdrop.providers.tiktok import TikTokProvider
from xdrop.providers.reddit import RedditProvider
from xdrop.providers.facebook import FacebookProvider
from xdrop.providers.pinterest import PinterestProvider
from xdrop.providers.vimeo import VimeoProvider
from xdrop.providers.direct import DirectMediaProvider

def test_direct_provider_urls():
    p = DirectMediaProvider()
    assert p.can_handle("https://example.com/video.mp4")
    assert p.can_handle("https://cdn.site.org/audio.wav?token=xyz")
    assert p.can_handle("https://images.site.com/photo.png")
    assert not p.can_handle("https://youtube.com/watch?v=123")

def test_youtube_urls():
    p = YouTubeProvider()
    assert p.can_handle("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert p.can_handle("https://youtu.be/dQw4w9WgXcQ")
    assert p.can_handle("https://www.youtube.com/shorts/abcd1234")
    assert not p.can_handle("https://vimeo.com/123456")

def test_instagram_urls():
    p = InstagramProvider()
    assert p.can_handle("https://www.instagram.com/reel/C8xyz123abc/")
    assert p.can_handle("https://instagram.com/p/B_xyz123/")

def test_x_twitter_urls():
    p = XTwitterProvider()
    assert p.can_handle("https://twitter.com/user/status/1234567890123456789")
    assert p.can_handle("https://x.com/user/status/9876543210987654321")

def test_tiktok_urls():
    p = TikTokProvider()
    assert p.can_handle("https://www.tiktok.com/@creator/video/1234567890")
    assert p.can_handle("https://vm.tiktok.com/ZM8abc123/")

def test_reddit_urls():
    p = RedditProvider()
    assert p.can_handle("https://www.reddit.com/r/videos/comments/xyz123/title/")
    assert p.can_handle("https://v.redd.it/abcdef123456")

def test_vimeo_urls():
    p = VimeoProvider()
    assert p.can_handle("https://vimeo.com/123456789")

def test_pinterest_urls():
    p = PinterestProvider()
    assert p.can_handle("https://www.pinterest.com/pin/123456789012345678/")

def test_provider_manager_routing():
    pm = get_provider_manager()
    yt_prov = pm.find_provider_for_url("https://www.youtube.com/watch?v=test1234")
    assert yt_prov is not None
    assert yt_prov.platform_id == "youtube"

    direct_prov = pm.find_provider_for_url("https://cdn.example.org/sample.mov")
    assert direct_prov is not None
    assert direct_prov.platform_id == "direct"

def test_provider_disabling():
    pm = get_provider_manager()
    # Disable instagram
    pm.set_provider_enabled("instagram", False)
    assert pm.find_provider_for_url("https://www.instagram.com/reel/123/") is not None # Falls back to generic
    # Re-enable
    pm.set_provider_enabled("instagram", True)
    assert pm.find_provider_for_url("https://www.instagram.com/reel/123/").platform_id == "instagram"
