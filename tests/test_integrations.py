"""
Tests for `xdrop.integrations` — the headless, per-user install of every host integration.

The claims worth defending here, because they are what the product promises and what breaks
quietly:

- the default install writes only to the current user's folders, so no step needs
  administrator rights (nothing may contain `sudo`, `runas`, or an elevation helper);
- the Resolve script lands where Resolve actually scans, and is verified after writing;
- the Adobe panel gets both its files *and* developer mode, on Windows (`HKCU\\...\\CSXS.<n>`)
  and macOS (`defaults write`), because files alone do not make a panel appear;
- running the installer twice is a no-op, not an error;
- Linux is told the truth (CEP does not exist there) instead of failing obscurely.

Every test points the install at a temporary sandbox, so no test touches a real editor
installation or the real registry.
"""

import json
import subprocess
from pathlib import Path

import pytest

from xdrop.integrations import (
    install_integrations,
    integrations_status,
    player_debug_mode_commands,
    read_player_debug_mode,
)
from xdrop.integrations.cep import (
    apply_player_debug_mode,
    cep_panel_status,
    install_cep_panel,
)
from xdrop.integrations.headless import silent_kwargs
from xdrop.integrations.paths import (
    CSXS_VERSIONS,
    LINUX,
    MACOS,
    SYSTEM_SCOPE,
    USER_SCOPE,
    WINDOWS,
    cep_extension_dir,
    cep_extensions_dir,
    detect,
    for_system,
    resolve_script_dir,
    resolve_script_dirs,
)
from xdrop.integrations.resolve import install_resolve_script, resolve_script_status


def _is_read_command(command):
    """True for the commands that only inspect state (`reg query`, `defaults read`)."""
    if not command:
        return False
    if command[0] == "reg":
        return "query" in command
    if command[0] == "defaults":
        return "read" in command
    return False


class FakeRunner:
    """Stand-in for `headless.run_silent` that records argv and never runs anything.

    Reads (`reg query` / `defaults read`) answer as if developer mode were already on, which
    is what a machine looks like right after the install that just ran. Passing a non-zero
    `returncode` makes both the writes and the reads fail, which is how a locked-down machine
    is modelled.
    """

    QUERY_STDOUT = "    PlayerDebugMode    REG_SZ    1"

    def __init__(
        self,
        returncode: int = 0,
        stdout: str = "",
        stderr: str = "",
        query_stdout: str = QUERY_STDOUT,
    ):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.query_stdout = query_stdout
        self.calls = []

    def __call__(self, argv, *args, **kwargs):
        command = [str(part) for part in argv]
        self.calls.append(command)
        if _is_read_command(command):
            if self.returncode == 0:
                return subprocess.CompletedProcess(command, 0, self.query_stdout, "")
            return subprocess.CompletedProcess(command, self.returncode, "", self.stderr)
        return subprocess.CompletedProcess(command, self.returncode, self.stdout, self.stderr)

    @property
    def commands(self):
        return [" ".join(call) for call in self.calls]


def sandbox(tmp_path: Path, system: str = WINDOWS):
    """A `HostPlatformPaths` rooted entirely inside `tmp_path`."""
    return for_system(
        system,
        home=tmp_path / "home",
        appdata=tmp_path / "appdata",
        program_data=tmp_path / "programdata",
    )


def assert_nothing_needs_admin(runner: FakeRunner) -> None:
    """The whole no-UAC promise, checked against every command that was actually run."""
    forbidden = ("sudo", "runas", "pkexec", "doas", "Start-Process", "Verb RunAs")
    for command in runner.commands:
        lowered = command.lower()
        for token in forbidden:
            assert token.lower() not in lowered, f"install tried to elevate: {command}"


# --- Path selection ------------------------------------------------------------------


def test_resolve_per_user_path_is_used_by_default(tmp_path):
    """The default Resolve target is the per-user folder, not ProgramData."""
    paths = sandbox(tmp_path)
    per_user, all_users = resolve_script_dirs(paths)

    assert per_user == (
        tmp_path
        / "appdata"
        / "Blackmagic Design"
        / "DaVinci Resolve"
        / "Support"
        / "Fusion"
        / "Scripts"
        / "Utility"
    )
    assert all_users == (
        tmp_path
        / "programdata"
        / "Blackmagic Design"
        / "DaVinci Resolve"
        / "Fusion"
        / "Scripts"
        / "Utility"
    )
    assert resolve_script_dir(paths) == per_user
    assert resolve_script_dir(paths, SYSTEM_SCOPE) == all_users


