"""Git history extraction — pull memory candidates from commits and diffs."""
from __future__ import annotations

from pathlib import Path


def _is_git_repo(root: Path) -> bool:
    return (root / ".git").is_dir()


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

    candidates: list[dict] = []
    for commit in repo.iter_commits(max_count=n_commits):
        if len(commit.parents) > 1:  # skip merge commits
            continue
        sha = commit.hexsha[:8]
        _extract_message(commit.message.strip(), sha, candidates)
        _extract_diff_comments(commit, sha, candidates)
    return candidates


def _extract_message(msg: str, sha: str, candidates: list[dict]) -> None:
    if len(msg) > 10:
        candidates.append({
            "category": _categorize_message(msg),
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
        f'({cmd} >> "$HOME/.lore-hook.log" 2>&1) &',
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
