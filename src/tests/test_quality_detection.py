import pytest
from xdrop.providers.ytdlp_base import YtDlpBaseProvider
from xdrop.providers.youtube import YouTubeProvider
from xdrop.config import discover_js_runtime

class MockProvider(YtDlpBaseProvider):
    platform_id = "test_platform"
    platform_name = "Test Platform"

    def can_handle(self, url: str) -> bool:
        return "test.com" in url

def test_best_quality_auto_detected_as_default_4k():
    provider = MockProvider()
    mock_info = {
        "title": "Sample 4K Video",
        "formats": [
            {"format_id": "18", "height": 360, "width": 640, "fps": 30, "vcodec": "avc1", "acodec": "mp4a", "ext": "mp4"},
            {"format_id": "136", "height": 720, "width": 1280, "fps": 30, "vcodec": "avc1", "acodec": "none", "ext": "mp4"},
            {"format_id": "137", "height": 1080, "width": 1920, "fps": 60, "vcodec": "avc1", "acodec": "none", "ext": "mp4"},
            {"format_id": "308", "height": 1440, "width": 2560, "fps": 60, "vcodec": "vp9", "acodec": "none", "ext": "webm"},
            {"format_id": "315", "height": 2160, "width": 3840, "fps": 60, "vcodec": "vp9", "acodec": "none", "ext": "webm"},
        ]
    }
    assets = provider._extract_assets(mock_info)
    default_assets = [a for a in assets if a.is_default]
    assert len(default_assets) == 1, "Exactly one asset must be marked as default"
    default_asset = default_assets[0]
    assert "2160" in default_asset.id or "4k" in default_asset.quality_label.lower(), (
        f"Default asset must be 4K (2160p), got {default_asset.id} ({default_asset.quality_label})"
    )
    # Check that other tiers exist in assets list
    qualities = [a.quality_label for a in assets]
    assert any("4K" in q for q in qualities)
    assert any("2K" in q or "1440" in q for q in qualities)
    assert any("Full HD" in q or "1080" in q for q in qualities)
    assert any("HD" in q or "720" in q for q in qualities)
    assert any("Basic" in q or "360" in q for q in qualities)

def test_best_quality_auto_detected_when_max_is_1080p():
    provider = MockProvider()
    mock_info = {
        "title": "Sample 1080p Video",
        "formats": [
            {"format_id": "18", "height": 360, "width": 640, "fps": 30, "vcodec": "avc1", "acodec": "mp4a", "ext": "mp4"},
            {"format_id": "136", "height": 720, "width": 1280, "fps": 30, "vcodec": "avc1", "acodec": "none", "ext": "mp4"},
            {"format_id": "137", "height": 1080, "width": 1920, "fps": 60, "vcodec": "avc1", "acodec": "none", "ext": "mp4"},
        ]
    }
    assets = provider._extract_assets(mock_info)
    default_assets = [a for a in assets if a.is_default]
    assert len(default_assets) == 1
    assert "1080" in default_assets[0].id
    assert "Full HD" in default_assets[0].quality_label

def test_js_runtime_discovery():
    runtime = discover_js_runtime()
    # If node/deno/bun exists on system, it returns a dict mapping
    if runtime:
        assert isinstance(runtime, dict)
        assert any(k in ("node", "deno", "bun") for k in runtime)

def test_youtube_provider_options_clean():
    yp = YouTubeProvider()
    opts = yp._get_ydl_opts()
    extractor_args = opts.get("extractor_args", {}).get("youtube", {})
    # Ensure player_skip webpage/configs is NOT present (which causes 360p limitation)
    player_skip = extractor_args.get("player_skip", [])
    assert "webpage" not in player_skip
    assert "configs" not in player_skip
