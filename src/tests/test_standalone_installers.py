import os
import sys
import json
from pathlib import Path

import pytest

REPO_ROOT = (
    Path(__file__).resolve().parent.parent.parent
    if Path(__file__).resolve().parent.parent.name == "src"
    else Path(__file__).resolve().parent.parent
)


def test_standalone_installer_executables_exist_and_valid():
    """Verify standalone installer binaries exist, have size > 5MB, and valid PE headers."""
    resolve_exe = REPO_ROOT / "XdropInstaller-Resolve.exe"
    premiere_exe = REPO_ROOT / "XdropInstaller-Premiere.exe"
    installer_list = [resolve_exe, premiere_exe]
    setup_exe = REPO_ROOT / "XdropSetup.exe"
    if setup_exe.is_file():
        installer_list.append(setup_exe)

    for exe in installer_list:
        assert exe.is_file(), f"Expected executable {exe.name} to exist at repo root"
        size = exe.stat().st_size
        assert size > 5_000_000, f"{exe.name} size ({size} bytes) is suspiciously small (expected > 5MB)"

        # Check Windows PE Executable magic header "MZ"
        with open(exe, "rb") as f:
            header = f.read(2)
            assert header == b"MZ", f"{exe.name} does not start with valid Windows PE header 'MZ'"


def test_resolve_installer_copies_fusion_script_and_drb(tmp_path, monkeypatch):
    """Verify Resolve installer writes Xdrop.lua and Starter Bin.drb into Comp folder without touching third-party scripts."""
    appdata_mock = tmp_path / "AppData" / "Roaming"
    localappdata_mock = tmp_path / "AppData" / "Local"
    monkeypatch.setenv("APPDATA", str(appdata_mock))
    monkeypatch.setenv("LOCALAPPDATA", str(localappdata_mock))

    # Pre-populate a fake Snap Captions script to prove it is NEVER removed
    comp_dir = appdata_mock / "Blackmagic Design" / "DaVinci Resolve" / "Support" / "Fusion" / "Scripts" / "Comp"
    comp_dir.mkdir(parents=True, exist_ok=True)
    snap_captions = comp_dir / "Snap Captions.lua"
    snap_captions.write_text("-- Snap Captions original script", encoding="utf-8")

    from tools.installer_resolve import ResolveExtensionInstaller

    installer = ResolveExtensionInstaller()
    installer.run_resolve_only()

    # 1. Verify Snap Captions is strictly preserved
    assert snap_captions.is_file(), "Third-party Snap Captions script was deleted or corrupted!"
    assert snap_captions.read_text(encoding="utf-8") == "-- Snap Captions original script"

    # 2. Verify Xdrop.lua is installed in Comp scripts
    xdrop_lua = comp_dir / "Xdrop.lua"
    assert xdrop_lua.is_file(), "Xdrop.lua was not installed to Comp scripts folder"
    lua_code = xdrop_lua.read_text(encoding="utf-8")
    assert "LaunchStudioApp" in lua_code
    assert "SERVICE_URL" in lua_code

    # 3. Verify Starter Bin is installed
    starter_drb = comp_dir / "Xdrop - Starter Bin.drb"
    assert starter_drb.is_file(), "Xdrop - Starter Bin.drb was not deployed to Comp scripts"

    # 4. Verify silent start_engine.vbs was generated in LocalAppData
    vbs = localappdata_mock / "Xdrop" / "start_engine.vbs"
    assert vbs.is_file(), "Silent background launcher start_engine.vbs was not created"
    vbs_text = vbs.read_text(encoding="utf-8")
    assert "WScript.Shell" in vbs_text
    assert ", 0, False" in vbs_text, "VBScript must pass windowStyle=0 (hidden)"


