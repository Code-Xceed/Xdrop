#!/usr/bin/env python3
"""
Package the Xdrop UXP plugin as `.ccx` files, one per Adobe host.

`.ccx` is the UXP package format and, unlike CEP's `.zxp`, it is **a plain ZIP with no
signature and no timestamp**, which removes the whole certificate-expiry failure mode. Creative
Cloud Desktop installs it by double-click.

Three rules from Adobe's documentation shape this tool:

1. **One host per production package.** `host` must be a single object, not an array (the array
   form is development-only), so Premiere Pro and After Effects get *separate* `.ccx` files.
2. **Non-Marketplace builds need their own plugin id.** Creative Cloud validates a plugin's id
   against the user's entitlements when the same id is also listed in the Adobe Marketplace; an
   id that is distributed directly but not purchased can be *rejected* at install. Every package
   here therefore carries a `.direct.` id that is deliberately different from the Marketplace
   id, and `validate_manifest` fails the build if that ever stops being true.
3. **Keep it pure JavaScript.** Hybrid plugins with native code additionally require Apple
   Developer ID signing, notarization and administrator credentials at install time. The panel
   is HTML inside a `<webview>` pointed at the local service, so none of that applies.

The panel UI itself is not duplicated here: the UXP plugin hosts the same frontend the CEP
panel uses, which is why `apps/premiere-plugin/uxp/` holds only a manifest template, an HTML
entrypoint, a small bootstrap and a stylesheet.

References: Adobe, *Package a UXP plugin* (Premiere Pro); Adobe, *CEP to UXP migration*.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = REPO_ROOT / "apps" / "premiere-plugin" / "uxp"
DEFAULT_ICONS = REPO_ROOT / "apps" / "premiere-plugin" / "icons"
DEFAULT_OUT_DIR = REPO_ROOT / "dist"

#: The CEP bundle id in use today. A UXP package must not reuse it, and must not reuse the
#: Marketplace id either — see rule 2 in the module docstring.
CEP_BUNDLE_ID = "com.xdrop.panel"

MANIFEST_TEMPLATE = "manifest.template.json"
INDEX_TEMPLATE = "index.template.html"
STATIC_FILES = ("main.js", "styles.css")

#: Panel icons reused from the CEP extension so both packages look identical.
ICON_FILES = ("iconNormal.png", "iconDark.png")

#: One entry per shipped `.ccx`. `min_version` for Premiere Pro comes from Adobe's UXP
#: documentation; After Effects' UXP support was still a public beta at the time of writing,
#: so its floor is a conservative guess to confirm against a real beta build.
HOSTS: Dict[str, Dict[str, str]] = {
    "premiere": {
        "plugin_id": "com.xdrop.panel.direct.premierepro",
        "app": "premierepro",
        "min_version": "25.6.0",
        "label": "Premiere Pro",
    },
    "aftereffects": {
        "plugin_id": "com.xdrop.panel.direct.aftereffects",
        "app": "aftereffects",
        "min_version": "26.0",
        "label": "After Effects",
    },
}

#: Network permission is limited to the local Xdrop service: HTTP for the panel and the
#: health probe, WebSocket for the live queue updates. Any other domain is a build failure.
ALLOWED_SERVICE_DOMAINS = ("http://127.0.0.1:8484", "ws://127.0.0.1:8484")


class PackagingError(RuntimeError):
    """A packaging step failed in a way the operator has to fix."""


@dataclass
class CcxResult:
    host: str
    label: str
    path: Path
    plugin_id: str
    host_app: str
    min_version: str
    members: List[str]

    def to_dict(self) -> Dict[str, object]:
        return {
            "host": self.host,
            "label": self.label,
            "path": str(self.path),
            "bytes": self.path.stat().st_size if self.path.exists() else 0,
            "pluginId": self.plugin_id,
            "hostApp": self.host_app,
            "minVersion": self.min_version,
            "members": list(self.members),
        }


# --- Rendering -----------------------------------------------------------------------


def render_manifest(host: str, version: str = "1.0.0", source_dir: Path = DEFAULT_SOURCE) -> Dict[str, object]:
    """Builds the plugin's `manifest.json` for one host from the template."""
    if host not in HOSTS:
        raise PackagingError(f"Unknown host '{host}'. Known hosts: {', '.join(HOSTS)}")

    template_path = source_dir / MANIFEST_TEMPLATE
    if not template_path.is_file():
        raise PackagingError(f"UXP manifest template not found: {template_path}")

    spec = HOSTS[host]
    raw = template_path.read_text(encoding="utf-8")
    substitutions = {
        "{{PLUGIN_ID}}": spec["plugin_id"],
        "{{PLUGIN_NAME}}": "Xdrop",
        "{{PLUGIN_VERSION}}": version,
        "{{HOST_APP}}": spec["app"],
        "{{MIN_VERSION}}": spec["min_version"],
    }
    for placeholder, value in substitutions.items():
        raw = raw.replace(placeholder, value)

    try:
        manifest = json.loads(raw)
    except json.JSONDecodeError as exc:  # pragma: no cover - template is checked in valid
        raise PackagingError(f"Rendered manifest is not valid JSON: {exc}") from exc

    return manifest