def test_cep_target_is_the_per_user_extensions_folder(tmp_path):
    paths = sandbox(tmp_path)
    expected = tmp_path / "appdata" / "Adobe" / "CEP" / "extensions"
    assert cep_extensions_dir(paths) == expected
    assert cep_extension_dir(paths) == expected / "com.xdrop.panel"


def test_macos_and_linux_paths_match_blackmagics_layout(tmp_path):
    mac_user, mac_all = resolve_script_dirs(sandbox(tmp_path, MACOS))
    assert mac_user == (
        tmp_path
        / "home"
        / "Library"
        / "Application Support"
        / "Blackmagic Design"
        / "DaVinci Resolve"
        / "Fusion"
        / "Scripts"
        / "Utility"
    )
    assert mac_all == (
        tmp_path
        / "programdata"
        / "Blackmagic Design"
        / "DaVinci Resolve"
        / "Fusion"
        / "Scripts"
        / "Utility"
    )

    linux_user, linux_all = resolve_script_dirs(sandbox(tmp_path, LINUX))
    assert linux_user == (
        tmp_path / "home" / ".local" / "share" / "DaVinciResolve" / "Fusion" / "Scripts" / "Utility"
    )
    assert linux_all == Path("/opt/resolve/Fusion/Scripts/Utility")

    # CEP does not exist on Linux at all — reported, never guessed at.
    assert cep_extensions_dir(sandbox(tmp_path, LINUX)) is None


def test_path_root_override_keeps_installs_inside_one_sandbox(tmp_path, monkeypatch):
    monkeypatch.setenv("XDROP_PATH_ROOT", str(tmp_path))
    paths = detect()

    assert paths.home == tmp_path / "home"
    assert paths.appdata == tmp_path / "appdata"
    assert str(resolve_script_dir(paths)).startswith(str(tmp_path))


# --- Resolve -------------------------------------------------------------------------


def test_resolve_install_writes_a_runnable_launcher_for_the_current_user(tmp_path):
    paths = sandbox(tmp_path)
    result = install_resolve_script(paths=paths)

    assert result.ok is True, result.message
    assert result.requires_admin is False
    assert result.scope == USER_SCOPE
    assert result.restart_required is True

    target = Path(result.path)
    assert target.is_file()
    assert str(target) in result.details["written"]
    assert target.parent == resolve_script_dir(paths, USER_SCOPE)

    # The legacy filename is kept so an old desktop shortcut keeps working after upgrading.
    assert (target.parent / "ResolveFetch.py").is_file()

    script = target.read_text(encoding="utf-8")
    assert "http://127.0.0.1:8484?host=resolve" in script
    assert "CREATE_NO_WINDOW" in script, "the launcher must start the engine without a console"
    assert "Workspace -> Scripts -> Utility" in script


def test_resolve_install_is_idempotent(tmp_path):
    paths = sandbox(tmp_path)
    first = install_resolve_script(paths=paths)
    second = install_resolve_script(paths=paths)

    assert first.ok and second.ok
    assert first.path == second.path
    directory = resolve_script_dir(paths, USER_SCOPE)
    assert sorted(p.name for p in directory.iterdir()) == ["ResolveFetch.py", "Xdrop.py"]


def test_resolve_status_sees_nothing_installed_then_sees_the_install(tmp_path):
    paths = sandbox(tmp_path)

    before = resolve_script_status(paths)
    assert before["installed"] is False
    assert before["path"] is None
    assert [loc["scope"] for loc in before["locations"]] == [USER_SCOPE, SYSTEM_SCOPE]
    assert [loc["requiresAdmin"] for loc in before["locations"]] == [False, True]

    install_resolve_script(paths=paths)

    after = resolve_script_status(paths)
    assert after["installed"] is True
    assert after["scope"] == USER_SCOPE
    assert after["locations"][0]["installed"] is True


def test_resolve_status_finds_a_legacy_all_users_install(tmp_path):
    """A machine that predates the move to per-user must still report as installed."""
    paths = sandbox(tmp_path)
    all_users = resolve_script_dir(paths, SYSTEM_SCOPE)
    all_users.mkdir(parents=True)
    (all_users / "ResolveFetch.py").write_text("# legacy\n", encoding="utf-8")

    status = resolve_script_status(paths)
    assert status["installed"] is True
    assert status["scope"] == SYSTEM_SCOPE


