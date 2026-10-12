"""
Tests for the packaging tools in `tools/`.

What is defended here is the set of rules that, when broken, produce a package that installs
fine today and stops working later:

- a `.zxp` is always signed **with a timestamp** — without one, an expired certificate kills
  the extension for every user with no warning, so the tool must refuse to build;
- a `.zxp` never carries files that look like secrets, and the repackage deadline is derived
  from the creation date we recorded rather than guessed;
- a `.ccx` is a plain ZIP (no signature, no timestamp), one host per package, and every
  package carries its own **direct-distribution** id so Creative Cloud's entitlement check
  cannot reject it.

`ZXPSignCmd` is not required: the argument builders are pure, and the orchestration is tested
against a stubbed runner. That keeps these tests runnable on any machine while still checking
the commands that would be executed.
"""

import json
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

import package_cep  # noqa: E402
import package_uxp  # noqa: E402


# --- CEP: signing --------------------------------------------------------------------


def test_sign_argv_always_carries_a_timestamp():
    argv = package_cep.sign_argv(
        Path("/tools/ZXPSignCmd"),
        source_dir=Path("/src/panel"),
        output_zxp=Path("/dist/xdrop.zxp"),
        cert_path=Path("/dist/cert.p12"),
        password="secret",
        tsa_url="http://timestamp.digicert.com",
    )

    assert argv[1] == "-sign"
    assert "-tsa" in argv
    assert argv[argv.index("-tsa") + 1] == "http://timestamp.digicert.com"
    assert argv[2] == str(Path("/src/panel"))
    assert argv[3] == str(Path("/dist/xdrop.zxp"))


@pytest.mark.parametrize("tsa", [None, "", "   "])
def test_sign_argv_refuses_to_build_without_a_timestamp(tsa):
    with pytest.raises(package_cep.TimestampRequiredError) as excinfo:
        package_cep.sign_argv(
            Path("ZXPSignCmd"),
            source_dir=Path("/src"),
            output_zxp=Path("/out.zxp"),
            cert_path=Path("/cert.p12"),
            password="secret",
            tsa_url=tsa,
        )

    # The message has to explain the consequence, not just assert a rule.
    assert "expires" in str(excinfo.value)


def test_self_signed_certificate_argv_matches_adobe_parameter_order():
    argv = package_cep.self_signed_cert_argv(
        Path("ZXPSignCmd"),
        country="US",
        state="California",
        organization="Xdrop",
        common_name="Xdrop CEP",
        password="pw",
        cert_path=Path("/dist/cert.p12"),
    )

    assert argv[1] == "-selfSignedCert"
    assert argv[2:7] == ["US", "California", "Xdrop", "Xdrop CEP", "pw"]
    assert argv[7] == str(Path("/dist/cert.p12"))


def test_verify_argv_requests_certificate_information():
    argv = package_cep.verify_argv(Path("ZXPSignCmd"), Path("/dist/xdrop.zxp"))
    assert argv[1] == "-verify"
    assert argv[-1] == "-certinfo"


def test_repackage_deadline_comes_from_the_recorded_creation_date():
    created = datetime(2026, 1, 1, tzinfo=timezone.utc)

    assert package_cep.repackage_deadline(created, 365) == "2027-01-01"
    # An externally supplied certificate has no recorded date: say nothing rather than guess.
    assert package_cep.repackage_deadline(None, 365) is None
    assert package_cep.repackage_deadline(created, None) is None


def test_secret_looking_files_are_detected_before_packaging(tmp_path):
    panel = tmp_path / "panel"
    (panel / "CSXS").mkdir(parents=True)
    (panel / "CSXS" / "manifest.xml").write_text("<ExtensionManifest/>", encoding="utf-8")
    (panel / ".env").write_text("API_KEY=oops", encoding="utf-8")
    (panel / "certs").mkdir()
    (panel / "certs" / "signing.p12").write_bytes(b"\x00")

    found = package_cep.find_forbidden_entries(panel)

    assert ".env" in found
    assert "certs/signing.p12" in found