def render_index(host: str, source_dir: Path = DEFAULT_SOURCE) -> str:
    """Builds the panel entrypoint with the host baked into the service URL."""
    template_path = source_dir / INDEX_TEMPLATE
    if not template_path.is_file():
        raise PackagingError(f"UXP index template not found: {template_path}")
    return template_path.read_text(encoding="utf-8").replace("{{HOST}}", host)


def validate_manifest(manifest: Dict[str, object], host: str) -> List[str]:
    """Returns a list of problems that would make the package rejected or misleading.

    Empty list means the package is structurally sound by the rules in the module docstring.
    """
    problems: List[str] = []
    spec = HOSTS.get(host)
    if spec is None:
        return [f"unknown host '{host}'"]

    plugin_id = manifest.get("id")
    if not isinstance(plugin_id, str) or not plugin_id.strip():
        problems.append("manifest id must be a non-empty string")
    else:
        if plugin_id == CEP_BUNDLE_ID:
            problems.append(
                f"id '{plugin_id}' is the CEP/Creative Cloud bundle id; a directly "
                "distributed .ccx must use its own id to avoid the entitlement check"
            )
        if plugin_id != spec["plugin_id"]:
            problems.append(
                f"id '{plugin_id}' does not match the expected direct-distribution id "
                f"'{spec['plugin_id']}'"
            )

    host_block = manifest.get("host")
    if not isinstance(host_block, dict):
        problems.append(
            "host must be a single object for a production package "
            "(an array is development-only)"
        )
    else:
        if host_block.get("app") != spec["app"]:
            problems.append(f"host.app must be '{spec['app']}'")
        if not host_block.get("minVersion"):
            problems.append("host.minVersion must be set")

    entrypoints = manifest.get("entrypoints")
    if not isinstance(entrypoints, list) or not entrypoints:
        problems.append("entrypoints must be a non-empty list")
    else:
        panels = [e for e in entrypoints if isinstance(e, dict) and e.get("type") == "panel"]
        if len(panels) != 1:
            problems.append(f"expected exactly one panel entrypoint, found {len(panels)}")

    main = manifest.get("main")
    if not isinstance(main, str) or not main:
        problems.append("main must name the entrypoint HTML file")

    permissions = manifest.get("requiredPermissions")
    if not isinstance(permissions, dict):
        problems.append("requiredPermissions must be present")
    else:
        network = permissions.get("network")
        domains: List[str] = []
        if isinstance(network, dict):
            raw_domains = network.get("domains")
            if isinstance(raw_domains, list):
                domains = [d for d in raw_domains if isinstance(d, str)]
        if not domains:
            problems.append("requiredPermissions.network.domains must list the Xdrop service")
        else:
            unexpected = [d for d in domains if d not in ALLOWED_SERVICE_DOMAINS]
            if unexpected:
                problems.append(
                    "network access must be limited to the local Xdrop service "
                    f"({', '.join(ALLOWED_SERVICE_DOMAINS)}); unexpected: {', '.join(unexpected)}"
                )

        webview = permissions.get("webview")
        if not isinstance(webview, dict) or webview.get("allow") != "yes":
            problems.append("requiredPermissions.webview.allow must be 'yes' to host the panel")

    return problems


# --- Building ------------------------------------------------------------------------