def test_permission_denied_says_admin_rights_and_offers_the_per_user_path(tmp_path, monkeypatch):
    paths = sandbox(tmp_path)

    def denied(target_dir, content):
        raise PermissionError(13, "Access is denied")

    monkeypatch.setattr("xdrop.integrations.resolve._write_launchers", denied)

    result = install_resolve_script(paths=paths, scope=SYSTEM_SCOPE)

    assert result.ok is False
    assert result.requires_admin is True
    assert "Administrator rights" in result.message
    # The useful part: where to install instead, so the user is never stuck.
    assert "needs no elevation" in result.message


# --- Adobe CEP -----------------------------------------------------------------------


def test_player_debug_mode_commands_are_plain_data_for_both_platforms():
    windows = player_debug_mode_commands(WINDOWS, ("9", "16"))
    assert windows[0] == [
        "reg",
        "add",
        "HKCU\\Software\\Adobe\\CSXS.9",
        "/v",
        "PlayerDebugMode",
        "/t",
        "REG_SZ",
        "/d",
        "1",
        "/f",
    ]
    assert "/f" in windows[1]

    macos = player_debug_mode_commands(MACOS, ("13",))
    assert macos == [["defaults", "write", "com.adobe.CSXS.13", "PlayerDebugMode", "1"]]

    assert player_debug_mode_commands(LINUX) == []


def test_cep_install_writes_the_panel_and_enables_developer_mode(tmp_path):
    paths = sandbox(tmp_path)
    runner = FakeRunner()

    result = install_cep_panel(paths=paths, runner=runner)

    assert result.ok is True, result.message
    assert result.requires_admin is False
    assert result.details["playerDebugMode"]["enabled"] is True

    dest = cep_extension_dir(paths)
    for relative in ("CSXS/manifest.xml", "index.html", "jsx/hostscript.jsx"):
        assert (dest / relative).is_file(), f"{relative} missing from the installed panel"

    config = json.loads((dest / "config.json").read_text(encoding="utf-8"))
    assert config["serviceUrl"] == "http://127.0.0.1:8484"
    assert config["pythonExe"], "the panel needs to know which interpreter to start"
    assert config["mainPy"].endswith("main.py")

    # The UXP sources are packaging input, not part of the CEP panel.
    assert not (dest / "uxp").exists()

    # Every CSXS major version is covered, so whichever one the host uses is already on.
    assert len(runner.calls) == len(CSXS_VERSIONS)
    assert any("CSXS.16" in command for command in runner.commands)
    assert_nothing_needs_admin(runner)


def test_cep_install_refreshes_stale_files_on_second_run(tmp_path):
    paths = sandbox(tmp_path)
    install_cep_panel(paths=paths, runner=FakeRunner())

    dest = cep_extension_dir(paths)
    (dest / "index.html").unlink()
    (dest / "jsx" / "hostscript.jsx").unlink()

    result = install_cep_panel(paths=paths, runner=FakeRunner())

    assert result.ok is True
    assert (dest / "index.html").is_file()
    assert (dest / "jsx" / "hostscript.jsx").is_file()


def test_cep_install_reports_a_failure_when_files_land_but_developer_mode_does_not(tmp_path):
    """Files without developer mode is a panel that never appears — not a success."""
    paths = sandbox(tmp_path)
    runner = FakeRunner(returncode=1, stderr="ERROR: Access is denied")

    result = install_cep_panel(paths=paths, runner=runner)

    assert result.ok is False
    assert "developer mode could not be enabled" in result.message
    # The files really are on disk; the message must say what is actually wrong.
    assert (cep_extension_dir(paths) / "CSXS" / "manifest.xml").is_file()
    assert result.details["playerDebugMode"]["failed"]


def test_cep_status_flags_developer_mode_as_the_reason_a_panel_is_invisible(tmp_path):
    paths = sandbox(tmp_path)
    install_cep_panel(paths=paths, runner=FakeRunner())

    disabled = cep_panel_status(paths, runner=FakeRunner(returncode=1))
    assert disabled["installed"] is True
    assert disabled["playerDebugMode"]["enabled"] is False
    assert disabled["playerDebugMode"]["missing"] == list(CSXS_VERSIONS)
    assert any("Developer mode is off" in note for note in disabled["notes"])

    enabled = cep_panel_status(
        paths,
        runner=FakeRunner(stdout="    PlayerDebugMode    REG_SZ    1"),
    )
    assert enabled["playerDebugMode"]["enabled"] is True
    assert enabled["playerDebugMode"]["missing"] == []