def test_build_refuses_without_the_signing_tool(tmp_path):
    panel = tmp_path / "panel"
    (panel / "CSXS").mkdir(parents=True)
    (panel / "CSXS" / "manifest.xml").write_text("<ExtensionManifest/>", encoding="utf-8")

    with pytest.raises(package_cep.PackagingError) as excinfo:
        package_cep.build(
            source_dir=panel,
            out_dir=tmp_path / "dist",
            cert_path=tmp_path / "cert.p12",
            zxpsigncmd=Path("/nonexistent/ZXPSignCmd"),
        )

    assert "ZXPSignCmd was not found" in str(excinfo.value)


def test_build_refuses_an_empty_timestamp_url(tmp_path):
    with pytest.raises(package_cep.TimestampRequiredError):
        package_cep.build(
            source_dir=tmp_path,
            out_dir=tmp_path / "dist",
            tsa_url="",
            zxpsigncmd=Path("/nonexistent/ZXPSignCmd"),
        )


def test_find_zxpsigncmd_returns_none_for_a_missing_explicit_path():
    assert package_cep.find_zxpsigncmd("/definitely/not/here/ZXPSignCmd") is None


def test_sign_zxp_runs_sign_then_verify_and_records_the_deadline(tmp_path, monkeypatch):
    """The orchestration, with ZXPSignCmd stubbed: sign, verify, report, warn."""
    source = tmp_path / "panel"
    (source / "CSXS").mkdir(parents=True)
    (source / "CSXS" / "manifest.xml").write_text("<ExtensionManifest/>", encoding="utf-8")
    cert = tmp_path / "cert.p12"
    cert.write_bytes(b"\x00")
    (cert.parent / package_cep.CERT_METADATA_FILENAME).write_text(
        json.dumps({"createdAt": "2026-01-01T00:00:00+00:00", "validDays": 365}),
        encoding="utf-8",
    )
    out = tmp_path / "dist" / "xdrop.zxp"
    calls = []

    def fake_run(argv, cwd=None):
        calls.append([str(part) for part in argv])
        if "-sign" in argv:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(b"PK\x03\x04fake zxp")
            return subprocess.CompletedProcess(list(argv), 0, "signed", "")
        return subprocess.CompletedProcess(
            list(argv), 0, "The certificate is valid", ""
        )

    monkeypatch.setattr(package_cep, "_run", fake_run)

    result = package_cep.sign_zxp(
        Path("ZXPSignCmd"),
        source_dir=source,
        output_zxp=out,
        cert_path=cert,
        password="pw",
    )

    assert result.verified is True
    assert result.repackage_by == "2027-01-01"
    assert "-tsa" in calls[0], "the very first call must include the timestamp"
    assert calls[1][1] == "-verify"
    assert result.to_dict()["bytes"] == out.stat().st_size


def test_sign_zxp_reports_a_failed_verification(tmp_path, monkeypatch):
    source = tmp_path / "panel"
    source.mkdir()
    cert = tmp_path / "cert.p12"
    cert.write_bytes(b"\x00")
    out = tmp_path / "dist" / "xdrop.zxp"

    def fake_run(argv, cwd=None):
        if "-sign" in argv:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(b"PK\x03\x04")
            return subprocess.CompletedProcess(list(argv), 0, "", "")
        return subprocess.CompletedProcess(list(argv), 1, "", "signature invalid")

    monkeypatch.setattr(package_cep, "_run", fake_run)

    result = package_cep.sign_zxp(
        Path("ZXPSignCmd"), source, out, cert, "pw"
    )

    assert result.verified is False
    assert any("may not load" in warning for warning in result.warnings)
    # No recorded certificate date, so the deadline is honestly unknown.
    assert result.repackage_by is None


def test_sign_zxp_stops_on_secret_looking_files(tmp_path):
    source = tmp_path / "panel"
    source.mkdir()
    (source / ".env").write_text("X=1", encoding="utf-8")
    cert = tmp_path / "cert.p12"
    cert.write_bytes(b"\x00")

    with pytest.raises(package_cep.PackagingError) as excinfo:
        package_cep.sign_zxp(Path("ZXPSignCmd"), source, tmp_path / "out.zxp", cert, "pw")

    assert "secrets" in str(excinfo.value)


# --- UXP: .ccx -----------------------------------------------------------------------


