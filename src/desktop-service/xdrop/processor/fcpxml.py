"""
FCPXML 1.11 interchange generator for Apple Final Cut Pro.

Generates compliant FCPXML 1.11 documents wrapping imported or downloaded assets.
Final Cut Pro users can import the generated .fcpxml file (or drag it into an FCP Event)
to immediately bring the media into their active library with correct frame rates,
aspect ratios, and media bindings.

Reference: Apple Final Cut Pro XML Format (v1.11)
"""

from __future__ import annotations

import os
from fractions import Fraction
from pathlib import Path
from typing import Optional
from xml.sax.saxutils import escape


def _frame_duration_fraction(fps: float) -> str:
    """Returns FCPXML frame duration attribute string, e.g. '1001/30000s' or '1/30s'."""
    if abs(fps - (30000 / 1001)) < 0.01 or abs(fps - 29.97) < 0.01:
        return "1001/30000s"
    if abs(fps - (24000 / 1001)) < 0.01 or abs(fps - 23.976) < 0.01 or abs(fps - 23.98) < 0.01:
        return "1001/24000s"
    if abs(fps - (60000 / 1001)) < 0.01 or abs(fps - 59.94) < 0.01:
        return "1001/60000s"
    if fps > 0:
        frac = Fraction(1, int(round(fps)))
        return f"{frac.numerator}/{frac.denominator}s"
    return "1/30s"


def _format_duration_seconds(duration_sec: float, fps: float = 30.0) -> str:
    """Formats duration in seconds to an FCPXML time value (e.g. '300/30s' or '10s')."""
    if duration_sec <= 0:
        return "10s"
    # Round to whole frame count for exact NLE conformity
    total_frames = max(1, int(round(duration_sec * fps)))
    frac = Fraction(total_frames, int(round(fps)))
    return f"{frac.numerator}/{frac.denominator}s"


def generate_fcpxml_for_asset(
    file_path: Path | str,
    title: str,
    duration_sec: Optional[float] = None,
    width: int = 1920,
    height: int = 1080,
    fps: float = 30.0,
    event_name: str = "Xdrop Imports",
) -> str:
    """Generates an FCPXML 1.11 document string referencing the media file."""
    path = Path(file_path).resolve()
    file_url = path.as_uri()

    dur_sec = duration_sec if (duration_sec and duration_sec > 0) else 10.0
    frame_dur = _frame_duration_fraction(fps)
    dur_str = _format_duration_seconds(dur_sec, fps)

    safe_title = escape(title or path.stem)
    safe_event = escape(event_name)

    is_audio = path.suffix.lower() in (".wav", ".mp3", ".aac", ".flac", ".m4a")

    if is_audio:
        media_clip = f"""                    <asset-clip name="{safe_title}" ref="r1" offset="0s" duration="{dur_str}" start="0s" />"""
    else:
        media_clip = f"""                    <asset-clip name="{safe_title}" ref="r1" offset="0s" duration="{dur_str}" start="0s" format="r2" />"""

    format_resource = "" if is_audio else f"""        <format id="r2" frameDuration="{frame_dur}" width="{width}" height="{height}" />\n"""

    xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE fcpxml>
<fcpxml version="1.11">
    <resources>
        <asset id="r1" name="{safe_title}" src="{file_url}" start="0s" duration="{dur_str}" hasAudio="1" hasVideo="{0 if is_audio else 1}" />
{format_resource}    </resources>
    <library>
        <event name="{safe_event}">
            <project name="{safe_title}">
                <sequence format="r2" duration="{dur_str}">
                    <spine>
{media_clip}
                    </spine>
                </sequence>
            </project>
        </event>
    </library>
</fcpxml>
"""
    return xml_content


def write_fcpxml_sidecar(
    file_path: Path | str,
    title: str,
    duration_sec: Optional[float] = None,
    output_xml_path: Optional[Path | str] = None,
    width: int = 1920,
    height: int = 1080,
    fps: float = 30.0,
) -> Path:
    """Writes an .fcpxml file alongside the media file and returns its path."""
    media_path = Path(file_path).resolve()
    if output_xml_path:
        out_path = Path(output_xml_path).resolve()
    else:
        out_path = media_path.with_suffix(".fcpxml")

    xml_text = generate_fcpxml_for_asset(
        file_path=media_path,
        title=title,
        duration_sec=duration_sec,
        width=width,
        height=height,
        fps=fps,
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(xml_text, encoding="utf-8")
    return out_path