def test_read_player_debug_mode_maps_versions_to_unknown_off_and_on(tmp_path):
    paths = sandbox(tmp_path)

    unset = read_player_debug_mode(WINDOWS, ("9",), runner=FakeRunner(returncode=1))
    assert unset == {"9": None}

    off = read_player_debug_mode(
        WINDOWS, ("9",), runner=FakeRunner(query_stdout="PlayerDebugMode    REG_SZ    0")
    )
    assert off == {"9": False}

    on = read_player_debug_mode(MACOS, ("13",), runner=FakeRunner(query_stdout="1\n"))
    assert on == {"13": True}

    # A value that is neither 0 nor 1 is "unknown", not "off".
    odd = read_player_debug_mode(
        WINDOWS, ("9",), runner=FakeRunner(query_stdout="PlayerDebugMode    REG_SZ    maybe")
    )
    assert odd == {"9": None}


def test_apply_player_debug_mode_reports_partial_success(tmp_path):
    calls = {"count": 0}

    def flaky(argv, *args, **kwargs):
        calls["count"] += 1
        code = 0 if calls["count"] != 2 else 1
        return subprocess.CompletedProcess(list(argv), code, "", "" if code == 0 else "denied")

    state = apply_player_debug_mode(WINDOWS, ("9", "10", "11"), runner=flaky)

    assert state["applied"] == ["9", "11"]
    assert [failure["version"] for failure in state["failed"]] == ["10"]


def test_linux_is_told_the_truth_about_cep(tmp_path):
    paths = sandbox(tmp_path, LINUX)

    result = install_cep_panel(paths=paths)
    assert result.ok is False
    assert "only supported on Windows and macOS" in result.message
    assert "DaVinci Resolve" in result.message

    status = cep_panel_status(paths)
    assert status["supported"] is False
    assert status["installed"] is False


# --- Orchestration -------------------------------------------------------------------


def test_install_everything_covers_all_three_hosts_without_admin(tmp_path):
    paths = sandbox(tmp_path)
    runner = FakeRunner()

    outcome = install_integrations(paths=paths, runner=runner)

    assert outcome["success"] is True, outcome["message"]
    assert {result["host"] for result in outcome["results"]} == {"resolve", "adobe"}
    assert all(result["requiresAdmin"] is False for result in outcome["results"])
    assert all(result["ok"] is True for result in outcome["results"])
    assert_nothing_needs_admin(runner)

    status = outcome["status"]
    assert [host["host"] for host in status["hosts"]] == ["resolve", "premiere", "aftereffects"]
    assert all(host["installed"] is True for host in status["hosts"])
    assert all(host["requiresAdmin"] is False for host in status["hosts"])
    assert status["playerDebugMode"]["enabled"] is True


def test_install_one_host_leaves_the_others_alone(tmp_path):
    paths = sandbox(tmp_path)

    outcome = install_integrations(hosts=["aftereffects"], paths=paths, runner=FakeRunner())

    assert outcome["success"] is True
    assert [result["host"] for result in outcome["results"]] == ["adobe"]
    assert (cep_extension_dir(paths) / "CSXS" / "manifest.xml").is_file()
    assert resolve_script_status(paths)["installed"] is False


def test_adobe_aliases_and_unknown_hosts_are_handled(tmp_path):
    paths = sandbox(tmp_path)

    aliased = install_integrations(hosts=["adobe", "nonsense"], paths=paths, runner=FakeRunner())
    assert [result["host"] for result in aliased["results"]] == ["adobe"]

    nothing = install_integrations(hosts=["nonsense"], paths=paths, runner=FakeRunner())
    assert nothing["success"] is False
    assert "No installable hosts" in nothing["message"]


def test_status_never_reports_admin_as_required(tmp_path):
    status = integrations_status(paths=sandbox(tmp_path), runner=FakeRunner())

    assert status["requiresAdmin"] is False
    assert status["platform"] == WINDOWS
    assert status["installationPaths"]["resolveUser"] == str(
        resolve_script_dir(sandbox(tmp_path), USER_SCOPE)
    )
    assert all(host["checkedPaths"] for host in status["hosts"])