@pytest.mark.parametrize("host,app", [("premiere", "premierepro"), ("aftereffects", "aftereffects")])
def test_build_ccx_produces_a_plain_zip_for_one_host(host, app, tmp_path):
    result = package_uxp.build_ccx(host, out_dir=tmp_path, version="1.2.3")

    assert result.path.suffix == ".ccx"
    assert result.path.is_file()
    assert zipfile.is_zipfile(result.path)

    with zipfile.ZipFile(result.path) as archive:
        members = set(archive.namelist())
        assert {"manifest.json", "index.html", "main.js", "styles.css"} <= members
        assert "icons/iconNormal.png" in members
        # A .ccx is a plain ZIP: no signature, no certificate, and no CEP leftovers.
        assert not any(member.endswith((".p12", ".zxp", ".sig")) for member in members)
        assert not any("CSXS" in member or "jsx" in member for member in members)

        manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
        index = archive.read("index.html").decode("utf-8")

    assert manifest["manifestVersion"] >= 6
    assert isinstance(manifest["host"], dict), "production packages use a single host object"
    assert manifest["host"]["app"] == app
    assert manifest["host"]["minVersion"]
    assert manifest["id"] == f"com.xdrop.panel.direct.{app}"
    assert manifest["version"] == "1.2.3"
    assert [entry["type"] for entry in manifest["entrypoints"]] == ["panel"]
    assert manifest["requiredPermissions"]["network"]["domains"] == [
        "http://127.0.0.1:8484",
        "ws://127.0.0.1:8484",
    ]
    assert f"?host={host}" in index
    assert len(result.members) == len(set(result.members)), "duplicate entries in the package"


def test_build_all_gives_each_host_its_own_plugin_id(tmp_path):
    report = package_uxp.build_all(out_dir=tmp_path)

    ids = [package["pluginId"] for package in report["packages"]]
    assert len(ids) == 2
    assert len(set(ids)) == 2, "two packages sharing an id would collide at install time"
    assert not any(plugin_id == package_uxp.CEP_BUNDLE_ID for plugin_id in ids), (
        "a package must not reuse the Marketplace/Creative Cloud bundle id"
    )
    assert (tmp_path / "uxp-package-report.json").is_file()


def test_manifest_validation_rejects_marketplace_id_and_array_host(tmp_path):
    manifest = package_uxp.render_manifest("premiere")
    assert package_uxp.validate_manifest(manifest, "premiere") == []

    reused_id = dict(manifest, id=package_uxp.CEP_BUNDLE_ID)
    problems = package_uxp.validate_manifest(reused_id, "premiere")
    assert any("entitlement" in problem for problem in problems)

    array_host = dict(manifest, host=[{"app": "premierepro", "minVersion": "25.6.0"}])
    problems = package_uxp.validate_manifest(array_host, "premiere")
    assert any("single object" in problem for problem in problems)


def test_manifest_validation_rejects_network_access_beyond_the_local_service(tmp_path):
    manifest = package_uxp.render_manifest("premiere")
    manifest["requiredPermissions"]["network"]["domains"] = [
        "http://127.0.0.1:8484",
        "https://example.com",
    ]

    problems = package_uxp.validate_manifest(manifest, "premiere")

    assert any("local Xdrop service" in problem for problem in problems)


def test_manifest_validation_requires_a_webview_permission():
    manifest = package_uxp.render_manifest("aftereffects")
    manifest["requiredPermissions"]["webview"]["allow"] = "no"

    problems = package_uxp.validate_manifest(manifest, "aftereffects")

    assert any("webview.allow" in problem for problem in problems)


def test_build_ccx_rejects_an_unknown_host(tmp_path):
    with pytest.raises(package_uxp.PackagingError):
        package_uxp.build_ccx("photoshop", out_dir=tmp_path)


def test_build_ccx_fails_loudly_when_the_source_is_incomplete(tmp_path):
    empty_source = tmp_path / "uxp"
    empty_source.mkdir()

    with pytest.raises(package_uxp.PackagingError) as excinfo:
        package_uxp.build_ccx("premiere", out_dir=tmp_path / "dist", source_dir=empty_source)

    assert "template not found" in str(excinfo.value)


def test_packagers_agree_on_the_adobe_hosts():
    """Both tools must describe the same two hosts, or one of them is silently stale."""
    assert set(package_uxp.HOSTS) == {"premiere", "aftereffects"}
    assert package_uxp.HOSTS["premiere"]["app"] == "premierepro"
    assert package_uxp.HOSTS["aftereffects"]["app"] == "aftereffects"
