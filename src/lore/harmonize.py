"""Harmonize memories into rollups and contradiction reports."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .associations import apply_related_links
from .search import suggest_associations
from .store import add_memory, list_memories

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
    active = [m for m in memories if str(m.get("category", "")) != "instructions"]
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
) -> dict[str, Any]:
    """Persist selected harmonize outputs as summaries.

    Never mutates source memories directly; only appends new summary entries.
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
        "created_rollups": created_rollups,
        "created_resolutions": created_resolutions,
        "linked": linked_count,
        "indexed_pairs": indexed_pairs,
    }
