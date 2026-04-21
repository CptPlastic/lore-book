"""Harmonize memories into rollups and contradiction reports."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any
import urllib.request

from .associations import apply_related_links
from .search import suggest_associations
from .store import add_memory, list_memories, remove_memory, update_memory

_NEGATION_TOKENS = {
    "not",
    "no",
    "never",
    "without",
    "cannot",
    "cant",
    "disabled",
    "disable",
    "false",
    "off",
    "deny",
}

_STOP_TOKENS = {
    "the",
    "a",
    "an",
    "is",
    "are",
    "to",
    "for",
    "of",
    "and",
    "or",
    "in",
    "on",
    "with",
    "be",
    "this",
    "that",
    "it",
    "as",
    "by",
    "from",
}

_NUMBER_RE = re.compile(r"\b\d+(?:\.\d+)?\b")


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _content_signature(text: str) -> set[str]:
    return {t for t in _tokenize(text) if t not in _STOP_TOKENS and len(t) > 2}


def _normalize_whitespace(text: str) -> str:
    return " ".join(str(text).split()).strip()


def _number_values(text: str) -> set[str]:
    return set(_NUMBER_RE.findall(text))


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def _has_negation(tokens: set[str]) -> bool:
    return bool(tokens & _NEGATION_TOKENS)


def _negation_conflict(a_text: str, b_text: str) -> tuple[bool, float, str]:
    a_sig = _content_signature(a_text)
    b_sig = _content_signature(b_text)
    overlap = _jaccard(a_sig, b_sig)
    if overlap < 0.45:
        return (False, 0.0, "")

    a_neg = _has_negation(a_sig)
    b_neg = _has_negation(b_sig)
    if a_neg == b_neg:
        return (False, 0.0, "")

    confidence = min(0.95, round(0.62 + overlap * 0.3, 4))
    return (True, confidence, "negation")


def _numeric_conflict(a_text: str, b_text: str) -> tuple[bool, float, str]:
    a_nums = _number_values(a_text)
    b_nums = _number_values(b_text)
    if not a_nums or not b_nums or a_nums == b_nums:
        return (False, 0.0, "")

    a_sig = _content_signature(a_text)
    b_sig = _content_signature(b_text)
    overlap = _jaccard(a_sig, b_sig)
    if overlap < 0.4:
        return (False, 0.0, "")

    confidence = min(0.9, round(0.58 + overlap * 0.32, 4))
    return (True, confidence, "numeric")


def _polarity_conflict(a_text: str, b_text: str) -> tuple[bool, float, str]:
    a = set(_tokenize(a_text))
    b = set(_tokenize(b_text))

    enabled_disabled = (("enable" in a or "enabled" in a) and ("disable" in b or "disabled" in b)) or (
        ("enable" in b or "enabled" in b) and ("disable" in a or "disabled" in a)
    )

    true_false = ("true" in a and "false" in b) or ("true" in b and "false" in a)
    if not enabled_disabled and not true_false:
        return (False, 0.0, "")

    a_sig = _content_signature(a_text)
    b_sig = _content_signature(b_text)
    overlap = _jaccard(a_sig, b_sig)
    if overlap < 0.35:
        return (False, 0.0, "")

    confidence = min(0.92, round(0.6 + overlap * 0.28, 4))
    return (True, confidence, "polarity")


def _preview(text: str, limit: int = 120) -> str:
    compact = _normalize_whitespace(text)
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "..."


def _build_rollup_content(entries: list[dict[str, Any]], category: str) -> str:
    snippets: list[str] = []
    for item in entries[:3]:
        content = _normalize_whitespace(str(item.get("content", "")))
        if not content:
            continue
        snippets.append(content.rstrip("."))
    lead = f"Harmonized {category}"
    if not snippets:
        return f"{lead}."
    return f"{lead}: " + "; ".join(snippets) + "."


def _build_resolution_suggestion(contradiction: dict[str, Any]) -> str:
    conflict_type = contradiction.get("type", "conflict")
    a_text = _normalize_whitespace(str(contradiction.get("left_content", "")))
    b_text = _normalize_whitespace(str(contradiction.get("right_content", "")))
    return (
        "Potential contradiction ("
        + str(conflict_type)
        + "): "
        + _preview(a_text, 90)
        + " <-> "
        + _preview(b_text, 90)
        + ". Consider adding one canonical statement with date/scope/trust context."
    )


def _is_harmonize_generated(mem: dict[str, Any]) -> bool:
    source = str(mem.get("source", "")).strip().lower()
    return source.startswith("harmonize:")


def _build_snapshot_content(
    report: dict[str, Any],
    *,
    max_themes: int = 6,
    max_contradictions: int = 4,
) -> str:
    memory_count = int(report.get("memory_count", 0) or 0)
    rollups = list(report.get("rollups", []))
    contradictions = list(report.get("contradictions", []))

    lines: list[str] = [f"Memory snapshot: {memory_count} memories scanned."]

    if rollups:
        lines.append("Top themes:")
        for item in rollups[: max(1, int(max_themes))]:
            score = float(item.get("score", 0.0))
            content = _normalize_whitespace(str(item.get("content", "")))
            if not content:
                continue
            lines.append(f"- [{score:.2f}] {_preview(content, 180)}")
    else:
        lines.append("Top themes: none identified yet.")

    lines.append(f"Contradictions: {len(contradictions)} potential issues.")
    if contradictions:
        lines.append("Watch list:")
        for item in contradictions[: max(1, int(max_contradictions))]:
            confidence = float(item.get("confidence", 0.0))
            left = _preview(str(item.get("left_content", "")), 85)
            right = _preview(str(item.get("right_content", "")), 85)
            lines.append(f"- [{confidence:.2f}] {left} <-> {right}")

    return "\n".join(lines).strip()


def _build_ai_snapshot_content(
    report: dict[str, Any],
    *,
    ai_summary_config: dict[str, Any],
) -> str | None:
    if not bool(ai_summary_config.get("enabled", False)):
        return None

    api_key = str(
        ai_summary_config.get("api_key")
        or os.environ.get("LORE_AI_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or ""
    ).strip()
    if not api_key:
        return None

    base_url = str(
        ai_summary_config.get("base_url")
        or os.environ.get("LORE_AI_BASE_URL")
        or os.environ.get("OPENAI_BASE_URL")
        or "https://api.openai.com/v1"
    ).strip().rstrip("/")
    model = str(ai_summary_config.get("model") or "gpt-4o-mini").strip()
    timeout_seconds = max(2, int(ai_summary_config.get("timeout_seconds", 12)))
    max_output_tokens = max(80, int(ai_summary_config.get("max_output_tokens", 260)))
    max_chars = max(200, int(ai_summary_config.get("max_chars", 1400)))

    rollups = list(report.get("rollups", []))
    contradictions = list(report.get("contradictions", []))

    context_payload = {
        "memory_count": int(report.get("memory_count", 0) or 0),
        "rollups": [
            {
                "score": round(float(item.get("score", 0.0)), 3),
                "category": str(item.get("category", "")),
                "content": _normalize_whitespace(str(item.get("content", ""))),
            }
            for item in rollups[:8]
        ],
        "contradictions": [
            {
                "confidence": round(float(item.get("confidence", 0.0)), 3),
                "type": str(item.get("type", "")),
                "left": _normalize_whitespace(str(item.get("left_content", ""))),
                "right": _normalize_whitespace(str(item.get("right_content", ""))),
            }
            for item in contradictions[:6]
        ],
    }

    prompt = (
        "Write a clean memory digest for engineers. "
        "Keep it concise and practical. "
        "Use this exact structure: "
        "first line 'Memory snapshot: <N> memories scanned.'; "
        "then section 'Top themes:' with 3-6 bullets; "
        "then section 'Contradictions: <count> potential issues.'; "
        "if contradictions exist, include 'Watch list:' with up to 4 bullets. "
        "No extra sections, no markdown heading levels, no code fences."
    )

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You produce short, neutral operational summaries.",
            },
            {
                "role": "user",
                "content": prompt + "\n\nData:\n" + json.dumps(context_payload, ensure_ascii=True),
            },
        ],
        "temperature": 0.2,
        "max_tokens": max_output_tokens,
    }

    req = urllib.request.Request(
        url=f"{base_url}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=float(timeout_seconds)) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        data = json.loads(raw)
        choices = data.get("choices") if isinstance(data, dict) else None
        if not isinstance(choices, list) or not choices:
            return None
        message = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
        content = message.get("content", "")
        if not isinstance(content, str):
            return None
        lines = [line.rstrip() for line in content.splitlines() if line.strip()]
        out = "\n".join(lines).strip()
        if not out:
            return None
        if len(out) > max_chars:
            out = out[: max_chars - 1].rstrip() + "..."
        return out
    except Exception:
        return None


def _resolve_snapshot_content(
    report: dict[str, Any],
    *,
    ai_summary_config: dict[str, Any] | None,
) -> tuple[str, bool]:
    fallback = _build_snapshot_content(report)
    if not ai_summary_config:
        return fallback, False
    ai_version = _build_ai_snapshot_content(report, ai_summary_config=ai_summary_config)
    if not ai_version:
        return fallback, False
    return ai_version, True


def generate_harmonize_report(
    root: Path,
    *,
    top_k: int = 3,
    min_score: float = 0.62,
    max_rollups: int = 20,
    contradiction_min_confidence: float = 0.67,
    include_resolution_suggestions: bool = True,
) -> dict[str, Any]:
    """Generate rollup and contradiction report without mutating memories."""
    memories = list_memories(root)
    active = [
        m
        for m in memories
        if str(m.get("category", "")) != "instructions" and not _is_harmonize_generated(m)
    ]
    id_map = {str(m.get("id", "")): m for m in active if m.get("id")}

    rollups: list[dict[str, Any]] = []
    seen_clusters: set[frozenset[str]] = set()

    for mem in active:
        mem_id = str(mem.get("id", "")).strip()
        if not mem_id:
            continue
        suggestions = suggest_associations(root, mem_id=mem_id, top_k=max(1, top_k), min_score=float(min_score))
        for item in suggestions:
            target_id = str(item.get("id", "")).strip()
            if not target_id or target_id not in id_map:
                continue
            cluster_ids = frozenset({mem_id, target_id})
            if cluster_ids in seen_clusters:
                continue
            seen_clusters.add(cluster_ids)

            members = [id_map[mid] for mid in sorted(cluster_ids) if mid in id_map]
            category = str(mem.get("category", "facts"))
            if len(members) < 2:
                continue
            rollups.append(
                {
                    "category": category,
                    "source_ids": sorted(cluster_ids),
                    "score": round(float(item.get("_score", 0.0)), 4),
                    "content": _build_rollup_content(members, category),
                    "evidence": [_preview(str(m.get("content", "")), 120) for m in members],
                }
            )

    rollups.sort(key=lambda item: float(item.get("score", 0.0)), reverse=True)
    rollups = rollups[: max(1, int(max_rollups))]

    contradictions: list[dict[str, Any]] = []
    contradiction_seen: set[tuple[str, str, str]] = set()
    by_category: dict[str, list[dict[str, Any]]] = {}
    for mem in active:
        cat = str(mem.get("category", "facts"))
        by_category.setdefault(cat, []).append(mem)

    for category, entries in by_category.items():
        n = len(entries)
        for i in range(n):
            left = entries[i]
            left_id = str(left.get("id", "")).strip()
            left_content = _normalize_whitespace(str(left.get("content", "")))
            if not left_id or not left_content:
                continue
            for j in range(i + 1, n):
                right = entries[j]
                right_id = str(right.get("id", "")).strip()
                right_content = _normalize_whitespace(str(right.get("content", "")))
                if not right_id or not right_content:
                    continue
                if left_content == right_content:
                    continue

                checks = [
                    _negation_conflict(left_content, right_content),
                    _numeric_conflict(left_content, right_content),
                    _polarity_conflict(left_content, right_content),
                ]
                for ok, confidence, reason in checks:
                    if not ok or confidence < contradiction_min_confidence:
                        continue
                    key = tuple(sorted([left_id, right_id]) + [reason])
                    if key in contradiction_seen:
                        continue
                    contradiction_seen.add(key)
                    contradictions.append(
                        {
                            "category": category,
                            "left_id": left_id,
                            "right_id": right_id,
                            "left_content": left_content,
                            "right_content": right_content,
                            "type": reason,
                            "confidence": round(confidence, 4),
                        }
                    )

    contradictions.sort(key=lambda item: float(item.get("confidence", 0.0)), reverse=True)

    resolution_suggestions: list[dict[str, Any]] = []
    if include_resolution_suggestions:
        for contradiction in contradictions:
            resolution_suggestions.append(
                {
                    "category": "summaries",
                    "source_ids": [contradiction["left_id"], contradiction["right_id"]],
                    "confidence": contradiction["confidence"],
                    "content": _build_resolution_suggestion(contradiction),
                }
            )

    return {
        "memory_count": len(active),
        "rollups": rollups,
        "contradictions": contradictions,
        "resolution_suggestions": resolution_suggestions,
    }


def apply_harmonize_report(
    root: Path,
    report: dict[str, Any],
    *,
    apply_rollups: bool,
    apply_resolution_suggestions: bool,
    link_sources: bool = True,
    mode: str = "snapshot",
    prune_legacy_harmonize: bool = True,
    ai_summary_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Persist selected harmonize outputs as summaries.

    Never mutates source memories directly.
    Default mode is ``snapshot`` to keep one concise, continuously updated summary.
    """
    existing_summaries = list_memories(root, "summaries")
    existing_content = {
        _normalize_whitespace(str(item.get("content", ""))).casefold()
        for item in existing_summaries
        if str(item.get("content", "")).strip()
    }

    indexed_pairs: list[tuple[str, str]] = []
    created_rollups = 0
    created_resolutions = 0
    linked_count = 0
    removed_legacy = 0
    ai_used = False

    normalized_mode = str(mode or "snapshot").strip().lower()
    if normalized_mode not in {"snapshot", "append"}:
        normalized_mode = "snapshot"

    if normalized_mode == "snapshot":
        snapshot_content, ai_used = _resolve_snapshot_content(
            report,
            ai_summary_config=ai_summary_config,
        )
        snapshot_entry = None
        for item in existing_summaries:
            if str(item.get("source", "")).strip().lower() == "harmonize:snapshot":
                snapshot_entry = item
                break

        if snapshot_entry is None:
            entry = add_memory(
                root,
                "summaries",
                snapshot_content,
                tags=["harmonized", "snapshot", "auto"],
                source="harmonize:snapshot",
            )
            created_rollups = 1
            indexed_pairs.append((entry["id"], snapshot_content))
            snapshot_id = str(entry.get("id", "")).strip()
        else:
            snapshot_id = str(snapshot_entry.get("id", "")).strip()
            current = _normalize_whitespace(str(snapshot_entry.get("content", "")))
            if current != snapshot_content:
                updated = update_memory(
                    root,
                    snapshot_id,
                    {
                        "content": snapshot_content,
                        "tags": ["harmonized", "snapshot", "auto"],
                        "source": "harmonize:snapshot",
                    },
                )
                if updated is not None:
                    indexed_pairs.append((snapshot_id, snapshot_content))

        if prune_legacy_harmonize:
            for item in existing_summaries:
                source = str(item.get("source", "")).strip().lower()
                item_id = str(item.get("id", "")).strip()
                if not item_id:
                    continue
                if source.startswith("harmonize:") and source != "harmonize:snapshot":
                    if remove_memory(root, item_id):
                        removed_legacy += 1

        if link_sources and snapshot_id:
            source_ids: list[str] = []
            for rollup in report.get("rollups", []):
                for sid in rollup.get("source_ids", []):
                    item = str(sid).strip()
                    if item and item not in source_ids:
                        source_ids.append(item)
            for contradiction in report.get("contradictions", []):
                for sid in (contradiction.get("left_id"), contradiction.get("right_id")):
                    item = str(sid).strip()
                    if item and item not in source_ids:
                        source_ids.append(item)
            if source_ids:
                linked_count += apply_related_links(
                    root,
                    snapshot_id,
                    source_ids,
                    linked_by="harmonize-snapshot",
                )

        return {
            "mode": "snapshot",
            "ai_used": ai_used,
            "created_rollups": created_rollups,
            "created_resolutions": created_resolutions,
            "linked": linked_count,
            "removed_legacy": removed_legacy,
            "indexed_pairs": indexed_pairs,
        }

    if apply_rollups:
        for rollup in report.get("rollups", []):
            content = _normalize_whitespace(str(rollup.get("content", "")))
            if not content:
                continue
            key = content.casefold()
            if key in existing_content:
                continue
            entry = add_memory(
                root,
                "summaries",
                content,
                tags=["harmonized", "rollup", "auto"],
                source="harmonize:rollup",
            )
            indexed_pairs.append((entry["id"], content))
            existing_content.add(key)
            created_rollups += 1
            if link_sources:
                linked_count += apply_related_links(
                    root,
                    str(entry["id"]),
                    [str(item).strip() for item in rollup.get("source_ids", []) if str(item).strip()],
                    linked_by="harmonize-rollup",
                )

    if apply_resolution_suggestions:
        for suggestion in report.get("resolution_suggestions", []):
            content = _normalize_whitespace(str(suggestion.get("content", "")))
            if not content:
                continue
            key = content.casefold()
            if key in existing_content:
                continue
            entry = add_memory(
                root,
                "summaries",
                content,
                tags=["harmonized", "resolution", "auto"],
                source="harmonize:resolution",
            )
            indexed_pairs.append((entry["id"], content))
            existing_content.add(key)
            created_resolutions += 1
            if link_sources:
                linked_count += apply_related_links(
                    root,
                    str(entry["id"]),
                    [str(item).strip() for item in suggestion.get("source_ids", []) if str(item).strip()],
                    linked_by="harmonize-resolution",
                )

    return {
        "mode": "append",
        "ai_used": ai_used,
        "created_rollups": created_rollups,
        "created_resolutions": created_resolutions,
        "linked": linked_count,
        "removed_legacy": removed_legacy,
        "indexed_pairs": indexed_pairs,
    }


