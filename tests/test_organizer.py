import pytest
from pathlib import Path
import sys
import os

# Add desktop-service to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "apps", "desktop-service")))

from xdrop.processor.organizer import MediaOrganizer, sanitize_filename_py

def test_sanitize_filename_basic():
    assert sanitize_filename_py("Normal Video Title") == "Normal Video Title"
    assert sanitize_filename_py("Title / with : invalid < chars > ?") == "Title _ with _ invalid _ chars _ _"

def test_sanitize_filename_windows_reserved():
    assert sanitize_filename_py("CON") == "CON_file"
    assert sanitize_filename_py("aux.mp4") == "aux_file.mp4"
    assert sanitize_filename_py("NUL") == "NUL_file"

def test_sanitize_filename_length_and_empty():
    assert sanitize_filename_py("") == "asset"
    assert sanitize_filename_py("   ") == "asset"
    long_name = "a" * 200
    sanitized = sanitize_filename_py(long_name)
    assert len(sanitized) <= 120

def test_organizer_path_resolution(tmp_path):
    organizer = MediaOrganizer(str(tmp_path))
    pattern = "{project}/{platform}/{mediaType}/{title}_{quality}"
    
    dest = organizer.resolve_destination(
        naming_pattern=pattern,
        project_name="MyDocumentary",
        platform="youtube",
        media_type="video",
        title="Epic B-Roll Clip",
        quality_label="1080p",
        extension="mp4"
    )

    expected_rel = Path("MyDocumentary/Youtube/Video/Epic B-Roll Clip_1080p.mp4")
    assert dest == (tmp_path / expected_rel).resolve()
    assert dest.is_relative_to(tmp_path)

def test_organizer_prevents_directory_traversal(tmp_path):
    organizer = MediaOrganizer(str(tmp_path))
    evil_pattern = "../../System32/{title}"
    
    dest = organizer.resolve_destination(
        naming_pattern=evil_pattern,
        project_name="Traitor",
        platform="youtube",
        media_type="video",
        title="malicious",
        quality_label="best",
        extension="mp4"
    )

    # Must stay inside tmp_path
    assert dest.is_relative_to(tmp_path)