def test_install_survives_a_host_that_fails(tmp_path, monkeypatch):
    """One broken host must not take the others down with it."""
    paths = sandbox(tmp_path)

    def broken(target_dir, content):
        raise OSError("disk on fire")

    monkeypatch.setattr("xdrop.integrations.resolve._write_launchers", broken)

    outcome = install_integrations(paths=paths, runner=FakeRunner())

    assert outcome["success"] is False
    assert "disk on fire" in outcome["message"]
    hosts = {result["host"]: result for result in outcome["results"]}
    assert hosts["resolve"]["ok"] is False
    assert hosts["adobe"]["ok"] is True


# --- Headless -----------------------------------------------------------------------


def test_child_processes_cannot_show_a_window(monkeypatch):
    kw = silent_kwargs()
    assert kw["stdin"] == subprocess.DEVNULL
    assert kw["stdout"] == subprocess.PIPE

    monkeypatch.setattr("sys.platform", "win32")
    assert silent_kwargs()["creationflags"] == 0x08000000  # CREATE_NO_WINDOW

    monkeypatch.setattr("sys.platform", "linux")
    assert silent_kwargs()["start_new_session"] is True


# --- HTTP interface ------------------------------------------------------------------


@pytest.fixture
def sandboxed_env(tmp_path, monkeypatch):
    """Redirect every install target into a temp dir and stub out the OS helpers."""
    root = tmp_path / "sandbox"
    monkeypatch.setenv("XDROP_PATH_ROOT", str(root))
    fake = FakeRunner()
    monkeypatch.setattr("xdrop.integrations.cep.run_silent", fake)
    monkeypatch.setattr("xdrop.integrations.run_silent", fake)
    return root, fake


def test_install_endpoint_installs_everything_without_touching_the_real_profile(sandboxed_env):
    from fastapi.testclient import TestClient

    root, fake = sandboxed_env

    from xdrop.main import app

    with TestClient(app) as client:
        response = client.post("/api/settings/integrations/install", json={})

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["success"] is True, body
        assert all(result["requiresAdmin"] is False for result in body["results"])

        status = client.get("/api/settings/integrations").json()
        assert all(host["installed"] for host in status["hosts"])

        tools = client.get("/api/settings/tools-status").json()
        assert tools["resolveScript"]["isInstalled"] is True
        assert tools["premiereExtension"]["isInstalled"] is True
        assert tools["premiereExtension"]["playerDebugMode"]["enabled"] is True

    assert (root / "appdata" / "Blackmagic Design" / "DaVinci Resolve" / "Support" / "Fusion" / "Scripts" / "Utility" / "Xdrop.py").is_file()
    assert (root / "appdata" / "Adobe" / "CEP" / "extensions" / "com.xdrop.panel" / "CSXS" / "manifest.xml").is_file()
    assert_nothing_needs_admin(fake)


def test_install_endpoint_can_target_a_single_host(sandboxed_env):
    from fastapi.testclient import TestClient

    root, _ = sandboxed_env

    from xdrop.main import app

    with TestClient(app) as client:
        response = client.post("/api/settings/integrations/install", json={"hosts": ["resolve"]})

    assert response.status_code == 200, response.text
    assert [result["host"] for result in response.json()["results"]] == ["resolve"]
    assert (root / "appdata" / "Adobe").exists() is False


def test_install_endpoint_rejects_an_unknown_scope(sandboxed_env):
    from fastapi.testclient import TestClient

    from xdrop.main import app

    with TestClient(app) as client:
        response = client.post("/api/settings/integrations/install", json={"scope": "root"})

    assert response.status_code == 400
    assert "Unknown scope" in response.json()["detail"]


def test_legacy_endpoints_still_work(sandboxed_env):
    """The old per-host endpoints are kept working; the panel and older callers use them."""
    from fastapi.testclient import TestClient

    root, _ = sandboxed_env

    from xdrop.main import app

    with TestClient(app) as client:
        resolve_response = client.post("/api/settings/install-resolve-script")
        adobe_response = client.post("/api/settings/install-premiere-extension")
        ae_response = client.post("/api/settings/install-aftereffects-extension")

    assert resolve_response.status_code == 200, resolve_response.text
    assert adobe_response.status_code == 200, adobe_response.text
    assert ae_response.status_code == 200, ae_response.text
    assert "com.xdrop.panel" in adobe_response.json()["message"]
    assert (root / "appdata" / "Blackmagic Design").is_dir()