def write_copilot_harmonize_artifacts(root: Path, report: dict[str, Any]) -> dict[str, str]:
    """Write Copilot-friendly harmonize context + slash prompt files.

    This does not call any external model directly; it prepares artifacts for
    Copilot Chat so users can ask for a polished final summary interactively.
    """
    memory_count = int(report.get("memory_count", 0) or 0)
    rollups = list(report.get("rollups", []))
    contradictions = list(report.get("contradictions", []))

    context_lines: list[str] = [
        "# Harmonize Context",
        "",
        f"Memories scanned: {memory_count}",
        f"Rollup candidates: {len(rollups)}",
        f"Contradictions: {len(contradictions)}",
        "",
        "## Top Themes",
    ]

    if rollups:
        for item in rollups[:8]:
            context_lines.append(
                f"- [{float(item.get('score', 0.0)):.2f}] {_preview(str(item.get('content', '')), 200)}"
            )
    else:
        context_lines.append("- None detected")

    context_lines.extend(["", "## Contradiction Watch List"])
    if contradictions:
        for item in contradictions[:6]:
            context_lines.append(
                "- "
                + f"[{float(item.get('confidence', 0.0)):.2f}] "
                + _preview(str(item.get("left_content", "")), 90)
                + " <-> "
                + _preview(str(item.get("right_content", "")), 90)
            )
    else:
        context_lines.append("- None detected")

    context_path = root / ".lore" / "reports" / "harmonize-context.md"
    context_path.parent.mkdir(parents=True, exist_ok=True)
    context_path.write_text("\n".join(context_lines).strip() + "\n")

    prompt_path = root / ".github" / "prompts" / "harmonize.prompt.md"
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(
        "---\n"
        "mode: 'ask'\n"
        "description: 'Create a clean project memory summary from harmonize output'\n"
        "---\n\n"
        "Read CHRONICLE.md and .lore/reports/harmonize-context.md, then produce a concise memory digest.\n"
        "Use this exact shape:\n"
        "1) Snapshot (2-3 lines)\n"
        "2) Top themes (3-6 bullets)\n"
        "3) Contradictions watch list (0-4 bullets)\n"
        "4) Suggested canonical updates (2-4 bullets, concrete and actionable)\n"
        "Keep wording tight, avoid repeating near-duplicate items, and prioritize recency and trust.\n"
    )

    return {
        "context_path": str(context_path),
        "prompt_path": str(prompt_path),
    }
