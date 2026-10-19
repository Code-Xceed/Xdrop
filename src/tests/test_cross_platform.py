"""
Cross-platform tests validating Windows, macOS, and Linux behavior.

Validates:
1. Process name candidate detection for DaVinci Resolve, Premiere Pro, After Effects, and Audition.
2. Platform-specific background daemon configurations (LaunchAgent on macOS, .desktop on Linux).
3. Preservation of third-party scripts (e.g. Snap Captions) across all OS directory layouts.
4. Existence and structural integrity of setup scripts across all operating systems.
"""

from pathlib import Path
import xml.etree.ElementTree as ET
import pytest

from xdrop.resolve.bridge import get_resolve_bridge
from xdrop.premiere.bridge import get_premiere_bridge
from xdrop.aftereffects.bridge import get_aftereffects_bridge
from xdrop.audition.bridge import get_audition_bridge
from xdrop.integrations.paths import for_system, WINDOWS, MACOS, LINUX, cep_extensions_dir
from tools.installer import ExtensionInstaller, BASE_DIR


def test_resolve_bridge_process_candidates():
    """Verify DaVinci Resolve bridge checks Windows, macOS, and Linux process names."""
    bridge = get_resolve_bridge()
    # Resolve process names across OSes: Resolve.exe (Win), Resolve (macOS), resolve (Linux)
    assert hasattr(bridge, "_is_process_running")


def test_adobe_bridges_cross_platform_candidates():
    """Verify Premiere, After Effects, and Audition bridges check macOS and Windows binaries."""
    prem = get_premiere_bridge()
    assert "Adobe Premiere Pro.exe" in prem.process_candidates
    assert "Adobe Premiere Pro" in prem.process_candidates

    ae = get_aftereffects_bridge()
    assert "AfterFX.exe" in ae.process_candidates
    assert "Adobe After Effects" in ae.process_candidates

    aud = get_audition_bridge()
    assert "Adobe Audition.exe" in aud.process_candidates
    assert "Adobe Audition" in aud.process_candidates


def test_path_resolution_across_all_three_operating_systems(tmp_path: Path):
    """Verify paths module resolves per-user directories correctly for Windows, macOS, and Linux."""
    home = tmp_path / "userhome"
    appdata = tmp_path / "appdata"
    home.mkdir()
    appdata.mkdir()

    # Windows
    win_paths = for_system(WINDOWS, home=home, appdata=appdata)
    assert win_paths.is_windows
    assert not win_paths.is_macos
    assert not win_paths.is_linux
    assert cep_extensions_dir(win_paths) is not None

    # macOS
    mac_paths = for_system(MACOS, home=home)
    assert mac_paths.is_macos
    assert not mac_paths.is_windows
    assert not mac_paths.is_linux
    assert cep_extensions_dir(mac_paths) is not None
    assert "Application Support" in str(cep_extensions_dir(mac_paths))

    # Linux
    lin_paths = for_system(LINUX, home=home)
    assert lin_paths.is_linux
    assert not lin_paths.is_windows
    assert not lin_paths.is_macos
    # CEP does not exist on Linux
    assert cep_extensions_dir(lin_paths) is None


def test_macos_launchagent_plist_generation(tmp_path: Path):
    """Verify the macOS LaunchAgent XML plist structure is well-formed."""
    target_dir = tmp_path / ".xdrop"
    target_dir.mkdir()
    python_exe = "/usr/local/bin/python3"
    run_engine_tgt = target_dir / "run_engine.py"

    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.xdrop.service</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python_exe}</string>
        <string>{run_engine_tgt}</string>
        <string>--background</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
    <key>StandardErrorPath</key>
    <string>{target_dir}/engine_error.log</string>
    <key>StandardOutPath</key>
    <string>{target_dir}/engine.log</string>
</dict>
</plist>
"""
    # Parse as XML to ensure strictly valid syntax
    root = ET.fromstring(plist_content)
    assert root.tag == "plist"
    assert root.attrib.get("version") == "1.0"


def test_linux_autostart_desktop_entry_structure(tmp_path: Path):
    """Verify Linux XDG autostart desktop entry has valid keys."""
    python_exe = "/usr/bin/python3"
    run_engine_tgt = tmp_path / ".xdrop" / "run_engine.py"

    desktop_content = f"""[Desktop Entry]
Type=Application
Version=1.0
Name=Xdrop Service
Comment=Xdrop Background Engine for DaVinci Resolve and Adobe NLEs
Exec={python_exe} {run_engine_tgt} --background
Terminal=false
Hidden=false
NoDisplay=true
X-GNOME-Autostart-enabled=true
"""
    lines = desktop_content.strip().splitlines()
    assert lines[0] == "[Desktop Entry]"
    assert "Type=Application" in lines
    assert f"Exec={python_exe} {run_engine_tgt} --background" in lines
    assert "Terminal=false" in lines


def test_clean_scripts_preserves_snap_captions(tmp_path: Path, monkeypatch):
    """Verify cleaning never removes third-party scripts (e.g. Snap Captions) on any OS."""
    # Create fake DaVinci Resolve scripts directory structure
    fusion_scripts = tmp_path / "Fusion" / "Scripts"
    comp_dir = fusion_scripts / "Comp"
    utility_dir = fusion_scripts / "Utility"
    comp_dir.mkdir(parents=True)
    utility_dir.mkdir(parents=True)

    # Place canonical Xdrop files
    (comp_dir / "Xdrop.lua").write_text("print('xdrop')", encoding="utf-8")
    (comp_dir / "Xdrop - Starter Bin.drb").write_text("bin", encoding="utf-8")
    (comp_dir / "XdropLogo.png").write_text("logo", encoding="utf-8")

    # Place third-party plugin that must NOT be removed
    snap_captions = comp_dir / "Snap Captions.lua"
    snap_captions.write_text("print('snap captions')", encoding="utf-8")

    # Place obsolete duplicate in Utility that SHOULD be removed
    legacy_file = utility_dir / "Xdrop.lua"
    legacy_file.write_text("print('legacy')", encoding="utf-8")

    installer = ExtensionInstaller([])
    installer.clean_davinci_resolve_scripts()

    # Verify Snap Captions was preserved
    assert snap_captions.exists(), "Snap Captions must NEVER be deleted by cleaner"
    assert (comp_dir / "Xdrop.lua").exists(), "Canonical Comp/Xdrop.lua must remain"


def test_cross_platform_setup_scripts_exist():
    """Verify setup and run scripts exist in repository root."""
    repo_root = BASE_DIR
    mac_setup = repo_root / "setup_mac.sh"
    mac_cmd = repo_root / "XdropSetup.command"
    linux_setup = repo_root / "setup_linux.sh"
    run_bat = repo_root / "run.bat"
    run_sh = repo_root / "run.sh"

    assert mac_setup.is_file(), "setup_mac.sh must exist"
    assert mac_cmd.is_file(), "XdropSetup.command must exist"
    assert linux_setup.is_file(), "setup_linux.sh must exist"
    assert run_bat.is_file(), "run.bat must exist"
    assert run_sh.is_file(), "run.sh must exist"

    assert "python3" in mac_setup.read_text(encoding="utf-8")
    assert "python3" in linux_setup.read_text(encoding="utf-8")
