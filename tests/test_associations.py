from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from lore.associations import (
    apply_related_links,
    audit_graph,
    generate_recommendations,
    heal_one_way_links,
    load_association_policy,
    prune_stale_links,
    repair_graph,
    relink_memories,
    resolve_association_run,
    suggest_for_entry,
)
from lore.store import add_memory, init_store, list_memories


class AssociationPolicyTests(unittest.TestCase):
    def test_default_policy_is_loaded(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            init_store(root)

            policy = load_association_policy(root)

            self.assertTrue(policy["enabled"])
            self.assertEqual(policy["max_links_per_memory"], 3)
            self.assertAlmostEqual(policy["auto_apply_min_score"], 0.55)
            self.assertTrue(policy["stages"]["add"])
            self.assertFalse(policy["stages"]["watch"])

    def test_resolve_association_run_clamps_values(self) -> None:
        policy = {
            "enabled": True,
            "auto_apply_min_score": 0.55,
            "max_links_per_memory": 3,
            "stages": {"sync": True},
        }

        should_run, top, min_score = resolve_association_run(
            policy,
            stage="sync",
            auto_associate=None,
            associate_top=0,
            associate_min_score=9.2,
        )

        self.assertTrue(should_run)
        self.assertEqual(top, 1)
        self.assertEqual(min_score, 1.0)


class AssociationLinkingTests(unittest.TestCase):
    def test_apply_related_links_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            init_store(root)

            a = add_memory(root, "facts", "alpha")
            b = add_memory(root, "facts", "beta")

            first = apply_related_links(root, a["id"], [b["id"]])
            second = apply_related_links(root, a["id"], [b["id"]])

            self.assertEqual(first, 1)
            self.assertEqual(second, 0)

            memories = {m["id"]: m for m in list_memories(root)}
            self.assertEqual(memories[a["id"]]["related_to"], [b["id"]])
            self.assertEqual(memories[b["id"]]["related_to"], [a["id"]])

    def test_suggest_for_entry_forwards_clamped_args(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            init_store(root)
            entry = add_memory(root, "facts", "gamma")

            with mock.patch("lore.associations.suggest_associations", return_value=[]) as mocked:
                suggest_for_entry(root, entry_id=entry["id"], top_k=0, min_score=-2.0)

            _, kwargs = mocked.call_args
            self.assertEqual(kwargs["mem_id"], entry["id"])
            self.assertEqual(kwargs["top_k"], 1)
            self.assertEqual(kwargs["min_score"], 0.0)

    def test_audit_graph_detects_orphans_and_dangling(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            init_store(root)

            a = add_memory(root, "facts", "a")
            b = add_memory(root, "facts", "b")

            apply_related_links(root, a["id"], [b["id"]])
            # Force dangling link on source only for audit coverage.
            from lore.store import update_memory

            update_memory(root, a["id"], {"related_to": [b["id"], "missing123"]})

            report = audit_graph(root, hub_threshold=1)

            self.assertIn((a["id"], "missing123"), report["dangling_refs"])
            hub_ids = {mem_id for mem_id, _ in report["hubs"]}
            self.assertIn(a["id"], hub_ids)

    def test_relink_memories_dry_run_and_apply(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            init_store(root)

            a = add_memory(root, "facts", "alpha")
            b = add_memory(root, "facts", "beta")

            with mock.patch(
                "lore.associations.suggest_for_entry",
                return_value=[{"id": b["id"], "_score": 0.9}],
            ):
                dry = relink_memories(root, memory_ids=[a["id"]], top_k=3, min_score=0.5, apply=False)
                self.assertEqual(dry["scanned"], 1)
                self.assertEqual(dry["proposed_links"], 1)
                self.assertEqual(dry["applied_links"], 0)

            with mock.patch(
                "lore.associations.suggest_for_entry",
                return_value=[{"id": b["id"], "_score": 0.9}],
            ):
                applied = relink_memories(root, memory_ids=[a["id"]], top_k=3, min_score=0.5, apply=True)
                self.assertEqual(applied["applied_links"], 1)

            memories = {m["id"]: m for m in list_memories(root)}
            self.assertEqual(memories[a["id"]]["related_to"], [b["id"]])
            self.assertEqual(memories[b["id"]]["related_to"], [a["id"]])

    def test_prune_stale_links_dry_run_and_apply(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            init_store(root)

            a = add_memory(root, "facts", "alpha")
            b = add_memory(root, "facts", "beta")
            apply_related_links(root, a["id"], [b["id"]])

            from lore.store import update_memory

            old_stamp = "2000-01-01T00:00:00+00:00"
            update_memory(root, a["id"], {"related_meta": {b["id"]: {"linked_at": old_stamp, "score": 0.1}}})
            update_memory(root, b["id"], {"related_meta": {a["id"]: {"linked_at": old_stamp, "score": 0.1}}})

            with mock.patch("lore.associations.suggest_for_entry", return_value=[]):
                dry = prune_stale_links(root, min_score=0.5, min_age_days=1, apply=False)
                self.assertEqual(dry["proposed_removals"], 2)
                self.assertEqual(dry["applied_removals"], 0)

            with mock.patch("lore.associations.suggest_for_entry", return_value=[]):
                applied = prune_stale_links(root, min_score=0.5, min_age_days=1, apply=True)
                self.assertEqual(applied["applied_removals"], 1)

            memories = {m["id"]: m for m in list_memories(root)}
            self.assertEqual(memories[a["id"]].get("related_to", []), [])
            self.assertEqual(memories[b["id"]].get("related_to", []), [])

    def test_heal_one_way_links_dry_run_and_apply(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            init_store(root)

            a = add_memory(root, "facts", "alpha")
            b = add_memory(root, "facts", "beta")

            from lore.store import update_memory

            apply_related_links(root, a["id"], [b["id"]])
            update_memory(root, a["id"], {"related_meta": {b["id"]: {"score": 0.8}}})

            memories = list_memories(root)
            # Manually remove reverse link to create asymmetry
            for m in memories:
                if m["id"] == b["id"]:
                    m["related_to"] = []
                    update_memory(root, b["id"], {"related_to": []})
                    break

            dry = heal_one_way_links(root, apply=False)
            self.assertEqual(dry["scanned"], 1)
            self.assertEqual(dry["found_asymmetric"], 1)
            self.assertEqual(dry["healed"], 0)

            applied = heal_one_way_links(root, apply=True)
            self.assertGreater(applied["healed"], 0)

            memories = {m["id"]: m for m in list_memories(root)}
            self.assertIn(a["id"], memories[b["id"]].get("related_to", []))

    def test_audit_graph_computes_confidence_buckets(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            init_store(root)

            a = add_memory(root, "facts", "a")
            b = add_memory(root, "facts", "b")
            c = add_memory(root, "facts", "c")

            from lore.store import update_memory

            apply_related_links(root, a["id"], [b["id"], c["id"]])
            update_memory(
                root,
                a["id"],
                {
                    "related_meta": {
                        b["id"]: {"score": 0.9},
                        c["id"]: {"score": 0.4},
                    }
                },
            )

            report = audit_graph(root)
            buckets = report.get("confidence_buckets", {})

            self.assertGreater(buckets["total"], 0)
            self.assertEqual(buckets["high"], 1)
            self.assertEqual(buckets["low"], 1)
            self.assertGreater(buckets["avg_score"], 0.0)


class AssociationRepairTests(unittest.TestCase):
    def test_generate_recommendations_detects_issues(self) -> None:
        audit_report = {
            "memory_count": 5,
            "dangling_refs": [("a", "missing123")],
            "missing_reverse": [("a", "b"), ("c", "d")],
            "self_links": [],
            "hubs": [],
            "orphans": ["lone"],
            "confidence_buckets": {"high": 1, "medium": 1, "low": 5, "total": 7, "avg_score": 0.4},
        }

        recommendations = generate_recommendations(audit_report)

        priorities = [r[0] for r in recommendations]
        actions = [r[1] for r in recommendations]

        self.assertIn("high", priorities)
        self.assertIn("associate-heal", actions)
        self.assertIn("associate-prune", actions)

    def test_generate_recommendations_all_clear(self) -> None:
        audit_report = {
            "memory_count": 5,
            "dangling_refs": [],
            "missing_reverse": [],
            "self_links": [],
            "hubs": [],
            "orphans": [],
            "confidence_buckets": {"high": 10, "medium": 2, "low": 0, "total": 12, "avg_score": 0.8},
        }

        recommendations = generate_recommendations(audit_report)

        self.assertEqual(len(recommendations), 1)
        self.assertEqual(recommendations[0][0], "info")
        self.assertEqual(recommendations[0][1], "none")

    def test_repair_graph_dry_run_and_apply(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            init_store(root)

            a = add_memory(root, "facts", "alpha")
            b = add_memory(root, "facts", "beta")
            apply_related_links(root, a["id"], [b["id"]])

            from lore.store import update_memory

            update_memory(root, a["id"], {"related_meta": {b["id"]: {"score": 0.1, "linked_at": "2000-01-01T00:00:00+00:00"}}})
            update_memory(root, b["id"], {"related_to": [], "related_meta": {}})

            dry = repair_graph(root, apply=False)
            self.assertFalse(dry["applied"])
            self.assertEqual(dry["healed"], 0)
            self.assertEqual(dry["pruned"], 0)
            self.assertIn("recommendations", dry)

            with mock.patch("lore.associations.suggest_for_entry", return_value=[]):
                applied = repair_graph(root, apply=True)
                self.assertTrue(applied["applied"])
                self.assertGreaterEqual(applied["healed"], 0)


if __name__ == "__main__":
    unittest.main()
