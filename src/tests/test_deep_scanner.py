"""
Unit tests for the Xdrop Deep System & Editor Discovery Scanner.
"""

from pathlib import Path
from xdrop.scanner import DeepEditorScanner, DetectedEditor, get_available_drives, run_scanner


def test_get_available_drives():
    drives = get_available_drives()
    assert isinstance(drives, list)
    assert len(drives) > 0
    for drive in drives:
        assert isinstance(drive, str)


def test_deep_scanner_runs_and_reports():
    scanner = DeepEditorScanner()
    report = scanner.scan()
    assert report.total_found >= 0
    assert isinstance(report.drives_scanned, list)
    assert isinstance(report.running_processes, list)

    serialized = report.to_dict()
    assert "editors" in serialized
    assert "drivesScanned" in serialized
    assert serialized["totalFound"] == len(report.editors)


def test_upsert_editor_deduplication():
    scanner = DeepEditorScanner()
    found = {}

    scanner._upsert_editor(
        found,
        editor_id="resolve",
        name="DaVinci Resolve",
        vendor="Blackmagic Design",
        version="21.0",
        install_dir=Path("C:/test/resolve"),
        executable_path=None,
        detection_source="Registry",
        extension_type="Script",
    )
    assert "resolve" in found
    assert len(found["resolve"].detection_sources) == 1

    # Second detection with executable and studio upgrade
    scanner._upsert_editor(
        found,
        editor_id="resolve",
        name="DaVinci Resolve Studio",
        vendor="Blackmagic Design",
        version="21.0.4",
        install_dir=None,
        executable_path=Path("C:/test/resolve/Resolve.exe"),
        detection_source="Filesystem",
        extension_type="Workflow Integration",
    )

    # Must be deduplicated into one entry with merged details
    assert len(found) == 1
    item = found["resolve"]
    assert "Studio" in item.name
    assert item.version == "21.0.4"
    assert item.executable_path == Path("C:/test/resolve/Resolve.exe")
    assert item.install_dir == Path("C:/test/resolve")
    assert len(item.detection_sources) == 2
    assert "Registry" in item.detection_sources
    assert "Filesystem" in item.detection_sources
