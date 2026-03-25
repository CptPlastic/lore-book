"""Configuration loading and resolution for mem."""
from __future__ import annotations

import os
import random
import uuid
from pathlib import Path
from typing import Any

import yaml

MEMORY_DIR = ".lore"
CONFIG_FILE = "config.yaml"

# Generated adapter files that should remain local by default.
# CHRONICLE.md is intentionally excluded so teams can commit shared memory.
LOCAL_AGENT_FILES = [
    ".github/copilot-instructions.md",
    "AGENTS.md",
    "CLAUDE.md",
    ".cursor/rules/memory.md",
    ".github/prompts/lore.prompt.md",
    ".windsurfrules",
    "GEMINI.md",
    ".clinerules",
    "CONVENTIONS.md",
]

_IDENTITY_ADJECTIVES = [
    "ancient", "arcane", "astral", "ashen", "burning", "crystal", "dark", "dim",
    "distant", "drifting", "eldritch", "emerald", "eternal", "fabled", "fallen",
    "forgotten", "ghost", "gilded", "glowing", "hidden", "hollow", "iron", "jade",
    "lost", "lunar", "misty", "obsidian", "phantom", "runic", "sacred", "shadowed",
    "silent", "silver", "spectral", "starlit", "sunken", "twilight", "veiled",
    "wandering", "whispering",
]

_IDENTITY_NOUNS = [
    "anvil", "archive", "atlas", "beacon", "codex", "crown", "ember", "gate",
    "glimmer", "grimoire", "loom", "meridian", "oracle", "prism", "reliquary",
    "sanctum", "scroll", "seal", "sentinel", "sigil", "specter", "spire",
    "tome", "vault", "veil", "watcher", "wayfarer",
]


def generate_identity() -> dict[str, str]:
    """Generate a unique thematic name and UUID for this lore instance."""
    name = f"{random.choice(_IDENTITY_ADJECTIVES)}-{random.choice(_IDENTITY_NOUNS)}"
    uid = str(uuid.uuid4())
    return {"name": name, "id": uid}


def is_valid_uuid(value: str) -> bool:
    """Return True if *value* is a well-formed UUID string."""
    try:
        uuid.UUID(value)
        return True
    except (ValueError, AttributeError):
        return False


DEFAULT_CONFIG: dict[str, Any] = {
    "version": 1,
    "identity": {"name": "", "id": ""},
    "project_description": "",
    "categories": ["decisions", "facts", "instructions", "preferences", "summaries"],
    "export_targets": {
        "chronicle": True,   # full memory file — lean instruction files reference this
        # Security-first defaults: export all adapters unless users disable them.
        "agents":    True,
        "copilot":   True,
        "cursor":    True,
        "claude":    True,
        "windsurf":  True,
        "gemini":    True,
        "cline":     True,
        "aider":     True,
        "prompt":    True,
    },
    "embedding_model": "all-MiniLM-L6-v2",
    # Default to the public Hugging Face Hub.
    # Override to point at Artifactory or any HuggingFace-compatible mirror.
    # Example:
    #   model_endpoint: "https://artifactory.example.com/huggingface"
    "model_endpoint": "https://huggingface.co",
    # Set to false to skip SSL verification (not recommended for prod):
    #   model_ssl_verify: false
    "model_ssl_verify": True,
    # Security preamble injected into all AI context file exports:
    "security": {
        "enabled": False,
        "owasp_top10": True,
        "security_policy": "SECURITY.md",
        "codeowners": True,
        "custom_rules": [],
    },
    # Controls how subdirectories discover this store.
    # "auto"  — walk up from any subdirectory (default, backward-compatible).
    # "local" — only the directory containing .lore/ can use this store;
    #            subdirectories will not inherit it.
    "scope": "auto",
    # Trust scoring controls for shared chronicle export and ranking.
    "trust": {
        "default_score": 50,
        "chronicle_min_score": 0,
        "lookback_commits": 200,
        "trusted_authors": [],
        "author_weights": {},
    },
}


def find_memory_root(start: Path | None = None) -> Path | None:
    """Walk up from *start* (default: cwd) looking for a .lore directory.

    Resolution order:
    1. ``LORE_ROOT`` environment variable — explicit root pin; the path must
       contain a ``.lore/`` directory or ``None`` is returned.
    2. Walk up from *start* toward the filesystem root.  If a store is found
       in the current directory it is always returned.  If it is found in a
       *parent* directory, the store's ``scope`` config key is checked:
       - ``"auto"`` (default) — inherit the parent store (current behaviour).
       - ``"local"`` — do **not** inherit; return ``None`` so the caller sees
         no active store, preventing unintentional cross-directory bleed.
    """
    # 1. Explicit root override.
    env_root = os.environ.get("LORE_ROOT")
    if env_root:
        p = Path(env_root).resolve()
        return p if (p / MEMORY_DIR).is_dir() else None

    # 2. Walk up the directory tree.
    cwd = (start or Path.cwd()).resolve()
    for parent in [cwd, *cwd.parents]:
        if (parent / MEMORY_DIR).is_dir():
            if parent == cwd:
                # Directly inside the store's own directory — always valid.
                return parent
            # Found in a parent directory; honour the store's scope setting.
            cfg_path = parent / MEMORY_DIR / CONFIG_FILE
            if cfg_path.exists():
                try:
                    with cfg_path.open() as _f:
                        _raw = yaml.safe_load(_f) or {}
                    if _raw.get("scope", "auto") == "local":
                        # Store is local-only; this subdirectory should not
                        # inherit it.  Stop searching — don't walk further up.
                        return None
                except Exception:
                    pass
            return parent
    return None


def memory_dir(root: Path) -> Path:
    return root / MEMORY_DIR


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge *override* into *base*, preserving nested dict keys."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(root: Path) -> dict[str, Any]:
    config_path = memory_dir(root) / CONFIG_FILE
    if config_path.exists():
        with config_path.open() as f:
            loaded = yaml.safe_load(f)
            if loaded:
                # Deep-merge so nested keys (e.g. security.*) are not wiped
                return _deep_merge(DEFAULT_CONFIG, loaded)
    return DEFAULT_CONFIG.copy()


def save_config(root: Path, config: dict[str, Any]) -> None:
    config_path = memory_dir(root) / CONFIG_FILE
    with config_path.open("w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
