from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lore.chronicle import import_chronicle
from lore.store import init_store, list_memories


class ChronicleImportTests(unittest.TestCase):
    def test_import_skips_harmonize_snapshot_noise(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            init_store(root)

            chronicle = root / "CHRONICLE.md"
            chronicle.write_text(
                "\n".join(
                    [
                        "# CHRONICLE",
                        "",
                        "## Summaries",
                        "- Memory snapshot: 147 memories scanned.",
                        "- Useful weekly recap for release readiness.",
                    ]
                ),
                encoding="utf-8",
            )

            stats = import_chronicle(root, chronicle_path=chronicle, dry_run=False)

            summaries = list_memories(root, "summaries")
            self.assertEqual(len(summaries), 1)
            self.assertEqual(
                summaries[0].get("content"),
                "Useful weekly recap for release readiness.",
            )
            self.assertEqual(stats.get("added"), 1)
            self.assertEqual(stats.get("skipped_noise"), 1)


if __name__ == "__main__":
    unittest.main()