def _stage_package(host: str, version: str, staging: Path, source_dir: Path, icons_dir: Path) -> Dict[str, object]:
    """Writes the files for one package into `staging`. Returns the manifest."""
    manifest = render_manifest(host, version=version, source_dir=source_dir)
    (staging / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (staging / "index.html").write_text(render_index(host, source_dir=source_dir), encoding="utf-8")

    for name in STATIC_FILES:
        source = source_dir / name
        if not source.is_file():
            raise PackagingError(f"UXP source file missing: {source}")
        shutil.copy2(source, staging / name)

    icon_target_dir = staging / "icons"
    icon_target_dir.mkdir(parents=True, exist_ok=True)
    for name in ICON_FILES:
        source = icons_dir / name
        if not source.is_file():
            raise PackagingError(f"Panel icon missing: {source}")
        shutil.copy2(source, icon_target_dir / name)

    return manifest


def build_ccx(
    host: str,
    out_dir: Path = DEFAULT_OUT_DIR,
    version: str = "1.0.0",
    source_dir: Path = DEFAULT_SOURCE,
    icons_dir: Path = DEFAULT_ICONS,
) -> CcxResult:
    """Builds one host's `.ccx` and returns what went into it."""
    if host not in HOSTS:
        raise PackagingError(f"Unknown host '{host}'. Known hosts: {', '.join(HOSTS)}")

    with tempfile.TemporaryDirectory(prefix=f"xdrop-uxp-{host}-") as tmp:
        staging = Path(tmp)
        manifest = _stage_package(host, version, staging, source_dir, icons_dir)

        problems = validate_manifest(manifest, host)
        if problems:
            raise PackagingError(
                f"Refusing to package '{host}': " + "; ".join(problems)
            )

        main_name = str(manifest.get("main", "index.html"))
        if not (staging / main_name).is_file():
            raise PackagingError(f"manifest main '{main_name}' is not present in the package")

        out_dir.mkdir(parents=True, exist_ok=True)
        ccx_path = out_dir / f"xdrop-uxp-{host}-{version}.ccx"

        members: List[str] = []
        with zipfile.ZipFile(ccx_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(staging.rglob("*")):
                if path.is_file():
                    # forward slashes: ZIP members are paths, not OS paths
                    member = path.relative_to(staging).as_posix()
                    archive.write(path, member)
                    members.append(member)

    spec = HOSTS[host]
    return CcxResult(
        host=host,
        label=spec["label"],
        path=ccx_path,
        plugin_id=spec["plugin_id"],
        host_app=spec["app"],
        min_version=spec["min_version"],
        members=members,
    )


def build_all(
    out_dir: Path = DEFAULT_OUT_DIR,
    version: str = "1.0.0",
    source_dir: Path = DEFAULT_SOURCE,
    icons_dir: Path = DEFAULT_ICONS,
) -> Dict[str, object]:
    """Builds every host's `.ccx` and asserts the per-host ids stay distinct."""
    results = [
        build_ccx(host, out_dir=out_dir, version=version, source_dir=source_dir, icons_dir=icons_dir)
        for host in HOSTS
    ]

    ids = [r.plugin_id for r in results]
    if len(set(ids)) != len(ids):
        raise PackagingError(f"Each package needs its own plugin id, got: {ids}")

    report = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "version": version,
        "packages": [r.to_dict() for r in results],
        "notes": [
            "Install by opening the .ccx; Creative Cloud Desktop handles the rest. No signing "
            "and no timestamp are required.",
            "One host per package is an Adobe production requirement, which is why Premiere Pro "
            "and After Effects get separate files.",
            "The .direct. plugin ids are intentionally not the Marketplace id: an id that is "
            "distributed directly and listed in the Marketplace can be rejected at install.",
        ],
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "uxp-package-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Build the Xdrop UXP .ccx packages")
    parser.add_argument("--out", default=str(DEFAULT_OUT_DIR), help="Output directory")
    parser.add_argument("--version", default="1.0.0", help="Plugin version to stamp")
    parser.add_argument("--source", default=str(DEFAULT_SOURCE), help="UXP source folder")
    parser.add_argument("--icons", default=str(DEFAULT_ICONS), help="Panel icons folder")
    parser.add_argument("--host", default="all", choices=["all", *HOSTS], help="Single host, or all")
    args = parser.parse_args(argv)

    try:
        if args.host == "all":
            report = build_all(
                out_dir=Path(args.out),
                version=args.version,
                source_dir=Path(args.source),
                icons_dir=Path(args.icons),
            )
            packages = report["packages"]
        else:
            packages = [
                build_ccx(
                    args.host,
                    out_dir=Path(args.out),
                    version=args.version,
                    source_dir=Path(args.source),
                    icons_dir=Path(args.icons),
                ).to_dict()
            ]
    except PackagingError as exc:
        print(f"[X] {exc}", file=sys.stderr)
        return 1

    for package in packages:
        print(f"[+] {package['label']}: {package['path']} ({package['bytes']} bytes)")
        print(f"    id: {package['pluginId']}  host: {package['hostApp']} >= {package['minVersion']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
