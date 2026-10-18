import json
import xml.etree.ElementTree as ET
from pathlib import Path


def _get_studio_dir() -> Path:
    base = Path(__file__).resolve().parents[1]
    if (base / "resolve-workflow-integration").is_dir():
        return base / "resolve-workflow-integration"
    return base / "apps" / "resolve-workflow-integration"


def test_resolve_studio_manifest_is_valid_xml():
    manifest_path = _get_studio_dir() / "manifest.xml"
    assert manifest_path.is_file(), f"Expected manifest at {manifest_path}"

    tree = ET.parse(manifest_path)
    root = tree.getroot()
    assert root.tag in ("BlackmagicDesign", "Plugin")

    name = root.find(".//Name")
    assert name is not None and name.text == "Xdrop"

    plugin_id = root.find(".//Id")
    if plugin_id is None:
        plugin_id = root.find(".//ID")
    assert plugin_id is not None and plugin_id.text == "com.xdrop.resolve.workflowintegration"

    main_file = root.find(".//FilePath")
    if main_file is None:
        main_file = root.find(".//MainFile")
    assert main_file is not None and main_file.text in ("main.js", "index.html")


def test_resolve_studio_package_json():
    pkg_path = _get_studio_dir() / "package.json"
    assert pkg_path.is_file()

    data = json.loads(pkg_path.read_text(encoding="utf-8"))
    assert data["name"] == "com.xdrop.resolve.workflowintegration"
    assert data["main"] == "main.js"


def test_resolve_studio_index_html_has_bridge_and_fallback():
    index_path = _get_studio_dir() / "index.html"
    assert index_path.is_file()

    content = index_path.read_text(encoding="utf-8")
    assert "com.xdrop.resolve.workflowintegration" in content
    assert "WorkflowIntegration" in content
    assert "importMediaToActiveProject" in content
    assert "checkConnection" in content
