"""Git history extraction — pull memory candidates from commits and diffs."""
from __future__ import annotations

from pathlib import Path
from typing import Any


def _is_git_repo(root: Path) -> bool:
    return (root / ".git").is_dir()


# Files lore writes itself — commits that only touch these are noise, not memory.
_LORE_OUTPUT_FILES: frozenset[str] = frozenset({
    "CHRONICLE.md",
    "AGENTS.md",
    "CLAUDE.md",
    "GEMINI.md",
    "CONVENTIONS.md",
    ".windsurfrules",
    ".clinerules",
    ".github/copilot-instructions.md",
    ".github/prompts/lore.prompt.md",
    ".cursor/rules/memory.md",
})


def _is_lore_only_commit(commit) -> bool:
    """True if a commit touches only lore-managed output files (export noise)."""
    try:
        changed = set(commit.stats.files.keys())
    except Exception:
        return False
    return bool(changed) and changed.issubset(_LORE_OUTPUT_FILES)


def git_context(root: Path) -> dict[str, Any]:
    """Return a dict of useful git metadata for the repo at *root*.

    Keys (all optional — absent if not in a git repo or git call fails):
      branch       current branch name (str)
      author       git config user.name (str)
      remote_name  name parsed from origin remote URL (str)
      last_sha     HEAD commit hex sha, 8 chars (str)
      last_msg     HEAD commit message, first line (str)
    """
    if not _is_git_repo(root):
        return {}
    try:
        from git import Repo, InvalidGitRepositoryError
        repo = Repo(root, search_parent_directories=True)
    except Exception:
        return {}

    ctx: dict[str, Any] = {}

    # Branch
    try:
        ctx["branch"] = repo.active_branch.name
    except TypeError:
        ctx["branch"] = "HEAD"  # detached HEAD state

    # Author (git config user.name)
    try:
        ctx["author"] = repo.config_reader().get_value("user", "name", default="") or None
        if ctx["author"] is None:
            del ctx["author"]
    except Exception:
        pass

    # Remote name (parse from origin URL: github.com/org/repo → repo)
    try:
        origin = repo.remotes["origin"].url
        # strip .git suffix and take the last path segment
        name = origin.rstrip("/").rstrip(".git").split("/")[-1]
        if name.endswith(".git"):
            name = name[:-4]
        if name:
            ctx["remote_name"] = name
    except Exception:
        pass

    # Last commit
    try:
        head = repo.head.commit
        ctx["last_sha"] = head.hexsha[:8]
        ctx["last_msg"] = head.message.strip().splitlines()[0]
    except Exception:
        pass

    return ctx


def extract_from_git(
    root: Path,
    n_commits: int = 20,
) -> list[dict]:
    """
    Scan the last *n_commits* commits and return a list of memory candidates.
    Each candidate is a dict with keys: category, content, source, commit_sha.
    """
    try:
        from git import Repo
    except ImportError:
        raise RuntimeError("gitpython is required. Run: pip install gitpython")

    try:
        repo = Repo(root, search_parent_directories=True)
    except Exception:
        raise RuntimeError(f"No git repository found at or above {root}")

    from .config import load_config
    cfg = load_config(root)
    patterns = cfg.get("extraction_patterns", [])

    candidates: list[dict] = []
    for commit in repo.iter_commits(max_count=n_commits):
        if len(commit.parents) > 1:  # skip merge commits
            continue
        if _is_lore_only_commit(commit):  # skip lore export-only commits
            continue
        sha = commit.hexsha[:8]
        _extract_message(commit.message.strip(), sha, candidates, patterns)
        _extract_diff_comments(commit, sha, candidates)
    return candidates


def _extract_message(msg: str, sha: str, candidates: list[dict], patterns: list | None = None) -> None:
    import re
    if len(msg) > 10:
        category = _categorize_message(msg)
        if patterns:
            for pat in patterns:
                if not pat.get("enabled", True):
                    continue
                try:
                    pat_type = pat.get("type", "prefix").lower()
                    pat_str = pat.get("pattern", "")
                    if pat_type == "regex" and re.search(pat_str, msg):
                        category = pat.get("category", category)
                        break
                    elif pat_type == "prefix" and msg.lower().startswith(pat_str.lower()):
                        category = pat.get("category", category)
                        break
                except Exception:
                    pass
        candidates.append({
            "category": category,
            "content": msg,
            "source": f"git:{sha}",
            "commit_sha": sha,
        })


def _extract_diff_comments(commit, sha: str, candidates: list[dict]) -> None:
    if not commit.parents:
        return
    try:
        diffs = commit.diff(commit.parents[0], create_patch=True)
    except Exception:
        return
    for d in diffs:
        if not d.diff:
            continue
        text = d.diff.decode("utf-8", errors="replace")
        for line in text.splitlines():
            if not line.startswith("+") or line.startswith("++"):
                continue
            body = line[1:].strip()
            if _looks_like_decision(body):
                candidates.append({
                    "category": "decisions",
                    "content": body,
                    "source": f"git:{sha}:{d.b_path}",
                    "commit_sha": sha,
                })


