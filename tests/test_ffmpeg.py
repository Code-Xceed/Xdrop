import pytest
import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "apps", "desktop-service")))

from xdrop.processor import get_ffmpeg_processor

def test_ffmpeg_processor_discovery():
    processor = get_ffmpeg_processor()
    assert processor.ffmpeg_path is not None
    is_ok, info = processor.is_available()
    assert is_ok is True
    assert "ffmpeg version" in info.lower()

def test_ffmpeg_probe_invalid_file(tmp_path):
    processor = get_ffmpeg_processor()
    non_existent = tmp_path / "does_not_exist.mp4"
    info = processor.probe_media_info(str(non_existent))
    assert info["duration"] is None
    assert info["filesize"] == 0
