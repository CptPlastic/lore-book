"""YAML-backed memory store — CRUD operations."""
from __future__ import annotations

import uuid
import yaml
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import memory_dir, load_config, save_config, DEFAULT_CONFIG

# Per-file YAML parse cache: path -> (mtime, parsed_data)
# Re-parses only when the file's mtime changes — transparent for both CLI and TUI.
_yaml_cache: dict[Path, tuple[float, Any]] = {}


def _load_yaml_cached(path: Path) -> Any:
    """Return parsed YAML for *path*, using the cache when mtime is unchanged."""
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return None
    cached = _yaml_cache.get(path)
    if cached is not None and cached[0] == mtime:
        return cached[1]
    with path.open() as fh:
        data = yaml.safe_load(fh)
    _yaml_cache[path] = (mtime, data)
    return data


def init_store(root: Path) -> None:
    """Create the .memory directory structure at *root*."""
    mem = memory_dir(root)
    mem.mkdir(exist_ok=True)
    config = DEFAULT_CONFIG.copy()
    for cat in config["categories"]:
        (mem / cat).mkdir(exist_ok=True)
    (mem / "embeddings").mkdir(exist_ok=True)
    config_path = mem / "config.yaml"
    if not config_path.exists():
        save_config(root, config)


def _short_id() -> str:
    return str(uuid.uuid4())[:8]


def add_memory(
    root: Path,
    category: str,
    content: str,
    tags: list[str] | None = None,
    source: str = "manual",
) -> dict[str, Any]:
    """Write a new memory entry and return the stored dict."""
    config = load_config(root)
    valid_cats: list[str] = config.get("categories", [])
    if category not in valid_cats:
        valid_cats.append(category)
        config["categories"] = valid_cats
        save_config(root, config)

    cat_dir = memory_dir(root) / category
    cat_dir.mkdir(exist_ok=True)

    mem_id = _short_id()
    now = datetime.now(timezone.utc)
    entry: dict[str, Any] = {
        "id": mem_id,
        "category": category,
        "content": content,
        "tags": tags or [],
        "source": source,
        "created_at": now.isoformat(),
    }
    filename = f"{now.strftime('%Y%m%d%H%M%S')}_{mem_id}.yaml"
    path = cat_dir / filename
    with path.open("w") as f:
        yaml.dump(entry, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
    return entry


def list_memories(root: Path, category: str | None = None) -> list[dict[str, Any]]:
    """Return all memories, optionally filtered to a single category."""
    mem = memory_dir(root)
    config = load_config(root)
    categories = [category] if category else config.get("categories", [])
    entries: list[dict[str, Any]] = []
    for cat in categories:
        cat_dir = mem / cat
        if not cat_dir.is_dir():
            continue
        for f in sorted(cat_dir.glob("*.yaml")):
            data = _load_yaml_cached(f)
            if data:
                entries.append(data)
    return entries


def remove_memory(root: Path, mem_id: str) -> bool:
    """Delete the YAML file for *mem_id*. Returns True if found and deleted."""
    mem = memory_dir(root)
    config = load_config(root)
    for cat in config.get("categories", []):
        cat_dir = mem / cat
        if not cat_dir.is_dir():
            continue
        # ID is embedded in the filename — no need to open every file
        matches = list(cat_dir.glob(f"*_{mem_id}.yaml"))
        if matches:
            matches[0].unlink()
            _yaml_cache.pop(matches[0], None)
            return True
    return False
