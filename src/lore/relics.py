"""Relics — rich captured artifacts (session notes, docs, diffs) stored in .lore/relics/."""
from __future__ import annotations

import uuid
import yaml
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import memory_dir

RELICS_DIR = "relics"


def _relics_dir(root: Path) -> Path:
    d = memory_dir(root) / RELICS_DIR
    d.mkdir(exist_ok=True)
    return d


def _short_id() -> str:
    return str(uuid.uuid4())[:8]


def save_relic(
    root: Path,
    title: str,
    content: str,
    summary: str = "",
    tags: list[str] | None = None,
    source: str = "capture",
    linked_memories: list[str] | None = None,
) -> dict[str, Any]:
    """Persist a relic and return the stored dict."""
    relic_id = _short_id()
    now = datetime.now(timezone.utc)
    entry: dict[str, Any] = {
        "id": relic_id,
        "title": title,
        "content": content,
        "summary": summary,
        "tags": tags or [],
        "source": source,
        "linked_memories": linked_memories or [],
        "created_at": now.isoformat(),
    }
    filename = f"{now.strftime('%Y%m%d%H%M%S')}_{relic_id}.yaml"
    path = _relics_dir(root) / filename
    with path.open("w") as f:
        yaml.dump(entry, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
    return entry


def list_relics(root: Path) -> list[dict[str, Any]]:
    """Return all relics, newest first."""
    entries: list[dict[str, Any]] = []
    for f in sorted(_relics_dir(root).glob("*.yaml"), reverse=True):
        with f.open() as fh:
            data = yaml.safe_load(fh)
            if data:
                entries.append(data)
    return entries


def get_relic(root: Path, relic_id: str) -> dict[str, Any] | None:
    """Find a relic by ID."""
    # ID is embedded in the filename — avoid scanning every file
    matches = list(_relics_dir(root).glob(f"*_{relic_id}.yaml"))
    if not matches:
        return None
    with matches[0].open() as fh:
        return yaml.safe_load(fh)


def link_memory_to_relic(root: Path, relic_id: str, memory_id: str) -> bool:
    """Append a memory ID to a relic's linked_memories list."""
    matches = list(_relics_dir(root).glob(f"*_{relic_id}.yaml"))
    for f in matches:
        with f.open() as fh:
            data = yaml.safe_load(fh)
        if data:
            linked: list[str] = data.get("linked_memories", [])
            if memory_id not in linked:
                linked.append(memory_id)
                data["linked_memories"] = linked
                with f.open("w") as fw:
                    yaml.dump(data, fw, default_flow_style=False, sort_keys=False, allow_unicode=True)
            return True
    return False


def remove_relic(root: Path, relic_id: str) -> bool:
    """Delete a relic by ID. Returns True if found."""
    matches = list(_relics_dir(root).glob(f"*_{relic_id}.yaml"))
    if matches:
        matches[0].unlink()
        return True
    return False
