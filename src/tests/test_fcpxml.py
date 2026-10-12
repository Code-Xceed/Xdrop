import xml.etree.ElementTree as ET
from pathlib import Path
from xdrop.processor.fcpxml import (
    generate_fcpxml_for_asset,
    write_fcpxml_sidecar,
    _frame_duration_fraction,
    _format_duration_seconds,
)


def test_frame_duration_fraction_standard_and_drop_frame():
    assert _frame_duration_fraction(29.97) == "1001/30000s"
    assert _frame_duration_fraction(23.976) == "1001/24000s"
    assert _frame_duration_fraction(59.94) == "1001/60000s"
    assert _frame_duration_fraction(30.0) == "1/30s"
    assert _frame_duration_fraction(24.0) == "1/24s"
    assert _frame_duration_fraction(60.0) == "1/60s"


def test_format_duration_seconds():
    assert _format_duration_seconds(10.0, 30.0) == "10/1s"
    assert _format_duration_seconds(0.5, 30.0) == "1/2s"
    assert _format_duration_seconds(-1.0, 30.0) == "10s"


def test_generate_fcpxml_for_video(tmp_path):
    video_file = tmp_path / "sample_video.mp4"
    video_file.write_bytes(b"\x00" * 128)

    xml_text = generate_fcpxml_for_asset(
        file_path=video_file,
        title="Sample Video Asset",
        duration_sec=15.0,
        width=1920,
        height=1080,
        fps=29.97,
    )

    # Must be valid XML
    root = ET.fromstring(xml_text)
    assert root.tag == "fcpxml"
    assert root.attrib["version"] == "1.11"

    asset = root.find(".//asset")
    assert asset is not None
    assert asset.attrib["name"] == "Sample Video Asset"
    assert asset.attrib["hasVideo"] == "1"
    assert asset.attrib["hasAudio"] == "1"

    fmt = root.find(".//format")
    assert fmt is not None
    assert fmt.attrib["frameDuration"] == "1001/30000s"
    assert fmt.attrib["width"] == "1920"
    assert fmt.attrib["height"] == "1080"

    clip = root.find(".//asset-clip")
    assert clip is not None
    assert clip.attrib["name"] == "Sample Video Asset"
    assert clip.attrib["ref"] == "r1"


def test_generate_fcpxml_for_audio(tmp_path):
    audio_file = tmp_path / "voiceover.wav"
    audio_file.write_bytes(b"\x00" * 128)

    xml_text = generate_fcpxml_for_asset(
        file_path=audio_file,
        title="Voiceover",
        duration_sec=42.0,
    )

    root = ET.fromstring(xml_text)
    assert root.tag == "fcpxml"
    asset = root.find(".//asset")
    assert asset is not None
    assert asset.attrib["hasVideo"] == "0"
    assert asset.attrib["hasAudio"] == "1"


def test_write_fcpxml_sidecar(tmp_path):
    clip = tmp_path / "interview.mov"
    clip.write_bytes(b"\x00" * 128)

    sidecar = write_fcpxml_sidecar(
        file_path=clip,
        title="Interview Clip",
        duration_sec=5.0,
    )

    assert sidecar.exists()
    assert sidecar.name == "interview.fcpxml"
    content = sidecar.read_text(encoding="utf-8")
    assert "fcpxml version=\"1.11\"" in content
    assert "Interview Clip" in content
