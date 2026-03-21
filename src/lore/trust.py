"""Trust scoring utilities for lore memories."""
from __future__ import annotations

from pathlib import Path
from typing import Any


def _clamp_score(value: int) -> int:
    return max(0, min(100, value))


def trust_level(score: int) -> str:
    """Return human trust level for a 0-100 score."""
    if score >= 80:
        return "high"
    if score >= 55:
        return "medium"
    return "low"


def memory_trust_score(entry: dict[str, Any], default_score: int = 50) -> int:
    """Read trust_score from an entry, falling back to default."""
    raw = entry.get("trust_score", default_score)
    try:
        return _clamp_score(int(raw))
    except Exception:
        return _clamp_score(default_score)


def _author_activity_bonus(root: Path, lookback_commits: int) -> dict[str, int]:
    """Compute a small bonus per author based on recent commit share."""
    try:
        from git import Repo
        repo = Repo(root, search_parent_directories=True)
    except Exception:
        return {}

    counts: dict[str, int] = {}
    total = 0
    for commit in repo.iter_commits(max_count=max(1, lookback_commits)):
        author = (getattr(commit.author, "name", "") or "").strip()
        if not author:
            continue
        counts[author] = counts.get(author, 0) + 1
        total += 1

    if total == 0:
        return {}

    # Up to +15 for the highest contributors in the lookback window.
    bonuses: dict[str, int] = {}
    for author, count in counts.items():
        share = count / total
        bonuses[author] = round(share * 15)
    return bonuses


def score_memory(
    root: Path,
    entry: dict[str, Any],
    config: dict[str, Any],
    author_activity_bonus: dict[str, int] | None = None,
) -> tuple[int, list[str]]:
    """Compute trust score/reasons for a memory entry."""
    trust_cfg = config.get("trust", {})
    score = int(trust_cfg.get("default_score", 50))
    reasons: list[str] = [f"base={score}"]

    trusted_authors = set(trust_cfg.get("trusted_authors", []) or [])
    author_weights = trust_cfg.get("author_weights", {}) or {}
    lookback = int(trust_cfg.get("lookback_commits", 200) or 200)

    author = (entry.get("git_author") or "").strip()
    if author:
        score += 5
        reasons.append("has-git-author:+5")

        if author in trusted_authors:
            score += 20
            reasons.append("trusted-author:+20")

        if author in author_weights:
            try:
                delta = int(author_weights[author])
            except Exception:
                delta = 0
            delta = max(-40, min(40, delta))
            score += delta
            reasons.append(f"author-weight:{delta:+d}")

        bonuses = author_activity_bonus or _author_activity_bonus(root, lookback)
        activity_bonus = bonuses.get(author, 0)
        if activity_bonus:
            score += activity_bonus
            reasons.append(f"author-activity:+{activity_bonus}")

    source = (entry.get("source") or "").strip().lower()
    if source.startswith("git:"):
        score += 10
        reasons.append("git-derived:+10")

    tags = set(entry.get("tags", []) or [])
    if "verified" in tags:
        score += 20
        reasons.append("tag-verified:+20")
    if "needs-review" in tags:
        score -= 20
        reasons.append("tag-needs-review:-20")
    if "deprecated" in tags:
        score -= 30
        reasons.append("tag-deprecated:-30")

    final = _clamp_score(score)
    return final, reasons


def build_author_activity_bonus(root: Path, config: dict[str, Any]) -> dict[str, int]:
    """Precompute author activity bonuses from repository history."""
    trust_cfg = config.get("trust", {})
    lookback = int(trust_cfg.get("lookback_commits", 200) or 200)
    return _author_activity_bonus(root, lookback)
