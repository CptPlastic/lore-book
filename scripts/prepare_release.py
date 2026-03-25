#!/usr/bin/env python3
"""Prepare a release: bump version, update changelog, emit release notes."""
from __future__ import annotations

import argparse
import re
import subprocess
from dataclasses import dataclass
from datetime import date
from pathlib import Path

VERSION_RE = re.compile(r'__version__\s*=\s*"(\d+)\.(\d+)\.(\d+)"')


@dataclass
class Version:
    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, value: str) -> "Version":
        parts = value.strip().split(".")
        if len(parts) != 3:
            raise ValueError(f"Invalid version: {value}")
        return cls(int(parts[0]), int(parts[1]), int(parts[2]))

    def bump(self, kind: str) -> "Version":
        if kind == "major":
            return Version(self.major + 1, 0, 0)
        if kind == "minor":
            return Version(self.major, self.minor + 1, 0)
        if kind == "patch":
            return Version(self.major, self.minor, self.patch + 1)
        raise ValueError(f"Unsupported bump kind: {kind}")

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


def run_git(args: list[str]) -> str:
    proc = subprocess.run(["git", *args], check=True, capture_output=True, text=True)
    return proc.stdout.strip()


def get_current_version(version_file: Path) -> Version:
    content = version_file.read_text(encoding="utf-8")
    match = VERSION_RE.search(content)
    if not match:
        raise RuntimeError(f"Could not find __version__ in {version_file}")
    return Version(int(match.group(1)), int(match.group(2)), int(match.group(3)))


def write_version(version_file: Path, new_version: Version) -> None:
    content = version_file.read_text(encoding="utf-8")
    updated = VERSION_RE.sub(f'__version__ = "{new_version}"', content, count=1)
    version_file.write_text(updated, encoding="utf-8")


def get_last_tag() -> str | None:
    try:
        out = run_git(["describe", "--tags", "--abbrev=0"])
    except subprocess.CalledProcessError:
        return None
    return out if out else None


def collect_commits(last_tag: str | None) -> list[str]:
    if last_tag:
        spec = f"{last_tag}..HEAD"
    else:
        spec = "HEAD"
    out = run_git(["log", "--pretty=format:%s", spec])
    lines = [line.strip() for line in out.splitlines() if line.strip()]
    return lines


def categorize(commit: str) -> str:
    lowered = commit.lower()
    if lowered.startswith("feat"):
        return "Features"
    if lowered.startswith("fix"):
        return "Fixes"
    if lowered.startswith("docs"):
        return "Documentation"
    if lowered.startswith("refactor"):
        return "Refactors"
    if lowered.startswith("perf"):
        return "Performance"
    if lowered.startswith("test"):
        return "Tests"
    if lowered.startswith("build") or lowered.startswith("ci"):
        return "Build/CI"
    return "Other"


def to_bullet(commit: str) -> str:
    cleaned = re.sub(r"^[a-zA-Z]+(\([^)]*\))?!?:\s*", "", commit).strip()
    return cleaned if cleaned else commit


def build_release_notes(version: Version, commits: list[str]) -> str:
    sections: dict[str, list[str]] = {
        "Features": [],
        "Fixes": [],
        "Documentation": [],
        "Refactors": [],
        "Performance": [],
        "Tests": [],
        "Build/CI": [],
        "Other": [],
    }
    for commit in commits:
        sections[categorize(commit)].append(to_bullet(commit))

    lines: list[str] = []
    heading = f"## v{version} - {date.today().isoformat()}"
    lines.append(heading)
    lines.append("")

    added_any = False
    for section, items in sections.items():
        if not items:
            continue
        added_any = True
        lines.append(f"### {section}")
        for item in items:
            lines.append(f"- {item}")
        lines.append("")

    if not added_any:
        lines.append("- Maintenance release.")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def prepend_changelog(changelog_file: Path, entry: str) -> None:
    if changelog_file.exists():
        existing = changelog_file.read_text(encoding="utf-8")
    else:
        existing = "# Changelog\n\n"
    header = "# Changelog\n\n"
    if existing.startswith(header):
        tail = existing[len(header):].lstrip("\n")
    else:
        tail = existing
    merged = header + entry + "\n" + tail
    changelog_file.write_text(merged, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare release artifacts")
    parser.add_argument("--bump", choices=["patch", "minor", "major"], default="patch")
    parser.add_argument("--version", default="", help="Explicit version (overrides --bump)")
    parser.add_argument("--version-file", default="src/lore/__init__.py")
    parser.add_argument("--changelog-file", default="CHANGELOG.md")
    parser.add_argument("--notes-file", default=".release-notes.md")
    parser.add_argument("--github-output", default="")
    return parser.parse_args()


def write_outputs(path: str, version: str, tag: str) -> None:
    if not path:
        return
    output = Path(path)
    with output.open("a", encoding="utf-8") as fh:
        fh.write(f"version={version}\n")
        fh.write(f"tag={tag}\n")


def main() -> int:
    args = parse_args()
    version_file = Path(args.version_file)
    changelog_file = Path(args.changelog_file)
    notes_file = Path(args.notes_file)

    current = get_current_version(version_file)
    if args.version.strip():
        target = Version.parse(args.version.strip())
    else:
        target = current.bump(args.bump)

    last_tag = get_last_tag()
    commits = collect_commits(last_tag)
    notes = build_release_notes(target, commits)

    write_version(version_file, target)
    prepend_changelog(changelog_file, notes)
    notes_file.write_text(notes, encoding="utf-8")

    tag = f"v{target}"
    write_outputs(args.github_output, str(target), tag)

    print(f"Prepared release {target}")
    print(f"Tag: {tag}")
    if last_tag:
        print(f"Commit range: {last_tag}..HEAD")
    else:
        print("Commit range: full history")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
