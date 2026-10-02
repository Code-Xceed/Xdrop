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
from xdrop.providers.ytdlp_base import YtDlpBaseProvider

def test_direct_provider_urls():
    p = DirectMediaProvider()
    assert p.can_handle("https://example.com/video.mp4")
    assert p.can_handle("https://cdn.site.org/audio.wav?token=xyz")
    assert p.can_handle("https://images.site.com/photo.png")
    assert p.can_handle("https://site.org/clip.mov")
    assert p.can_handle("https://site.org/track.mp3")
    assert p.can_handle("https://site.org/audio.flac")
    assert p.can_handle("https://site.org/audio.m4a")
    assert p.can_handle("https://site.org/image.gif")
    assert not p.can_handle("https://youtube.com/watch?v=123")

def test_youtube_urls():
    p = YouTubeProvider()
    assert p.can_handle("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert p.can_handle("https://youtu.be/dQw4w9WgXcQ")
    assert p.can_handle("https://www.youtube.com/shorts/abcd1234")
    assert p.can_handle("https://www.youtube.com/live/liveStream123")
    assert p.can_handle("https://music.youtube.com/watch?v=music123")
    assert p.can_handle("https://m.youtube.com/watch?v=mobile123")
    assert not p.can_handle("https://vimeo.com/123456")

def test_tiktok_urls():
    p = TikTokProvider()
    assert p.can_handle("https://www.tiktok.com/@creator/video/1234567890")
    assert p.can_handle("https://vm.tiktok.com/ZM8abc123/")
    assert p.can_handle("https://vt.tiktok.com/ZS8abc123/")
    assert p.can_handle("https://m.tiktok.com/v/123456.html")

def test_instagram_urls():
    p = InstagramProvider()
    assert p.can_handle("https://www.instagram.com/reel/C8xyz123abc/")
    assert p.can_handle("https://instagram.com/reels/C8xyz123abc/")
    assert p.can_handle("https://instagram.com/p/B_xyz123/")
    assert p.can_handle("https://instagram.com/tv/B_xyz123/")
    assert p.can_handle("https://instagram.com/share/reel/B_xyz123/")
    assert p.can_handle("https://instagr.am/p/short123/")

def test_x_twitter_urls():
    p = XTwitterProvider()
    assert p.can_handle("https://twitter.com/user/status/1234567890123456789")
    assert p.can_handle("https://x.com/user/status/9876543210987654321")
    assert p.can_handle("https://x.com/i/status/9876543210987654321")
    assert p.can_handle("https://mobile.twitter.com/user/status/1234567890")
    assert p.can_handle("https://t.co/xyz12345")

def test_reddit_urls():
    p = RedditProvider()
    assert p.can_handle("https://www.reddit.com/r/videos/comments/xyz123/title/")
    assert p.can_handle("https://reddit.com/r/videos/s/AbCdEf123")
    assert p.can_handle("https://v.redd.it/abcdef123456")
    assert p.can_handle("https://redd.it/xyz123")
    assert p.can_handle("https://old.reddit.com/r/funny/comments/123/funny_clip/")

def test_facebook_urls():
    p = FacebookProvider()
    assert p.can_handle("https://www.facebook.com/watch/?v=123456789")
    assert p.can_handle("https://facebook.com/reel/987654321")
    assert p.can_handle("https://facebook.com/user/videos/11223344")
    assert p.can_handle("https://facebook.com/share/r/ReelShareId123/")
    assert p.can_handle("https://fb.watch/shortFb123/")
    assert p.can_handle("https://m.facebook.com/watch/?v=987654")

def test_pinterest_urls():
    p = PinterestProvider()
    assert p.can_handle("https://www.pinterest.com/pin/123456789012345678/")
    assert p.can_handle("https://pin.it/abc1234")
    assert p.can_handle("https://pinterest.co.uk/pin/987654321/")
    assert p.can_handle("https://pinterest.ca/pin/1122334455/")

def test_vimeo_urls():
    p = VimeoProvider()
    assert p.can_handle("https://vimeo.com/123456789")
    assert p.can_handle("https://player.vimeo.com/video/123456789")
    assert p.can_handle("https://vimeo.com/channels/staffpicks/987654321")
    assert p.can_handle("https://vimeo.com/groups/motion/videos/11223344")

def test_provider_manager_routing():
    pm = get_provider_manager()
    for url, expected_id in [
        ("https://www.youtube.com/watch?v=test1234", "youtube"),
        ("https://tiktok.com/@user/video/12345", "tiktok"),
        ("https://instagram.com/reel/abc1234", "instagram"),
        ("https://x.com/user/status/123456", "x"),
        ("https://reddit.com/r/videos/comments/123", "reddit"),
        ("https://facebook.com/watch/?v=123", "facebook"),
        ("https://pin.it/abc1234", "pinterest"),
        ("https://vimeo.com/12345678", "vimeo"),
        ("https://cdn.example.org/sample.mov", "direct"),
    ]:
        prov = pm.find_provider_for_url(url)
        assert prov is not None, f"Provider missing for {url}"
        assert prov.platform_id == expected_id, f"Expected {expected_id} for {url}, got {prov.platform_id}"

def test_provider_disabling():
    pm = get_provider_manager()
    pm.set_provider_enabled("instagram", False)
    assert pm.find_provider_for_url("https://www.instagram.com/reel/123/") is not None
    pm.set_provider_enabled("instagram", True)
    assert pm.find_provider_for_url("https://www.instagram.com/reel/123/").platform_id == "instagram"

def test_ytdlp_asset_format_extraction():
    class DummyYtDlp(YtDlpBaseProvider):
        platform_id = "dummy"
        platform_name = "Dummy"
        def can_handle(self, url: str) -> bool:
            return True

    provider = DummyYtDlp()
    mock_info = {
        "title": "Sample 4K Video",
        "thumbnail": "https://example.com/thumb.jpg",
        "formats": [
            {"format_id": "137", "vcodec": "avc1", "acodec": "none", "width": 1920, "height": 1080, "fps": 30, "filesize": 50000000},
            {"format_id": "313", "vcodec": "vp9", "acodec": "none", "width": 3840, "height": 2160, "fps": 60, "filesize": 200000000},
            {"format_id": "136", "vcodec": "avc1", "acodec": "none", "width": 1280, "height": 720, "fps": 30, "filesize": 25000000},
            {"format_id": "140", "vcodec": "none", "acodec": "mp4a.40.2", "abr": 128, "filesize": 5000000},
        ]
    }

    assets = provider._extract_assets(mock_info)
    asset_ids = [a.id for a in assets]
    formats = [a.format for a in assets]
    media_types = [a.media_type for a in assets]

    # Verify 4K and 1080p video assets exist
    assert any("2160p" in a.id for a in assets)
    assert any("1080p" in a.id for a in assets)
    assert any("720p" in a.id for a in assets)

    # Verify ProRes MOV editing master asset exists
    assert "video_prores_mov" in asset_ids
    assert "mov" in formats

    # Verify audio formats exist: WAV, MP3, AAC
    assert "audio_wav" in asset_ids
    assert "wav" in formats
    assert "audio_mp3" in asset_ids
    assert "mp3" in formats
    assert "audio_aac" in asset_ids
    assert "m4a" in formats

    # Verify thumbnail asset exists
    assert "thumbnail_image" in asset_ids

def test_direct_provider_formats_inspection():
    p = DirectMediaProvider()
    video_info = p.inspect("https://example.com/media/clip.mp4")
    video_asset_ids = [a.id for a in video_info.assets]
    assert "direct_original_video" in video_asset_ids
    assert "direct_prores_mov" in video_asset_ids
    assert "direct_audio_wav" in video_asset_ids
    assert "direct_audio_mp3" in video_asset_ids
    assert "direct_audio_aac" in video_asset_ids

    audio_info = p.inspect("https://example.com/audio/song.mp3")
    audio_asset_ids = [a.id for a in audio_info.assets]
    assert "direct_original_audio" in audio_asset_ids
    assert "direct_audio_wav" in audio_asset_ids
    assert "direct_audio_aac" in audio_asset_ids
