#!/usr/bin/env python3
"""Generate Windows packaging artifacts for Scoop and winget submission."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import urllib.request
from datetime import date
from pathlib import Path


PACKAGE_NAME = "lore-book"
PYPI_SOURCE_BASE = "https://files.pythonhosted.org/packages/source"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare Windows packaging artifacts")
    parser.add_argument("--version", required=True, help="Release version (e.g. 1.3.1)")
    parser.add_argument("--repo", default="CptPlastic/lore-book", help="GitHub repository owner/name")
    parser.add_argument("--sdist-file", default="", help="Path to local sdist (.tar.gz) to hash")
    parser.add_argument("--output-root", default=".", help="Repository root")
    parser.add_argument("--github-output", default="", help="Path to GitHub Actions output file")
    return parser.parse_args()


def distribution_name_from_sdist_filename(filename: str, version: str) -> str:
    pattern = re.compile(rf"^(?P<name>.+)-{re.escape(version)}\.tar\.gz$")
    match = pattern.match(filename)
    if not match:
        raise ValueError(f"sdist filename does not match version {version}: {filename}")
    return match.group("name")


def pypi_sdist_url(version: str, sdist_filename: str = "") -> str:
    if sdist_filename:
        filename = Path(sdist_filename).name
        distribution_name = distribution_name_from_sdist_filename(filename, version)
    else:
        distribution_name = PACKAGE_NAME.replace("-", "_")
        filename = f"{distribution_name}-{version}.tar.gz"

    first_letter = distribution_name[0].lower()
    return f"{PYPI_SOURCE_BASE}/{first_letter}/{distribution_name}/{filename}"


def sha256_of_url(url: str) -> str:
    with urllib.request.urlopen(url, timeout=30) as resp:  # noqa: S310
        data = resp.read()
    return hashlib.sha256(data).hexdigest()


def sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_scoop_manifest(root: Path, version: str, url: str, sha256: str) -> Path:
    manifest = {
        "version": version,
        "description": "The spellbook for your codebase - chronicle decisions, context, and lessons your AI tools can read.",
        "homepage": "https://github.com/CptPlastic/lore-book",
        "license": "FSL-1.1-MIT",
        "depends": "python",
        "architecture": {
            "64bit": {
                "url": url,
                "hash": sha256,
            }
        },
        "checkver": "https://pypi.org/pypi/lore-book/json",
        "autoupdate": {
            "architecture": {
                "64bit": {
                    "url": "https://files.pythonhosted.org/packages/source/l/lore_book/lore_book-$version.tar.gz"
                }
            }
        },
        "pre_install": [
            'python -m pip install --upgrade --target "$dir\\site" "$dir"',
            'if ($LASTEXITCODE -ne 0) { throw "Failed to install lore-book from extracted package payload." }',
            '$installed = python -c "import sys; sys.path.insert(0, r\"$dir\\site\"); import lore; print(lore.__version__)"',
            'if ($LASTEXITCODE -ne 0) { throw "Failed to validate installed lore-book version." }',
            'if ($installed.Trim() -ne $version) { throw "Installed lore-book version does not match manifest version." }',
            'Set-Content -Path "$dir\\lore.cmd" -Value "@echo off`r`nsetlocal`r`nset ""PYTHONPATH=%~dp0site;%PYTHONPATH%""`r`npython -c ""from lore.cli import app; app()"" %*" -Encoding Ascii',
        ],
        "bin": "lore.cmd",
    }

    path = root / "packaging" / "scoop" / "lore-book.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return path


def write_winget_submission_bundle(
    root: Path,
    version: str,
    repo: str,
    url: str,
    sha256: str,
) -> Path:
    path = root / "packaging" / "winget" / f"submission-{version}.md"
    body = f"""# winget submission helper for lore-book {version}

Generated: {date.today().isoformat()}

## Package metadata

- PackageIdentifier: CptPlastic.LoreBook
- PackageVersion: {version}
- Publisher: CptPlastic
- PackageName: lore-book
- License: FSL-1.1-MIT
- InstallerUrl: {url}
- InstallerSha256: {sha256}

## Notes

`lore-book` is a Python CLI package. A direct winget installer is not auto-published from this repo.
Use this file as the source of truth for opening/updating a PR in `microsoft/winget-pkgs`.

## Recommended submission flow

1. Install wingetcreate.
2. Create or update a manifest for `CptPlastic.LoreBook` using the URL/hash above.
3. Open a PR in `microsoft/winget-pkgs`.

Reference repository: https://github.com/{repo}
"""
    path.write_text(body, encoding="utf-8")
    return path


def write_outputs(path: str, scoop_manifest: Path, winget_bundle: Path, sha256: str) -> None:
    if not path:
        return
    with Path(path).open("a", encoding="utf-8") as fh:
        fh.write(f"scoop_manifest={scoop_manifest.as_posix()}\n")
        fh.write(f"winget_bundle={winget_bundle.as_posix()}\n")
        fh.write(f"pypi_sdist_sha256={sha256}\n")


def main() -> int:
    args = parse_args()
    root = Path(args.output_root).resolve()
    sdist_file: Path | None = None
    if args.sdist_file:
        sdist_file = Path(args.sdist_file)
        if not sdist_file.is_absolute():
            sdist_file = root / sdist_file
        if not sdist_file.exists():
            raise FileNotFoundError(f"sdist file not found: {sdist_file}")

    url = pypi_sdist_url(args.version, sdist_file.name if sdist_file else "")
    if sdist_file:
        sha256 = sha256_of_file(sdist_file)
    else:
        sha256 = sha256_of_url(url)

    scoop_manifest = write_scoop_manifest(root, args.version, url, sha256)
    winget_bundle = write_winget_submission_bundle(root, args.version, args.repo, url, sha256)
    write_outputs(args.github_output, scoop_manifest, winget_bundle, sha256)

    print(f"Prepared Scoop manifest: {scoop_manifest}")
    print(f"Prepared winget submission bundle: {winget_bundle}")
    print(f"PyPI sdist SHA256: {sha256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
