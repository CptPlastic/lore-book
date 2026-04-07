"""YAML-backed memory store — CRUD operations."""
from __future__ import annotations

import uuid
import yaml
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import memory_dir, load_config, save_config, DEFAULT_CONFIG, generate_identity, is_valid_uuid

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
        identity = generate_identity()
        config["identity"] = identity
        save_config(root, config)
    else:
        # Ensure existing stores gain an identity if they were created before this feature.
        existing_cfg = load_config(root)
        ident = existing_cfg.get("identity", {})
        if not ident.get("id"):
            existing_cfg["identity"] = generate_identity()
            save_config(root, existing_cfg)


def ensure_identity(root: Path) -> tuple[bool, dict]:
    """Verify the store has a valid identity; repair silently if not.

    Returns ``(was_repaired, identity_dict)``.
    If the id is missing or not a valid UUID the id is regenerated.
    If the name is also absent a fresh name is generated too.
    The existing name is preserved when only the id is broken.
    """
    cfg = load_config(root)
    identity = cfg.get("identity", {})
    ident_id   = identity.get("id", "")
    ident_name = identity.get("name", "")

    if ident_id and is_valid_uuid(ident_id):
        return False, identity

    # Repair: keep name when still present, always issue a fresh id.
    if ident_name:
        new_identity: dict = {"name": ident_name, "id": str(uuid.uuid4())}
    else:
        new_identity = generate_identity()

    cfg["identity"] = new_identity
    save_config(root, cfg)
    return True, new_identity


def _short_id() -> str:
    return str(uuid.uuid4())[:8]


def _normalize_id_list(values: list[str] | None) -> list[str]:
    if not values:
        return []
    out: list[str] = []
    for value in values:
        item = (value or "").strip()
        if item and item not in out:
            out.append(item)
    return out


def add_memory(
    root: Path,
    category: str,
    content: str,
    tags: list[str] | None = None,
    depends_on: list[str] | None = None,
    related_to: list[str] | None = None,
    deprecated: bool = False,
    review_date: str | None = None,
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

    # Capture git context at write time (branch + author) — silently skipped if not a git repo
    from .extract import git_context
    gctx = git_context(root)

    mem_id = _short_id()
    now = datetime.now(timezone.utc)
    trust_cfg = config.get("trust", {})
    default_trust = int(trust_cfg.get("default_score", 50))

    entry: dict[str, Any] = {
        "id": mem_id,
        "category": category,
        "content": content,
        "tags": tags or [],
        "depends_on": _normalize_id_list(depends_on),
        "related_to": _normalize_id_list(related_to),
        "deprecated": bool(deprecated),
        "source": source,
        "created_at": now.isoformat(),
        "trust_score": max(0, min(100, default_trust)),
    }
    if review_date:
        entry["review_date"] = review_date
    if gctx.get("branch"):
        entry["git_branch"] = gctx["branch"]
    if gctx.get("author"):
        entry["git_author"] = gctx["author"]
    if source.startswith("git:"):
        entry["source_commit"] = source.split(":", 2)[1] if ":" in source else None

    from .trust import trust_level
    entry["trust_level"] = trust_level(int(entry["trust_score"]))
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


def update_memory(root: Path, mem_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
    """Update fields of a memory in-place. Returns the updated entry or None if not found.

    If 'category' changes, the YAML file is moved to the new category directory.
    """
    mem = memory_dir(root)
    config = load_config(root)

    # Find the file across all category dirs
    found_path: Path | None = None
    for cat in config.get("categories", []):
        cat_dir = mem / cat
        if not cat_dir.is_dir():
            continue
        matches = list(cat_dir.glob(f"*_{mem_id}.yaml"))
        if matches:
            found_path = matches[0]
            break

    if found_path is None:
        return None

    with found_path.open() as f:
        entry = yaml.safe_load(f)
    if not entry:
        return None

    old_category = entry.get("category", "")
    new_category = updates.get("category", old_category)

    # Normalize metadata lists when they are updated.
    if "depends_on" in updates:
        updates["depends_on"] = _normalize_id_list(updates.get("depends_on"))
    if "related_to" in updates:
        updates["related_to"] = _normalize_id_list(updates.get("related_to"))

    # Apply updates (exclude internal helper keys)
    for k, v in updates.items():
        entry[k] = v

    # Move file if category changed
    if new_category != old_category:
        new_cat_dir = mem / new_category
        new_cat_dir.mkdir(exist_ok=True)
        cats = config.get("categories", [])
        if new_category not in cats:
            cats.append(new_category)
            config["categories"] = cats
            save_config(root, config)
        new_path = new_cat_dir / found_path.name
        _yaml_cache.pop(found_path, None)
        found_path.rename(new_path)
        found_path = new_path

    with found_path.open("w") as f:
        yaml.dump(entry, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
    _yaml_cache.pop(found_path, None)
    return entry
