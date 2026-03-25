"""CHRONICLE.md import helpers.

Import flow is intentionally conservative:
- only sectioned bullets under known memory categories are considered
- existing entries are deduplicated by category + normalized content + tags
- export annotations (trust/scope/tags suffixes) are stripped when present
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .store import add_memory, list_memories


_HEADING_TO_CATEGORY: dict[str, str] = {
    "decision": "decisions",
    "decisions": "decisions",
    "fact": "facts",
    "facts": "facts",
    "instruction": "instructions",
    "instructions": "instructions",
    "preference": "preferences",
    "preferences": "preferences",
    "summary": "summaries",
    "summaries": "summaries",
}

_SECTION_RE = re.compile(r"^##\s+(.+?)\s*$")
_BULLET_RE = re.compile(r"^-\s+(.*\S)\s*$")
_TRUST_SUFFIX_RE = re.compile(r"\s+_\(trust:[^)]+\)_\s*$", flags=re.IGNORECASE)
_SCOPE_SUFFIX_RE = re.compile(r"\s+_\(scope:\s*([^)]+)\)_\s*$", flags=re.IGNORECASE)
_TAGS_SUFFIX_RE = re.compile(r"\s+_([^_]+)_\s*$")


def _normalize_heading(heading: str) -> str | None:
    normalized = re.sub(r"[^a-z]+", " ", heading.lower()).strip()
    return _HEADING_TO_CATEGORY.get(normalized)


def _normalize_text(value: str) -> str:
    return " ".join(value.split()).strip().casefold()


def _normalize_key(category: str, content: str, tags: list[str]) -> tuple[str, str, tuple[str, ...]]:
    normalized_tags = tuple(sorted(_normalize_text(t) for t in tags if t.strip()))
    return (category, _normalize_text(content), normalized_tags)


def _parse_scope_tags(raw_scope: str) -> list[str]:
    tags = [t.strip() for t in raw_scope.split(",") if t.strip()]
    return tags if tags else ["all"]


def _strip_export_suffixes(category: str, text: str) -> tuple[str, list[str]]:
    content = text.strip()
    tags: list[str] = []

    while True:
        prior = content

        trust_match = _TRUST_SUFFIX_RE.search(content)
        if trust_match:
            content = content[:trust_match.start()].rstrip()
            continue

        scope_match = _SCOPE_SUFFIX_RE.search(content)
        if scope_match:
            if category == "instructions" and not tags:
                tags = _parse_scope_tags(scope_match.group(1))
            content = content[:scope_match.start()].rstrip()
            continue

        tags_match = _TAGS_SUFFIX_RE.search(content)
        if tags_match:
            maybe_tags = [t.strip() for t in tags_match.group(1).split(",") if t.strip()]
            if maybe_tags and category != "instructions":
                tags = maybe_tags
                content = content[:tags_match.start()].rstrip()
                continue

        if content == prior:
            break

    return content, tags


def import_chronicle(
    root: Path,
    chronicle_path: Path | None = None,
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Import CHRONICLE bullets into the lore store.

    Returns a stats dict with keys:
    - path
    - bullets_seen
    - recognized
    - added
    - skipped_duplicates
    - skipped_unknown_section
    - indexed_pairs: list[(id, content)] for newly created entries
    """
    path = chronicle_path or (root / "CHRONICLE.md")
    if not path.exists():
        raise RuntimeError(f"CHRONICLE file not found: {path}")

    existing = list_memories(root)
    seen_keys: set[tuple[str, str, tuple[str, ...]]] = set()
    for entry in existing:
        cat = entry.get("category", "")
        content = str(entry.get("content", ""))
        tags = list(entry.get("tags") or [])
        if cat and content.strip():
            seen_keys.add(_normalize_key(cat, content, tags))

    current_category: str | None = None
    bullets_seen = 0
    recognized = 0
    added = 0
    skipped_duplicates = 0
    skipped_unknown_section = 0
    indexed_pairs: list[tuple[str, str]] = []

    rel_source = f"chronicle:{path.relative_to(root)}" if path.is_relative_to(root) else f"chronicle:{path}"

    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        section_match = _SECTION_RE.match(raw_line)
        if section_match:
            current_category = _normalize_heading(section_match.group(1))
            continue

        bullet_match = _BULLET_RE.match(raw_line)
        if not bullet_match:
            continue

        bullets_seen += 1
        if not current_category:
            skipped_unknown_section += 1
            continue

        content, tags = _strip_export_suffixes(current_category, bullet_match.group(1))
        if not content.strip():
            continue

        recognized += 1
        key = _normalize_key(current_category, content, tags)
        if key in seen_keys:
            skipped_duplicates += 1
            continue

        seen_keys.add(key)
        if dry_run:
            added += 1
            continue

        entry = add_memory(root, current_category, content, tags=tags, source=rel_source)
        indexed_pairs.append((entry["id"], content))
        added += 1

    return {
        "path": path,
        "bullets_seen": bullets_seen,
        "recognized": recognized,
        "added": added,
        "skipped_duplicates": skipped_duplicates,
        "skipped_unknown_section": skipped_unknown_section,
        "indexed_pairs": indexed_pairs,
    }
