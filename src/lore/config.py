"""Configuration loading and resolution for mem."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

MEMORY_DIR = ".lore"
CONFIG_FILE = "config.yaml"

DEFAULT_CONFIG: dict[str, Any] = {
    "version": 1,
    "project_description": "",
    "categories": ["decisions", "facts", "preferences", "summaries"],
    "export_targets": {
        "chronicle": True,   # full memory file — lean instruction files reference this
        "agents":    True,
        "copilot":   True,
        "cursor":    True,
        "claude":    True,
        "windsurf":  False,  # opt-in: .windsurfrules for Windsurf/Codeium
        "gemini":    False,  # opt-in: GEMINI.md for Gemini CLI
        "cline":     False,  # opt-in: .clinerules for Cline (VS Code agent)
        "aider":     False,  # opt-in: CONVENTIONS.md for Aider
        "prompt":    True,   # .github/prompts/lore.prompt.md — invokable as /lore
    },
    "embedding_model": "all-MiniLM-L6-v2",
    # Override to point at Artifactory or any HuggingFace-compatible mirror:
    #   model_endpoint: "https://artifactory.example.com/huggingface"
    # Set to false to skip SSL verification (not recommended for prod):
    #   model_ssl_verify: false
    "model_endpoint": None,
    "model_ssl_verify": True,
    # Security preamble injected into all AI context file exports:
    "security": {
        "enabled": False,
        "owasp_top10": True,
        "security_policy": "SECURITY.md",
        "codeowners": True,
        "custom_rules": [],
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
