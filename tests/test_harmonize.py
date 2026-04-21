from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from lore.harmonize import apply_harmonize_report, generate_harmonize_report
from lore.store import add_memory, init_store, list_memories


class HarmonizeReportTests(unittest.TestCase):
    def test_detects_negation_contradiction(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            init_store(root)

            add_memory(root, "facts", "Auto export is enabled for this repo")
            add_memory(root, "facts", "Auto export is not enabled for this repo")

            report = generate_harmonize_report(root, contradiction_min_confidence=0.6)

            contradictions = report.get("contradictions", [])
            self.assertGreaterEqual(len(contradictions), 1)
            self.assertEqual(contradictions[0]["type"], "negation")

    def test_rollup_candidates_from_associations(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            init_store(root)

            left = add_memory(root, "facts", "The daemon watches CHRONICLE changes")
            right = add_memory(root, "facts", "The daemon imports CHRONICLE updates")

            with mock.patch(
                "lore.harmonize.suggest_associations",
                return_value=[
                    {
                        "id": right["id"],
                        "_score": 0.88,
                    }
                ],
            ):
                report = generate_harmonize_report(root, min_score=0.5)

            rollups = report.get("rollups", [])
            self.assertEqual(len(rollups), 1)
            self.assertIn(left["id"], rollups[0]["source_ids"])
            self.assertIn(right["id"], rollups[0]["source_ids"])


class HarmonizeApplyTests(unittest.TestCase):
    def test_apply_writes_summary_entries_without_mutating_sources(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            init_store(root)

            left = add_memory(root, "facts", "Feature flag is enabled in production")
            right = add_memory(root, "facts", "Feature flag is disabled in production")

            report = {
                "rollups": [
                    {
                        "content": "Harmonized facts: Feature flag config was updated.",
                        "source_ids": [left["id"], right["id"]],
                    }
                ],
                "resolution_suggestions": [
                    {
                        "content": "Potential contradiction: enable vs disable statements should be dated.",
                        "source_ids": [left["id"], right["id"]],
                    }
                ],
            }

            stats = apply_harmonize_report(
                root,
                report,
                apply_rollups=True,
                apply_resolution_suggestions=True,
                link_sources=True,
            )

            self.assertEqual(stats["created_rollups"], 1)
            self.assertEqual(stats["created_resolutions"], 1)
            self.assertEqual(len(stats["indexed_pairs"]), 2)

            summaries = list_memories(root, "summaries")
            self.assertEqual(len(summaries), 2)

            sources = {m["id"]: m for m in list_memories(root, "facts")}
            self.assertIn(left["id"], sources)
            self.assertIn(right["id"], sources)
            self.assertEqual(
                sources[left["id"]]["content"],
                "Feature flag is enabled in production",
            )
            self.assertEqual(
                sources[right["id"]]["content"],
                "Feature flag is disabled in production",
            )


if __name__ == "__main__":
    unittest.main()
