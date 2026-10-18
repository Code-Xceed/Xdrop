"""
Regression tests for the two M0 showstoppers from docs/REVAMP_PLAN.md:

- W1.1  the shipped Adobe CEP manifest was malformed XML, so the panel could never load.
- W1.2  `install_premiere_extension()` referenced `sys.executable` without importing
        `sys`, so every Adobe extension install path failed with a swallowed NameError.
"""

import json
import xml.dom.minidom
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = (
    SRC_ROOT / "premiere-plugin" / "CSXS" / "manifest.xml"
    if (SRC_ROOT / "premiere-plugin").is_dir()
    else SRC_ROOT / "apps" / "premiere-plugin" / "CSXS" / "manifest.xml"
)


def test_shipped_cep_manifest_is_valid_xml():
    """W1.1 — an unclosed <Geometry> made this file unparseable and the panel invisible."""
    xml.dom.minidom.parse(str(MANIFEST_PATH))


def test_cep_manifest_has_well_formed_ui_block():
    """W1.1 — assert the specific structure that was broken, not just global parseability."""
    document = xml.dom.minidom.parse(str(MANIFEST_PATH))

    ui_elements = document.getElementsByTagName("UI")
    assert len(ui_elements) == 1, "manifest must declare exactly one <UI> block"

    ui = ui_elements[0]
    child_tags = [node.tagName for node in ui.childNodes if node.nodeType == node.ELEMENT_NODE]

    assert "Geometry" in child_tags, "<Geometry> must be a direct child of <UI>"
    assert "Icons" in child_tags, "<Icons> must be a sibling of <Geometry>, not nested inside it"

    geometry = ui.getElementsByTagName("Geometry")[0]
    geometry_children = [
        node.tagName for node in geometry.childNodes if node.nodeType == node.ELEMENT_NODE
    ]
    assert "Size" in geometry_children
    assert "MinSize" in geometry_children
    # An unclosed <Geometry> swallows later siblings; Icons must NOT be inside it.
    assert "Icons" not in geometry_children

    # The panel is useless without the PPRO and AEFT host declarations.
    host_names = {
        node.getAttribute("Name") for node in document.getElementsByTagName("Host")
    }
    assert {"PPRO", "AEFT"} <= host_names


def test_install_premiere_extension_succeeds_into_temp_appdata(tmp_path, monkeypatch):
    """W1.2 — previously returned (False, "name 'sys' is not defined")."""
    monkeypatch.setenv("APPDATA", str(tmp_path))

    from xdrop.api.routes_settings import install_premiere_extension

    success, message = install_premiere_extension()

    assert success is True, f"extension install failed: {message}"

    dest = tmp_path / "Adobe" / "CEP" / "extensions" / "com.xdrop.panel"
    assert (dest / "CSXS" / "manifest.xml").is_file()
    assert (dest / "index.html").is_file()
    assert (dest / "jsx" / "hostscript.jsx").is_file()

    config = json.loads((dest / "config.json").read_text(encoding="utf-8"))
    assert config["pythonExe"], "pythonExe must be populated (this was the swallowed NameError)"
    assert config["mainPy"].endswith("main.py")
    assert config["serviceUrl"] == "http://127.0.0.1:8484"


def test_install_premiere_extension_endpoint_returns_200(tmp_path, monkeypatch):
    """W1.2 — exercise the real HTTP interface, not just the function."""
    from fastapi.testclient import TestClient

    monkeypatch.setenv("APPDATA", str(tmp_path))

    from xdrop.main import app

    with TestClient(app) as client:
        response = client.post("/api/settings/install-premiere-extension")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True, body
    assert "com.xdrop.panel" in body["message"]
