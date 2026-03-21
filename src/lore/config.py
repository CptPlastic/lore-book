"""Configuration loading and resolution for mem."""
from __future__ import annotations

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

DEFAULT_CONFIG: dict[str, Any] = {
    "version": 1,
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
    """Walk up from *start* (default: cwd) looking for a .lore directory."""
    path = (start or Path.cwd()).resolve()
    for parent in [path, *path.parents]:
        if (parent / MEMORY_DIR).is_dir():
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
