import zipfile
from pathlib import Path
from tools.package_drb import build_xdrop_starter_drb

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_xdrop_lua_file_structure_and_syntax():
    lua_file = REPO_ROOT / "apps" / "resolve-plugin" / "Xdrop.lua"
    assert lua_file.is_file(), "apps/resolve-plugin/Xdrop.lua must exist"

    content = lua_file.read_text(encoding="utf-8")
    # Verify Fusion UIManager tokens matching Snap Captions architecture
    assert "local ui = fu.UIManager" in content
    assert "local disp = bmd.UIDispatcher(ui)" in content
    assert "local winID = \"XdropResolveWin\"" in content
    assert "disp:AddWindow" in content
    assert "disp:RunLoop()" in content
    assert "disp:ExitLoop()" in content

    # Verify DaVinci Resolve API integration tokens
    assert "projectManager = resolve" in content
    assert "mediaPool = project" in content
    assert "mediaPool:ImportMedia" in content
    assert "SetupXdropBins" in content
    assert "create_bins_btn" in content
    assert "Xdrop - Starter Bin.drb" in content


def test_xdrop_starter_drb_packaging(tmp_path):
    drb_path = tmp_path / "test_xdrop.drb"
    build_xdrop_starter_drb(drb_path)

    assert drb_path.is_file()
    assert zipfile.is_zipfile(drb_path)

    with zipfile.ZipFile(drb_path) as z:
        names = z.namelist()
        assert "project.xml" in names
        assert "MediaPool/Master/MpFolder.xml" in names
        assert "MediaPool/Master/000_Xdrop Assets/MpFolder.xml" in names
        assert "MediaPool/Master/000_Xdrop Assets/01_Downloads/MpFolder.xml" in names
        assert "MediaPool/Master/000_Xdrop Assets/02_Video Clips/MpFolder.xml" in names
        assert "MediaPool/Master/000_Xdrop Assets/03_Music & SFX/MpFolder.xml"

        # Check project.xml content
        proj_xml = z.read("project.xml").decode("utf-8")
        assert "<ProjectName>Xdrop Assets</ProjectName>" in proj_xml
        assert "Sm2MediaPool" in proj_xml

        # Check root bin XML content
        root_bin_xml = z.read("MediaPool/Master/000_Xdrop Assets/MpFolder.xml").decode("utf-8")
        assert "<Name>000_Xdrop Assets</Name>" in root_bin_xml
        assert "FOLDER_COLOR_TEAL" in root_bin_xml


def test_dist_drb_exists_and_valid():
    dist_drb = REPO_ROOT / "dist" / "Xdrop - Starter Bin.drb"
    assert dist_drb.is_file(), "dist/Xdrop - Starter Bin.drb must exist"
    assert zipfile.is_zipfile(dist_drb)
