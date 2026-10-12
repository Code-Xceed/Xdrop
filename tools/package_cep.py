#!/usr/bin/env python3
"""
Package the Adobe CEP panel as a signed `.zxp`.

Why this exists: a `.zxp` is a ZIP plus a signature, and CEP re-checks that signature every
time a host loads the extension — not just at install. A certificate typically lives one to
four years, so a `.zxp` signed without a timestamp **stops working for every user, on a date,
with no warning**. Signing with `-tsa` is therefore mandatory here, not a flag to remember:
this tool refuses to produce a package without a timestamp, and records the date the
certificate must be replaced and the package rebuilt.

Two modes:

- `--create-cert` creates a self-signed certificate (fine for sideloading and internal
  distribution) and records when it was made, which is what lets the tool tell you the
  repackage deadline later.
- the default mode signs `apps/premiere-plugin` into `dist/xdrop-cep-<version>.zxp`,
  verifies the signature, and writes `dist/package-report.json`.

Adobe's tool is `ZXPSignCmd`. It is not vendored here: point at it with `--zxpsigncmd`,
`$ZXPSIGNCMD`, or put it under `tools/bin/`.

References:
- Adobe, *Package, Distribute, Install Guide* (CEP)
- Adobe, *ZXPSignCmd* / CEP Resources
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = REPO_ROOT / "apps" / "premiere-plugin"
DEFAULT_CERT = REPO_ROOT / "dist" / "certs" / "xdrop-cep.p12"
DEFAULT_OUT_DIR = REPO_ROOT / "dist"

#: A timestamp means an already-expired certificate still validates. These are the URLs
#: Adobe's own guide uses; the first is the default.
DEFAULT_TSA_URLS = (
    "http://timestamp.digicert.com",
    "http://time.certum.pl/",
)

#: Self-signed certificates default to ~1 year here, which is conservative on purpose: the
#: failure mode is "rebuild the package", and a shorter cycle makes that routine rather than
#: a surprise.
DEFAULT_CERT_VALID_DAYS = 365

CERT_METADATA_FILENAME = "cep-cert.json"

#: Files that must never end up inside a distributed package.
SECRET_PATTERNS = (".env", ".p12", ".pfx", ".key", ".pem", "secrets", "credentials")


class PackagingError(RuntimeError):
    """A packaging step failed in a way the operator has to fix."""


class TimestampRequiredError(PackagingError):
    """Raised when a build would produce a signature that dies on certificate expiry."""


@dataclass
class SignResult:
    zxp: Path
    verified: bool
    tsa_url: str
    verify_output: str = ""
    repackage_by: Optional[str] = None
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return {
            "zxp": str(self.zxp),
            "bytes": self.zxp.stat().st_size if self.zxp.exists() else 0,
            "verified": self.verified,
            "tsaUrl": self.tsa_url,
            "verifyOutput": self.verify_output,
            "repackageBy": self.repackage_by,
            "warnings": list(self.warnings),
        }


# --- Pure argument builders ----------------------------------------------------------
#
# These are plain functions returning argument lists so the signing contract (in particular
# "a timestamp is always present") is testable without ZXPSignCmd installed.


def self_signed_cert_argv(
    zxpsigncmd: Path,
    country: str,
    state: str,
    organization: str,
    common_name: str,
    password: str,
    cert_path: Path,
) -> List[str]:
    """`ZXPSignCmd -selfSignedCert ...`."""
    return [
        str(zxpsigncmd),
        "-selfSignedCert",
        country,
        state,
        organization,
        common_name,
        password,
        str(cert_path),
    ]


def sign_argv(
    zxpsigncmd: Path,
    source_dir: Path,
    output_zxp: Path,
    cert_path: Path,
    password: str,
    tsa_url: Optional[str],
) -> List[str]:
    """`ZXPSignCmd -sign ... [-tsa ...]`, refusing an empty or missing timestamp URL."""
    if not tsa_url or not str(tsa_url).strip():
        raise TimestampRequiredError(
            "Signing without a timestamp would break every user's install when the "
            "certificate expires (CEP re-checks the signature on every load). Pass a "
            "timestamp URL, e.g. -tsa " + DEFAULT_TSA_URLS[0]
        )
    return [
        str(zxpsigncmd),
        "-sign",
        str(source_dir),
        str(output_zxp),
        str(cert_path),
        password,
        "-tsa",
        str(tsa_url).strip(),
    ]


def verify_argv(zxpsigncmd: Path, zxp_path: Path) -> List[str]:
    """`ZXPSignCmd -verify ... -certinfo`."""
    return [str(zxpsigncmd), "-verify", str(zxp_path), "-certinfo"]


def repackage_deadline(
    cert_created_at: Optional[datetime],
    valid_days: Optional[int] = DEFAULT_CERT_VALID_DAYS,
) -> Optional[str]:
    """When the certificate must be replaced and the package rebuilt, as an ISO date.

    This works from the creation date *we* recorded, not from parsing ZXPSignCmd's
    certificate dump — if the certificate was supplied externally the answer is honestly
    `None` rather than a guess.
    """
    if cert_created_at is None or valid_days is None:
        return None
    deadline = cert_created_at + timedelta(days=valid_days)
    return deadline.date().isoformat()


def find_forbidden_entries(source_dir: Path) -> List[str]:
    """Files that look like secrets and must not be shipped inside a `.zxp`."""
    found: List[str] = []
    for path in source_dir.rglob("*"):
        if not path.is_file():
            continue
        # Always reported with forward slashes: these strings end up in messages an operator
        # reads, and the same package must look identical on Windows and macOS.
        relative = path.relative_to(source_dir).as_posix()
        if any(pattern in relative.lower() for pattern in SECRET_PATTERNS):
            found.append(relative)
    return sorted(found)


# --- Tooling -------------------------------------------------------------------------


def find_zxpsigncmd(explicit: Optional[str] = None) -> Optional[Path]:
    """Locates `ZXPSignCmd` via the argument, `$ZXPSIGNCMD`, `tools/bin`, or `PATH`."""
    import os

    if explicit:
        candidate = Path(explicit)
        return candidate if candidate.is_file() else None

    env = os.getenv("ZXPSIGNCMD")
    if env and Path(env).is_file():
        return Path(env)

    candidates: List[Path] = []
    for name in ("ZXPSignCmd.exe", "ZXPSignCmd"):
        candidates.append(REPO_ROOT / "tools" / "bin" / name)
        located = shutil.which(name)
        if located:
            candidates.append(Path(located))

    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def _run(argv: Sequence[str], cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        list(argv),
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        check=False,
    )


def cert_metadata_path(cert_path: Path) -> Path:
    return cert_path.parent / CERT_METADATA_FILENAME


def read_cert_metadata(cert_path: Path) -> Dict[str, object]:
    meta_file = cert_metadata_path(cert_path)
    if not meta_file.is_file():
        return {}
    try:
        return json.loads(meta_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def create_self_signed_certificate(
    zxpsigncmd: Path,
    cert_path: Path = DEFAULT_CERT,
    password: str = "xdrop-local",
    country: str = "US",
    state: str = "California",
    organization: str = "Xdrop",
    common_name: str = "Xdrop CEP",
    valid_days: int = DEFAULT_CERT_VALID_DAYS,
) -> Path:
    """Creates a certificate and records its creation date for the repackage deadline."""
    cert_path.parent.mkdir(parents=True, exist_ok=True)
    argv = self_signed_cert_argv(
        zxpsigncmd, country, state, organization, common_name, password, cert_path
    )
    proc = _run(argv)
    if proc.returncode != 0:
        raise PackagingError(
            f"ZXPSignCmd could not create a certificate (exit {proc.returncode}): "
            f"{proc.stdout.strip()} {proc.stderr.strip()}"
        )

    created_at = datetime.now(timezone.utc)
    cert_metadata_path(cert_path).write_text(
        json.dumps(
            {
                "createdAt": created_at.isoformat(),
                "validDays": valid_days,
                "commonName": common_name,
                "organization": organization,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return cert_path


def sign_zxp(
    zxpsigncmd: Path,
    source_dir: Path,
    output_zxp: Path,
    cert_path: Path,
    password: str,
    tsa_url: str = DEFAULT_TSA_URLS[0],
    verify: bool = True,
) -> SignResult:
    """Signs `source_dir` into a `.zxp`, verifying the result and reporting the deadline."""
    if not source_dir.is_dir():
        raise PackagingError(f"CEP source directory not found: {source_dir}")
    if not cert_path.is_file():
        raise PackagingError(
            f"Signing certificate not found: {cert_path}. Create one with --create-cert."
        )

    forbidden = find_forbidden_entries(source_dir)
    if forbidden:
        raise PackagingError(
            "Refusing to package files that look like secrets: " + ", ".join(forbidden)
        )

    output_zxp.parent.mkdir(parents=True, exist_ok=True)
    proc = _run(sign_argv(zxpsigncmd, source_dir, output_zxp, cert_path, password, tsa_url))
    if proc.returncode != 0 or not output_zxp.is_file():
        raise PackagingError(
            f"ZXPSignCmd -sign failed (exit {proc.returncode}): "
            f"{proc.stdout.strip()} {proc.stderr.strip()}"
        )

    result = SignResult(zxp=output_zxp, verified=False, tsa_url=tsa_url)

    metadata = read_cert_metadata(cert_path)
    valid_days = metadata.get("validDays") if isinstance(metadata, dict) else None
    created_raw = metadata.get("createdAt") if isinstance(metadata, dict) else None
    created_at: Optional[datetime] = None
    if isinstance(created_raw, str):
        try:
            created_at = datetime.fromisoformat(created_raw)
        except ValueError:
            created_at = None
    result.repackage_by = repackage_deadline(created_at, valid_days)  # type: ignore[arg-type]
    if result.repackage_by is None:
        result.warnings.append(
            "A timestamp protects an expired certificate, but repackaging is still required: "
            "read the expiry from the -certinfo output and replace the certificate before then."
        )

    if verify:
        verify_proc = _run(verify_argv(zxpsigncmd, output_zxp))
        result.verify_output = (verify_proc.stdout + verify_proc.stderr).strip()
        result.verified = verify_proc.returncode == 0
        if not result.verified:
            result.warnings.append(
                "ZXPSignCmd -verify did not exit cleanly. The package may not load in a host."
            )
    else:
        result.warnings.append("Verification was skipped; the signature is unproven.")

    return result


def build(
    source_dir: Path = DEFAULT_SOURCE,
    out_dir: Path = DEFAULT_OUT_DIR,
    version: str = "1.0.0",
    cert_path: Path = DEFAULT_CERT,
    password: str = "xdrop-local",
    tsa_url: str = DEFAULT_TSA_URLS[0],
    zxpsigncmd: Optional[Path] = None,
    create_cert: bool = False,
) -> Dict[str, object]:
    """Full build: locate the tool, optionally create a certificate, sign, verify, report."""
    if not tsa_url or not tsa_url.strip():
        raise TimestampRequiredError(
            "This tool will not build a .zxp without a timestamp URL (--tsa)."
        )

    tool = find_zxpsigncmd(str(zxpsigncmd) if zxpsigncmd else None)
    if tool is None:
        raise PackagingError(
            f"ZXPSignCmd was not found (looked at: {zxpsigncmd or '$ZXPSIGNCMD, tools/bin, PATH'}). "
            "Download it from Adobe's CEP Resources repository, then pass --zxpsigncmd <path> "
            "or set ZXPSIGNCMD."
        )

    if create_cert or not cert_path.is_file():
        create_self_signed_certificate(tool, cert_path=cert_path, password=password)

    out_dir.mkdir(parents=True, exist_ok=True)
    zxp_path = out_dir / f"xdrop-cep-{version}.zxp"

    result = sign_zxp(
        tool,
        source_dir=source_dir,
        output_zxp=zxp_path,
        cert_path=cert_path,
        password=password,
        tsa_url=tsa_url,
    )

    report = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "source": str(source_dir),
        "certificate": str(cert_path),
        "sign": result.to_dict(),
        "notes": [
            "A signed .zxp installs through Creative Cloud / ExManCmd and does not need "
            "PlayerDebugMode, unlike the folder copy the app installs.",
            "Rebuild and reinstall before repackageBy.",
        ],
    }
    (out_dir / "cep-package-report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return report


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Sign the Xdrop CEP panel into a .zxp")
    parser.add_argument("--source", default=str(DEFAULT_SOURCE), help="CEP extension folder")
    parser.add_argument("--out", default=str(DEFAULT_OUT_DIR), help="Output directory")
    parser.add_argument("--version", default="1.0.0", help="Version used in the file name")
    parser.add_argument("--cert", default=str(DEFAULT_CERT), help="Path to the .p12 certificate")
    parser.add_argument("--password", default="xdrop-local", help="Certificate password")
    parser.add_argument(
        "--tsa",
        default=DEFAULT_TSA_URLS[0],
        help="RFC 3161 timestamp URL. Mandatory: an un-timestamped signature dies with the certificate.",
    )
    parser.add_argument("--zxpsigncmd", default=None, help="Path to ZXPSignCmd")
    parser.add_argument(
        "--create-cert",
        action="store_true",
        help="Create/refresh a self-signed certificate first",
    )
    args = parser.parse_args(argv)

    try:
        report = build(
            source_dir=Path(args.source),
            out_dir=Path(args.out),
            version=args.version,
            cert_path=Path(args.cert),
            password=args.password,
            tsa_url=args.tsa,
            zxpsigncmd=Path(args.zxpsigncmd) if args.zxpsigncmd else None,
            create_cert=args.create_cert,
        )
    except PackagingError as exc:
        print(f"[X] {exc}", file=sys.stderr)
        return 1

    sign = report["sign"]
    print(f"[+] Signed: {sign['zxp']} ({sign['bytes']} bytes)")
    print(f"[+] Timestamp: {sign['tsaUrl']}")
    print(f"[+] Signature verified: {sign['verified']}")
    if sign["repackageBy"]:
        print(f"[!] Rebuild and reinstall before: {sign['repackageBy']}")
    for warning in sign["warnings"]:
        print(f"[i] {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