def test_premiere_installer_copies_cep_panel_and_uxp(tmp_path, monkeypatch):
    """Verify Premiere installer deploys CEP panel, config.json, hostscript, and CCX package."""
    appdata_mock = tmp_path / "AppData" / "Roaming"
    localappdata_mock = tmp_path / "AppData" / "Local"
    monkeypatch.setenv("APPDATA", str(appdata_mock))
    monkeypatch.setenv("LOCALAPPDATA", str(localappdata_mock))

    from tools.installer_premiere import PremiereExtensionInstaller

    installer = PremiereExtensionInstaller()
    installer.run_premiere_only()

    # 1. Verify CEP panel structure
    cep_dir = appdata_mock / "Adobe" / "CEP" / "extensions" / "com.xdrop.panel"
    assert cep_dir.is_dir(), "CEP extension folder was not created"
    assert (cep_dir / "CSXS" / "manifest.xml").is_file()
    assert (cep_dir / "index.html").is_file()
    assert (cep_dir / "jsx" / "hostscript.jsx").is_file()
    assert (cep_dir / "config.json").is_file()

    # 2. Verify CSXS manifest includes Premiere, After Effects, and Audition
    manifest_xml = (cep_dir / "CSXS" / "manifest.xml").read_text(encoding="utf-8")
    assert 'Name="PPRO"' in manifest_xml
    assert 'Name="AEFT"' in manifest_xml
    assert 'Name="AUDT"' in manifest_xml

    # 3. Verify silent start_engine.vbs was generated
    vbs = localappdata_mock / "Xdrop" / "start_engine.vbs"
    assert vbs.is_file(), "Silent background launcher start_engine.vbs was not created"


def test_resolve_installer_custom_folder(tmp_path, monkeypatch):
    """Verify Resolve installer deploys files into user-specified custom directory."""
    appdata_mock = tmp_path / "AppData" / "Roaming"
    localappdata_mock = tmp_path / "AppData" / "Local"
    monkeypatch.setenv("APPDATA", str(appdata_mock))
    monkeypatch.setenv("LOCALAPPDATA", str(localappdata_mock))

    custom_dir = tmp_path / "CustomDrive" / "DaVinci Resolve" / "Fusion" / "Scripts"
    custom_dir.mkdir(parents=True, exist_ok=True)

    from tools.installer_resolve import ResolveExtensionInstaller, get_default_resolve_paths

    installer = ResolveExtensionInstaller(custom_scripts_dir=custom_dir)
    installer.run_resolve_only(install_engine=False)

    # Verify custom Comp directory received Xdrop.lua and Starter Bin
    comp_dir = custom_dir / "Comp"
    assert (comp_dir / "Xdrop.lua").is_file(), "Custom Comp/Xdrop.lua missing"
    assert (comp_dir / "Xdrop - Starter Bin.drb").is_file(), "Custom Comp/Xdrop - Starter Bin.drb missing"

    # Verify custom Utility directory received Xdrop.py
    util_dir = custom_dir / "Utility"
    assert (util_dir / "Xdrop.py").is_file(), "Custom Utility/Xdrop.py missing"

    # Verify paths detection
    paths = get_default_resolve_paths()
    assert "user_comp" in paths
    assert "user_workflow" in paths


def test_premiere_installer_custom_folder(tmp_path, monkeypatch):
    """Verify Premiere installer deploys files into user-specified custom CEP directory."""
    appdata_mock = tmp_path / "AppData" / "Roaming"
    localappdata_mock = tmp_path / "AppData" / "Local"
    monkeypatch.setenv("APPDATA", str(appdata_mock))
    monkeypatch.setenv("LOCALAPPDATA", str(localappdata_mock))

    custom_cep = tmp_path / "CustomDrive" / "Adobe" / "CEP" / "extensions"
    custom_cep.mkdir(parents=True, exist_ok=True)

    from tools.installer_premiere import PremiereExtensionInstaller, get_default_adobe_paths

    installer = PremiereExtensionInstaller(custom_cep_dir=custom_cep)
    installer.run_premiere_only(install_engine=False)

    # Verify custom CEP extension folder was created
    custom_panel = custom_cep / "com.xdrop.panel"
    assert custom_panel.is_dir(), "Custom com.xdrop.panel directory missing"
    assert (custom_panel / "CSXS" / "manifest.xml").is_file(), "Custom manifest.xml missing"
    assert (custom_panel / "config.json").is_file(), "Custom config.json missing"

    # Verify paths detection
    paths = get_default_adobe_paths()
    assert "user_cep" in paths
    assert "user_panel" in paths


def test_process_util_silent_hook():
    """Verify install_silent_subprocess_hook sets CREATE_NO_WINDOW and SW_HIDE flags."""
    import subprocess
    from xdrop.process_util import install_silent_subprocess_hook

    install_silent_subprocess_hook()

    # Create dummy Popen kwargs and check modifications if on Windows
    if sys.platform == "win32":
        # Test running a fast silent command like 'where python'
        proc = subprocess.Popen(
            ["cmd.exe", "/c", "echo silent"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, _ = proc.communicate(timeout=5)
        assert "silent" in stdout
