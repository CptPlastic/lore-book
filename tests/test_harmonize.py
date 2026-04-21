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
    def test_apply_writes_single_snapshot_without_mutating_sources(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            init_store(root)

            left = add_memory(root, "facts", "Feature flag is enabled in production")
            right = add_memory(root, "facts", "Feature flag is disabled in production")
            add_memory(
                root,
                "summaries",
                "Harmonized facts: stale rollup that should be removed",
                source="harmonize:rollup",
            )

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
            self.assertEqual(stats["created_resolutions"], 0)
            self.assertEqual(len(stats["indexed_pairs"]), 1)
            self.assertEqual(stats["mode"], "snapshot")
            self.assertGreaterEqual(stats["removed_legacy"], 1)

            summaries = list_memories(root, "summaries")
            self.assertEqual(len(summaries), 1)
            self.assertEqual(summaries[0].get("source"), "harmonize:snapshot")
            self.assertIn("Memory snapshot:", summaries[0].get("content", ""))

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

    def test_apply_uses_ai_snapshot_when_configured(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            init_store(root)

            left = add_memory(root, "facts", "Search index is rebuilt after memory updates")
            right = add_memory(root, "facts", "Search index is not rebuilt after memory updates")

            report = {
                "memory_count": 2,
                "rollups": [
                    {
                        "content": "Harmonized facts: Search index policy updated.",
                        "source_ids": [left["id"], right["id"]],
                        "score": 0.91,
                        "category": "facts",
                    }
                ],
                "contradictions": [
                    {
                        "left_id": left["id"],
                        "right_id": right["id"],
                        "left_content": "Search index is rebuilt after memory updates",
                        "right_content": "Search index is not rebuilt after memory updates",
                        "confidence": 0.82,
                        "type": "negation",
                    }
                ],
                "resolution_suggestions": [],
            }

            class _FakeResponse:
                def __enter__(self):
                    return self

                def __exit__(self, exc_type, exc, tb):
                    return False

                def read(self):
                    return (
                        b'{"choices":[{"message":{"content":"Memory snapshot: 2 memories scanned.\\nTop themes:\\n- Search indexing policy clarified.\\nContradictions: 1 potential issues.\\nWatch list:\\n- Index rebuild behavior conflicts across notes."}}]}'
                    )

            with mock.patch.dict("os.environ", {"LORE_AI_API_KEY": "test-key"}, clear=False):
                with mock.patch("lore.harmonize.urllib.request.urlopen", return_value=_FakeResponse()):
                    stats = apply_harmonize_report(
                        root,
                        report,
                        apply_rollups=True,
                        apply_resolution_suggestions=False,
                        link_sources=False,
                        ai_summary_config={
                            "enabled": True,
                            "model": "gpt-4o-mini",
                            "base_url": "https://api.openai.com/v1",
                            "timeout_seconds": 8,
                            "max_output_tokens": 220,
                            "max_chars": 1200,
                        },
                    )

            self.assertTrue(stats["ai_used"])
            summaries = list_memories(root, "summaries")
            self.assertEqual(len(summaries), 1)
            self.assertIn("Search indexing policy clarified", summaries[0].get("content", ""))


if __name__ == "__main__":
    unittest.main()
