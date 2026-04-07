"""Shared association policy and link-application helpers."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import load_config
from .search import suggest_associations
from .store import list_memories, update_memory


def load_association_policy(root: Path) -> dict[str, Any]:
    """Return normalized association policy from config with safe defaults."""
    cfg = load_config(root)
    association = cfg.get("association") or {}
    stages = association.get("stages") or {}
    max_links = association.get("max_links_per_memory", 3)
    auto_min = association.get("auto_apply_min_score", 0.55)
    suggest_min = association.get("suggest_min_score", 0.35)

    try:
        max_links_int = max(1, int(max_links))
    except Exception:
        max_links_int = 3

    try:
        auto_min_float = float(auto_min)
    except Exception:
        auto_min_float = 0.55
    auto_min_float = max(0.0, min(1.0, auto_min_float))

    try:
        suggest_min_float = float(suggest_min)
    except Exception:
        suggest_min_float = 0.35
    suggest_min_float = max(0.0, min(1.0, suggest_min_float))

    return {
        "enabled": bool(association.get("enabled", True)),
        "auto_apply_min_score": auto_min_float,
        "suggest_min_score": suggest_min_float,
        "max_links_per_memory": max_links_int,
        "stages": {
            "add": bool(stages.get("add", True)),
            "edit": bool(stages.get("edit", True)),
            "sync": bool(stages.get("sync", True)),
            "extract": bool(stages.get("extract", True)),
            "watch": bool(stages.get("watch", False)),
        },
    }


def resolve_association_run(
    policy: dict[str, Any],
    *,
    stage: str,
    auto_associate: bool | None,
    associate_top: int | None,
    associate_min_score: float | None,
) -> tuple[bool, int, float]:
    """Resolve effective association run settings for a command stage."""
    stage_enabled = bool((policy.get("stages") or {}).get(stage, False))
    enabled = bool(policy.get("enabled", True))

    resolved_auto = (enabled and stage_enabled) if auto_associate is None else (enabled and auto_associate)

    try:
        resolved_top = int(associate_top) if associate_top is not None else int(policy.get("max_links_per_memory", 3))
    except Exception:
        resolved_top = int(policy.get("max_links_per_memory", 3))
    resolved_top = max(1, resolved_top)

    try:
        if associate_min_score is None:
            resolved_min = float(policy.get("auto_apply_min_score", 0.55))
        else:
            resolved_min = float(associate_min_score)
    except Exception:
        resolved_min = float(policy.get("auto_apply_min_score", 0.55))
    resolved_min = max(0.0, min(1.0, resolved_min))

    return resolved_auto, resolved_top, resolved_min


def suggest_for_entry(
    root: Path,
    *,
    entry_id: str,
    top_k: int,
    min_score: float,
) -> list[dict[str, Any]]:
    """Return ranked association suggestions for a memory entry ID."""
    return suggest_associations(
        root,
        mem_id=entry_id,
        top_k=max(1, int(top_k)),
        min_score=max(0.0, min(1.0, float(min_score))),
    )


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_iso_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        stamp = str(value).strip()
        if stamp.endswith("Z"):
            stamp = stamp[:-1] + "+00:00"
        parsed = datetime.fromisoformat(stamp)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except Exception:
        return None


def _link_age_days(linked_at: str | None, fallback_created_at: str | None) -> float:
    dt = _parse_iso_timestamp(linked_at) or _parse_iso_timestamp(fallback_created_at)
    if dt is None:
        return 10_000.0
    return max(0.0, (datetime.now(timezone.utc) - dt).total_seconds() / 86400.0)


def _compute_confidence_buckets(scores: list[float]) -> dict[str, Any]:
    """Compute edge confidence distribution from list of link scores."""
    if not scores:
        return {"high": 0, "medium": 0, "low": 0, "total": 0, "avg_score": 0.0}
    
    high = sum(1 for s in scores if s >= 0.75)
    medium = sum(1 for s in scores if 0.55 <= s < 0.75)
    low = sum(1 for s in scores if s < 0.55)
    total = len(scores)
    avg_score = round(sum(scores) / total, 4) if total else 0.0
    
    return {
        "high": high,
        "medium": medium,
        "low": low,
        "total": total,
        "avg_score": avg_score,
    }


def apply_related_links(
    root: Path,
    source_id: str,
    target_ids: list[str],
    *,
    source_scores: dict[str, float] | None = None,
    linked_by: str | None = None,
) -> int:
    """Apply bidirectional related_to links and return number of new source links."""
    memories = list_memories(root)
    id_map = {str(m.get("id", "")): m for m in memories if m.get("id")}
    source = id_map.get(source_id)
    if source is None:
        return 0

    current_source = [str(v).strip() for v in (source.get("related_to") or []) if str(v).strip()]
    updated_source = current_source[:]
    source_meta_raw = source.get("related_meta") if isinstance(source.get("related_meta"), dict) else {}
    updated_source_meta = dict(source_meta_raw)
    applied = 0
    now_iso = _iso_now()
    scores = source_scores or {}

    for target_id in target_ids:
        tid = str(target_id).strip()
        if not tid or tid == source_id or tid not in id_map:
            continue
        if tid not in updated_source:
            updated_source.append(tid)
            applied += 1

        source_meta = updated_source_meta.get(tid)
        if not isinstance(source_meta, dict):
            source_meta = {}
        if "linked_at" not in source_meta:
            source_meta["linked_at"] = now_iso
        if tid in scores:
            source_meta["score"] = round(float(scores[tid]), 4)
        if linked_by:
            source_meta["linked_by"] = str(linked_by)
        updated_source_meta[tid] = source_meta

        target = id_map[tid]
        target_related = [str(v).strip() for v in (target.get("related_to") or []) if str(v).strip()]
        target_meta_raw = target.get("related_meta") if isinstance(target.get("related_meta"), dict) else {}
        target_meta = dict(target_meta_raw)
        reverse_meta = target_meta.get(source_id)
        if not isinstance(reverse_meta, dict):
            reverse_meta = {}
        if "linked_at" not in reverse_meta:
            reverse_meta["linked_at"] = now_iso
        if tid in scores:
            reverse_meta["score"] = round(float(scores[tid]), 4)
        if linked_by:
            reverse_meta["linked_by"] = str(linked_by)
        target_meta[source_id] = reverse_meta
        if source_id not in target_related:
            target_related.append(source_id)
        update_memory(root, tid, {"related_to": target_related, "related_meta": target_meta})

    if updated_source != current_source or updated_source_meta != source_meta_raw:
        update_memory(root, source_id, {"related_to": updated_source, "related_meta": updated_source_meta})
    return applied


def audit_graph(root: Path, *, hub_threshold: int = 12) -> dict[str, Any]:
    """Inspect relationship quality and return graph health findings."""
    memories = list_memories(root)
    id_map = {str(m.get("id", "")): m for m in memories if m.get("id")}
    known_ids = set(id_map)

    missing_reverse: list[tuple[str, str]] = []
    dangling_refs: list[tuple[str, str]] = []
    self_links: list[str] = []
    incoming_count: dict[str, int] = {mid: 0 for mid in known_ids}
    confidence_scores: list[float] = []

    for source_id, mem in id_map.items():
        related = [str(v).strip() for v in (mem.get("related_to") or []) if str(v).strip()]
        source_meta = mem.get("related_meta") if isinstance(mem.get("related_meta"), dict) else {}
        for target_id in related:
            if target_id == source_id:
                self_links.append(source_id)
                continue
            if target_id not in known_ids:
                dangling_refs.append((source_id, target_id))
                continue

            incoming_count[target_id] = incoming_count.get(target_id, 0) + 1
            target_meta = source_meta.get(target_id)
            if isinstance(target_meta, dict) and "score" in target_meta:
                confidence_scores.append(float(target_meta.get("score", 0.0)))
            
            target_related = [
                str(v).strip() for v in (id_map[target_id].get("related_to") or []) if str(v).strip()
            ]
            if source_id not in target_related:
                missing_reverse.append((source_id, target_id))

    hubs: list[tuple[str, int]] = []
    for mem_id, mem in id_map.items():
        degree = len([str(v).strip() for v in (mem.get("related_to") or []) if str(v).strip()])
        if degree >= max(1, int(hub_threshold)):
            hubs.append((mem_id, degree))

    orphan_ids = [
        mem_id
        for mem_id, mem in id_map.items()
        if not [str(v).strip() for v in (mem.get("related_to") or []) if str(v).strip()]
        and incoming_count.get(mem_id, 0) == 0
    ]

    confidence_buckets = _compute_confidence_buckets(confidence_scores)

    return {
        "memory_count": len(id_map),
        "missing_reverse": missing_reverse,
        "dangling_refs": dangling_refs,
        "self_links": sorted(set(self_links)),
        "hubs": sorted(hubs, key=lambda item: item[1], reverse=True),
        "orphans": sorted(orphan_ids),
        "confidence_buckets": confidence_buckets,
    }


def relink_memories(
    root: Path,
    *,
    memory_ids: list[str] | None = None,
    top_k: int = 3,
    min_score: float = 0.55,
    apply: bool = False,
) -> dict[str, int]:
    """Recompute related links for selected memories, optionally applying updates."""
    id_filter = {str(mid).strip() for mid in (memory_ids or []) if str(mid).strip()}
    memories = list_memories(root)
    candidates = [m for m in memories if m.get("id") and (not id_filter or str(m.get("id")) in id_filter)]

    scanned = 0
    proposed_links = 0
    applied_links = 0

    for mem in candidates:
        scanned += 1
        mem_id = str(mem.get("id", "")).strip()
        if not mem_id:
            continue

        suggestions = suggest_for_entry(root, entry_id=mem_id, top_k=top_k, min_score=min_score)
        target_ids = [str(item.get("id", "")).strip() for item in suggestions if str(item.get("id", "")).strip()]
        proposed_links += len(target_ids)

        if apply and target_ids:
            score_map = {
                str(item.get("id", "")).strip(): float(item.get("_score", 0.0))
                for item in suggestions
                if str(item.get("id", "")).strip()
            }
            applied_links += apply_related_links(
                root,
                mem_id,
                target_ids,
                source_scores=score_map,
                linked_by="associate-relink",
            )

    return {
        "scanned": scanned,
        "proposed_links": proposed_links,
        "applied_links": applied_links,
    }


def prune_stale_links(
    root: Path,
    *,
    min_score: float = 0.25,
    min_age_days: float = 14.0,
    apply: bool = False,
) -> dict[str, int]:
    """Prune weak old links based on score and age thresholds."""
    memories = list_memories(root)
    id_map = {str(m.get("id", "")): m for m in memories if m.get("id")}
    all_ids = list(id_map.keys())

    scanned = 0
    proposed_removals = 0
    applied_removals = 0

    for source_id in all_ids:
        source = id_map.get(source_id)
        if source is None:
            continue
        related = [str(v).strip() for v in (source.get("related_to") or []) if str(v).strip()]
        if not related:
            continue

        scanned += 1
        source_created = str(source.get("created_at", "") or "")
        source_meta_raw = source.get("related_meta") if isinstance(source.get("related_meta"), dict) else {}
        source_meta = dict(source_meta_raw)

        suggestions = suggest_for_entry(
            root,
            entry_id=source_id,
            top_k=max(len(id_map), 1),
            min_score=0.0,
        )
        score_map = {
            str(item.get("id", "")).strip(): float(item.get("_score", 0.0))
            for item in suggestions
            if str(item.get("id", "")).strip()
        }

        remove_targets: list[str] = []
        for target_id in related:
            score = float(score_map.get(target_id, 0.0))
            meta = source_meta.get(target_id)
            linked_at = meta.get("linked_at") if isinstance(meta, dict) else None
            age_days = _link_age_days(linked_at, source_created)
            if score < float(min_score) and age_days >= float(min_age_days):
                remove_targets.append(target_id)

        if not remove_targets:
            continue

        proposed_removals += len(remove_targets)
        if not apply:
            continue

        new_related = [rid for rid in related if rid not in set(remove_targets)]
        new_meta = {k: v for k, v in source_meta.items() if k in new_related}
        update_memory(root, source_id, {"related_to": new_related, "related_meta": new_meta})
        source["related_to"] = new_related
        source["related_meta"] = new_meta

        applied_removals += len(remove_targets)
        for target_id in remove_targets:
            target = id_map.get(target_id)
            if target is None:
                continue
            target_related = [str(v).strip() for v in (target.get("related_to") or []) if str(v).strip()]
            target_meta_raw = target.get("related_meta") if isinstance(target.get("related_meta"), dict) else {}
            target_meta = dict(target_meta_raw)
            if source_id in target_related:
                target_related = [rid for rid in target_related if rid != source_id]
            if source_id in target_meta:
                target_meta.pop(source_id, None)
            update_memory(root, target_id, {"related_to": target_related, "related_meta": target_meta})
            target["related_to"] = target_related
            target["related_meta"] = target_meta

    return {
        "scanned": scanned,
        "proposed_removals": proposed_removals,
        "applied_removals": applied_removals,
    }


def heal_one_way_links(
    root: Path,
    *,
    apply: bool = False,
) -> dict[str, Any]:
    """Identify and fix one-way links by adding reverse links with same score."""
    memories = list_memories(root)
    id_map = {str(m.get("id", "")): m for m in memories if m.get("id")}
    all_ids = list(id_map.keys())

    scanned = 0
    found_asymmetric = 0
    healed = 0

    for source_id in all_ids:
        source = id_map.get(source_id)
        if source is None:
            continue
        related = [str(v).strip() for v in (source.get("related_to") or []) if str(v).strip()]
        if not related:
            continue

        scanned += 1
        source_meta = source.get("related_meta") if isinstance(source.get("related_meta"), dict) else {}

        asymmetric_targets: list[tuple[str, float]] = []
        for target_id in related:
            if target_id not in id_map:
                continue
            target = id_map[target_id]
            target_related = [str(v).strip() for v in (target.get("related_to") or []) if str(v).strip()]
            
            if source_id not in target_related:
                target_meta = source_meta.get(target_id)
                score = float(target_meta.get("score", 0.5)) if isinstance(target_meta, dict) else 0.5
                asymmetric_targets.append((target_id, score))

        if not asymmetric_targets:
            continue

        found_asymmetric += len(asymmetric_targets)
        if not apply:
            continue

        for target_id, score in asymmetric_targets:
            target_ids = [target_id]
            score_map = {target_id: score}
            healed += apply_related_links(
                root,
                target_id,
                target_ids=[source_id],
                source_scores={source_id: score},
                linked_by="associate-heal",
            )

    return {
        "scanned": scanned,
        "found_asymmetric": found_asymmetric,
        "healed": healed,
    }


def generate_recommendations(
    audit_report: dict[str, Any],
) -> list[tuple[str, str, str]]:
    """Generate actionable recommendations from audit report (priority, action, description)."""
    recommendations: list[tuple[str, str, str]] = []

    dangling_count = len(audit_report.get("dangling_refs", []))
    if dangling_count > 0:
        recommendations.append(
            ("high", "manual-review", f"Found {dangling_count} dangling refs (broken pointers)")
        )

    missing_reverse_count = len(audit_report.get("missing_reverse", []))
    if missing_reverse_count > 0:
        recommendations.append(
            ("high", "associate-heal", f"Found {missing_reverse_count} one-way links fixable by heal")
        )

    self_links = audit_report.get("self_links", [])
    if self_links:
        recommendations.append(
            ("medium", "manual-review", f"Found {len(self_links)} self-referential links")
        )

    orphan_count = len(audit_report.get("orphans", []))
    if orphan_count > 0:
        recommendations.append(
            ("low", "investigate", f"Found {orphan_count} orphan memories (disconnected from graph)")
        )

    buckets = audit_report.get("confidence_buckets", {})
    if buckets.get("total", 0) > 0:
        low_pct = 100 * buckets.get("low", 0) / buckets["total"]
        if low_pct > 25:
            recommendations.append(
                ("medium", "associate-prune", f"{low_pct:.1f}% of links are low-confidence (<0.55)")
            )

    if not recommendations:
        recommendations.append(
            ("info", "none", "Graph looks healthy—no immediate actions required")
        )

    return recommendations


def repair_graph(
    root: Path,
    *,
    apply: bool = False,
) -> dict[str, Any]:
    """Execute full repair workflow: heal one-way links, prune stale, audit result."""
    heal_stats = heal_one_way_links(root, apply=apply)
    prune_stats = prune_stale_links(root, min_score=0.25, min_age_days=14.0, apply=apply)
    audit_report = audit_graph(root)
    recommendations = generate_recommendations(audit_report)

    return {
        "healed": heal_stats["healed"],
        "pruned": prune_stats["applied_removals"],
        "audit": audit_report,
        "recommendations": recommendations,
        "applied": apply,
    }