def _categorize_message(msg: str) -> str:
    lower = msg.lower()
    if lower.startswith(("feat", "add", "new")):
        return "facts"
    if lower.startswith(("fix", "bug")):
        return "facts"
    if lower.startswith(("refactor", "perf", "improve")):
        return "decisions"
    if lower.startswith(("docs", "readme")):
        return "summaries"
    return "facts"


def _looks_like_decision(line: str) -> bool:
    """Heuristic: long comment lines that contain rationale keywords."""
    if len(line) < 30:
        return False
    decision_words = [
        "because", "decided", "chose", "use ", "avoid", "prefer",
        "note:", "todo:", "reason:", "rationale",
    ]
    lower = line.lower()
    comment_starters = ("#", "//", "/*", " *", "--")
    if not any(lower.startswith(s) for s in comment_starters):
        return False
    return any(w in lower for w in decision_words)


def install_git_hook(root: Path, auto_export: bool = False) -> Path:
    """Write a post-commit hook that auto-extracts memories after each commit.

    The hook runs in the background so git commits return instantly.
    Output is appended to ~/.lore-hook.log for inspection if needed.
    """
    if not _is_git_repo(root):
        raise RuntimeError(f"{root} is not a git repository (no .git directory found)")

    hooks_dir = root / ".git" / "hooks"
    hooks_dir.mkdir(exist_ok=True)
    hook_path = hooks_dir / "post-commit"

    if auto_export:
        cmd = "lore extract --last 1 --auto --export"
    else:
        cmd = "lore extract --last 1 --auto"

    lines = [
        "#!/bin/sh",
        "# Installed by lore -- https://github.com/HORIZON/memory",
        "# Runs in background so commits return instantly.",
        "# Re-entry guard: avoids recursive runs when multiple lore hooks are installed.",
        "(if [ \"${LORE_HOOK_ACTIVE:-}\" = \"1\" ]; then exit 0; fi; "
        "if ! mkdir .git/.lore-hook.lock 2>/dev/null; then exit 0; fi; "
        "trap 'rmdir .git/.lore-hook.lock 2>/dev/null' EXIT INT TERM; "
        f'LORE_HOOK_ACTIVE=1 {cmd} >> "$HOME/.lore-hook.log" 2>&1) &',
        "",  # trailing newline
    ]

    hook_path.write_text("\n".join(lines))
    hook_path.chmod(0o755)
    return hook_path


def uninstall_git_hook(root: Path) -> bool:
    """Remove the lore-managed post-commit hook.

    Returns True if it was found and removed, False if there was nothing to remove.
    Raises RuntimeError if the hook exists but was not installed by lore (safety guard).
    """
    if not _is_git_repo(root):
        raise RuntimeError(f"{root} is not a git repository")
    hook_path = root / ".git" / "hooks" / "post-commit"
    if not hook_path.exists():
        return False
    content = hook_path.read_text()
    if "# Installed by lore" not in content:
        raise RuntimeError(
            "The post-commit hook was not installed by lore — refusing to remove it.\n"
            f"Edit it manually: {hook_path}"
        )
    hook_path.unlink()
    return True


def install_post_merge_sync_hook(root: Path) -> Path:
    """Write a post-merge hook that syncs CHRONICLE updates into .lore.

    The hook only runs sync when CHRONICLE.md changed in the merge.
    """
    if not _is_git_repo(root):
        raise RuntimeError(f"{root} is not a git repository (no .git directory found)")

    hooks_dir = root / ".git" / "hooks"
    hooks_dir.mkdir(exist_ok=True)
    hook_path = hooks_dir / "post-merge"

    lines = [
        "#!/bin/sh",
        "# Installed by lore -- chronicle sync",
        "# Re-entry guard: avoids recursive runs when multiple lore hooks are installed.",
        "if [ \"${LORE_HOOK_ACTIVE:-}\" = \"1\" ]; then exit 0; fi",
        "if ! mkdir .git/.lore-hook.lock 2>/dev/null; then exit 0; fi",
        "trap 'rmdir .git/.lore-hook.lock 2>/dev/null' EXIT INT TERM",
        "if git diff --name-only ORIG_HEAD HEAD | grep -q '^CHRONICLE.md$'; then",
        "  LORE_HOOK_ACTIVE=1 lore sync --no-export >/dev/null 2>&1",
        "  LORE_HOOK_ACTIVE=1 lore export >/dev/null 2>&1",
        "fi",
        "",  # trailing newline
    ]

    hook_path.write_text("\n".join(lines))
    hook_path.chmod(0o755)
    return hook_path


def uninstall_post_merge_sync_hook(root: Path) -> bool:
    """Remove the lore-managed post-merge sync hook."""
    if not _is_git_repo(root):
        raise RuntimeError(f"{root} is not a git repository")
    hook_path = root / ".git" / "hooks" / "post-merge"
    if not hook_path.exists():
        return False
    content = hook_path.read_text()
    if "# Installed by lore -- chronicle sync" not in content:
        raise RuntimeError(
            "The post-merge hook was not installed by lore — refusing to remove it.\n"
            f"Edit it manually: {hook_path}"
        )
    hook_path.unlink()
    return True
