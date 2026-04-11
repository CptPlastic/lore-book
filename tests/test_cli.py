from __future__ import annotations

import json
import os
import re
import tempfile
import time
import types
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

from typer.testing import CliRunner

from lore import __version__
from lore.cli import _latest_pypi_version, _parse_id_csv, app
from lore.store import init_store


_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def _clean(text: str) -> str:
    return _ANSI_RE.sub("", text)


class _FakeEmbedding(list):
    def tolist(self) -> list[float]:
        return list(self)


class _FakeSentenceTransformer:
    def __init__(self, _name: str) -> None:
        self._name = _name

    def encode(self, inputs, **_kwargs):
        def _one(item: object) -> _FakeEmbedding:
            # Deterministic low-dimensional vector suitable for tests.
            base = float(max(len(str(item)), 1))
            return _FakeEmbedding([base, 0.5, 0.25])

        if isinstance(inputs, list):
            return [_one(item) for item in inputs]
        return _one(inputs)


def _reset_search_cache() -> None:
    import lore.search as _search

    _search._model = None
    _search._use_tfidf = None


@contextmanager
def _cwd(path: str):
    old = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old)


class _FakeResponse:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def read(self) -> bytes:
        return self._payload


class CliVersionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = CliRunner()

    def test_version_shows_current_version(self) -> None:
        result = self.runner.invoke(app, ["version"], env={"LORE_NO_COLOR": "1"})

        self.assertEqual(result.exit_code, 0)
        self.assertIn(__version__, _clean(result.stdout))

    def test_version_check_reports_up_to_date(self) -> None:
        with mock.patch("lore.cli._latest_pypi_version", return_value=__version__):
            result = self.runner.invoke(app, ["version", "--check"], env={"LORE_NO_COLOR": "1"})

        self.assertEqual(result.exit_code, 0)
        self.assertIn("You are up to date", _clean(result.stdout))

    def test_version_check_reports_update_available(self) -> None:
        with mock.patch("lore.cli._latest_pypi_version", return_value="9.9.9"):
            result = self.runner.invoke(app, ["version", "--check"], env={"LORE_NO_COLOR": "1"})

        self.assertEqual(result.exit_code, 0)
        output = _clean(result.stdout)
        self.assertIn("A new version is available", output)
        self.assertIn("9.9.9", output)

    def test_version_check_handles_pypi_unavailable(self) -> None:
        with mock.patch("lore.cli._latest_pypi_version", return_value=None):
            result = self.runner.invoke(app, ["version", "--check"], env={"LORE_NO_COLOR": "1"})

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Could not reach PyPI", _clean(result.stdout))


class CliHelperTests(unittest.TestCase):
    def test_latest_pypi_version_returns_version(self) -> None:
        payload = b'{"info": {"version": "2.0.0"}}'
        with mock.patch("urllib.request.urlopen", return_value=_FakeResponse(payload)):
            latest = _latest_pypi_version(timeout=1)

        self.assertEqual(latest, "2.0.0")

    def test_latest_pypi_version_returns_none_on_error(self) -> None:
        with mock.patch("urllib.request.urlopen", side_effect=OSError("network down")):
            latest = _latest_pypi_version(timeout=1)

        self.assertIsNone(latest)

    def test_parse_id_csv_deduplicates_and_strips(self) -> None:
        values = _parse_id_csv(" a, b ,a, , c ")

        self.assertEqual(values, ["a", "b", "c"])


class CliDoctorJsonTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = CliRunner()
        _reset_search_cache()

    def tearDown(self) -> None:
        _reset_search_cache()

    def test_doctor_json_returns_error_without_store(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            with _cwd(td):
                result = self.runner.invoke(app, ["doctor", "--json"], env={"LORE_NO_COLOR": "1"})

        self.assertEqual(result.exit_code, 1)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["store"]["found"])
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["recommended_action"], "run lore doctor --fix or lore init .")

    def test_doctor_json_returns_report_with_store(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            init_store(root)

            fake_st = types.ModuleType("sentence_transformers")

            def _raise_model_error(_name: str) -> None:
                raise RuntimeError("model unavailable")

            fake_st.SentenceTransformer = _raise_model_error

            with _cwd(td):
                with mock.patch.dict("sys.modules", {"sentence_transformers": fake_st}):
                    result = self.runner.invoke(app, ["doctor", "--json"], env={"LORE_NO_COLOR": "1"})

        self.assertEqual(result.exit_code, 0)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["store"]["found"])
        self.assertFalse(payload["git"]["is_repo"])
        self.assertEqual(payload["spells"]["total"], 0)
        self.assertTrue(payload["model"]["fallback_tfidf"])
        self.assertEqual(payload["status"], "degraded")
        self.assertEqual(payload["recommended_action"], "run lore add")

    def test_doctor_json_compact_is_single_line(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            init_store(root)

            fake_st = types.ModuleType("sentence_transformers")

            def _raise_model_error(_name: str) -> None:
                raise RuntimeError("model unavailable")

            fake_st.SentenceTransformer = _raise_model_error

            with _cwd(td):
                with mock.patch.dict("sys.modules", {"sentence_transformers": fake_st}):
                    result = self.runner.invoke(app, ["doctor", "--json-compact"], env={"LORE_NO_COLOR": "1"})

        self.assertEqual(result.exit_code, 0)
        self.assertNotIn("\n", result.stdout.strip())
        payload = json.loads(result.stdout)
        self.assertIn("ok", payload)
        self.assertIn("model", payload)
        self.assertEqual(payload["status"], "degraded")

    def test_doctor_json_reports_healthy_when_model_loads(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            init_store(root)

            fake_st = types.ModuleType("sentence_transformers")

            def _ok_model(_name: str) -> object:
                return object()

            fake_st.SentenceTransformer = _ok_model

            with _cwd(td):
                with mock.patch.dict("sys.modules", {"sentence_transformers": fake_st}):
                    result = self.runner.invoke(app, ["doctor", "--json"], env={"LORE_NO_COLOR": "1"})

        self.assertEqual(result.exit_code, 0)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["ok"])
        self.assertFalse(payload["degraded"])
        self.assertTrue(payload["model"]["semantic_search_active"])
        self.assertEqual(payload["status"], "healthy")

    def test_doctor_json_schema_contract_keys_present(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            init_store(root)

            fake_st = types.ModuleType("sentence_transformers")

            def _raise_model_error(_name: str) -> None:
                raise RuntimeError("model unavailable")

            fake_st.SentenceTransformer = _raise_model_error

            with _cwd(td):
                with mock.patch.dict("sys.modules", {"sentence_transformers": fake_st}):
                    result = self.runner.invoke(app, ["doctor", "--json"], env={"LORE_NO_COLOR": "1"})

        self.assertEqual(result.exit_code, 0)
        payload = json.loads(result.stdout)
        self.assertSetEqual(
            set(payload.keys()),
            {
                "ok",
                "degraded",
                "status",
                "recommended_action",
                "fixes_applied",
                "fixes_planned",
                "store",
                "git",
                "config",
                "spells",
                "model",
            },
        )
        self.assertSetEqual(
            set(payload["model"].keys()),
            {
                "semantic_search_active",
                "fallback_tfidf",
                "reason",
                "timed_out",
                "check_seconds",
                "timeout_seconds",
            },
        )

    def test_doctor_json_strict_fails_on_degraded(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            init_store(root)

            fake_st = types.ModuleType("sentence_transformers")

            def _raise_model_error(_name: str) -> None:
                raise RuntimeError("model unavailable")

            fake_st.SentenceTransformer = _raise_model_error

            with _cwd(td):
                with mock.patch.dict("sys.modules", {"sentence_transformers": fake_st}):
                    result = self.runner.invoke(app, ["doctor", "--json", "--strict"], env={"LORE_NO_COLOR": "1"})

        self.assertEqual(result.exit_code, 1)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "degraded")

    def test_doctor_json_strict_succeeds_on_healthy(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            init_store(root)

            fake_st = types.ModuleType("sentence_transformers")

            def _ok_model(_name: str) -> object:
                return object()

            fake_st.SentenceTransformer = _ok_model

            with _cwd(td):
                with mock.patch.dict("sys.modules", {"sentence_transformers": fake_st}):
                    result = self.runner.invoke(app, ["doctor", "--json", "--strict"], env={"LORE_NO_COLOR": "1"})

        self.assertEqual(result.exit_code, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "healthy")

    def test_doctor_json_timeout_marks_degraded(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            init_store(root)

            fake_st = types.ModuleType("sentence_transformers")

            def _slow_model(_name: str) -> object:
                time.sleep(1.0)
                return object()

            fake_st.SentenceTransformer = _slow_model

            with _cwd(td):
                with mock.patch.dict("sys.modules", {"sentence_transformers": fake_st}):
                    result = self.runner.invoke(
                        app,
                        ["doctor", "--json", "--model-timeout", "0.5"],
                        env={"LORE_NO_COLOR": "1"},
                    )

        self.assertEqual(result.exit_code, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "degraded")
        self.assertTrue(payload["model"]["timed_out"])
        self.assertGreaterEqual(payload["model"]["check_seconds"], 0.5)
        self.assertEqual(payload["model"]["timeout_seconds"], 0.5)

    def test_doctor_json_fix_initializes_missing_store(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fake_st = types.ModuleType("sentence_transformers")

            def _raise_model_error(_name: str) -> None:
                raise RuntimeError("model unavailable")

            fake_st.SentenceTransformer = _raise_model_error

            with _cwd(td):
                with mock.patch.dict("sys.modules", {"sentence_transformers": fake_st}):
                    result = self.runner.invoke(app, ["doctor", "--json", "--fix"], env={"LORE_NO_COLOR": "1"})

        self.assertEqual(result.exit_code, 0)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["store"]["found"])
        self.assertIn("initialized_store", payload["fixes_applied"])
        self.assertIn("exported_context_files", payload["fixes_applied"])

    def test_doctor_json_fix_installs_hook_in_git_repo(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            init_store(root)
            (root / ".git" / "hooks").mkdir(parents=True)

            fake_st = types.ModuleType("sentence_transformers")

            def _raise_model_error(_name: str) -> None:
                raise RuntimeError("model unavailable")

            fake_st.SentenceTransformer = _raise_model_error

            with _cwd(td):
                with mock.patch.dict("sys.modules", {"sentence_transformers": fake_st}):
                    result = self.runner.invoke(app, ["doctor", "--json", "--fix"], env={"LORE_NO_COLOR": "1"})

        self.assertEqual(result.exit_code, 0)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["git"]["post_commit_hook_installed"])
        self.assertIn("installed_post_commit_hook", payload["fixes_applied"])

    def test_doctor_json_fix_dry_run_plans_changes_only(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fake_st = types.ModuleType("sentence_transformers")

            def _raise_model_error(_name: str) -> None:
                raise RuntimeError("model unavailable")

            fake_st.SentenceTransformer = _raise_model_error

            with _cwd(td):
                with mock.patch.dict("sys.modules", {"sentence_transformers": fake_st}):
                    result = self.runner.invoke(app, ["doctor", "--json", "--fix-dry-run"], env={"LORE_NO_COLOR": "1"})

                    self.assertFalse((Path(td) / ".lore").exists())

        self.assertEqual(result.exit_code, 1)
        payload = json.loads(result.stdout)
        self.assertIn("initialized_store", payload["fixes_planned"])
        self.assertEqual(payload["fixes_applied"], [])


class CliIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = CliRunner()
        _reset_search_cache()

    def tearDown(self) -> None:
        _reset_search_cache()

    def test_init_add_and_doctor_json_compact_flow(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fake_st = types.ModuleType("sentence_transformers")

            def _ok_model(_name: str) -> _FakeSentenceTransformer:
                return _FakeSentenceTransformer(_name)

            fake_st.SentenceTransformer = _ok_model

            with _cwd(td):
                with mock.patch.dict("sys.modules", {"sentence_transformers": fake_st}):
                    init_result = self.runner.invoke(app, ["init", "."], env={"LORE_NO_COLOR": "1"})
                    self.assertEqual(init_result.exit_code, 0)

                    add_result = self.runner.invoke(
                        app,
                        ["add", "facts", "integration smoke memory"],
                        env={"LORE_NO_COLOR": "1"},
                    )
                    self.assertEqual(add_result.exit_code, 0)

                    doctor_result = self.runner.invoke(app, ["doctor", "--json-compact"], env={"LORE_NO_COLOR": "1"})

        self.assertEqual(doctor_result.exit_code, 0)
        payload = json.loads(doctor_result.stdout)
        self.assertNotIn("\n", doctor_result.stdout.strip())
        self.assertEqual(payload["status"], "healthy")
        self.assertGreaterEqual(payload["spells"]["total"], 1)
        self.assertGreaterEqual(payload["spells"]["by_category"].get("facts", 0), 1)

    def test_list_json_outputs_items(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            with _cwd(td):
                init_result = self.runner.invoke(app, ["init", "."], env={"LORE_NO_COLOR": "1"})
                self.assertEqual(init_result.exit_code, 0)
                add_result = self.runner.invoke(app, ["add", "facts", "json list memory"], env={"LORE_NO_COLOR": "1"})
                self.assertEqual(add_result.exit_code, 0)
                result = self.runner.invoke(app, ["list", "--json"], env={"LORE_NO_COLOR": "1"})

        self.assertEqual(result.exit_code, 0)
        payload = json.loads(result.stdout)
        self.assertGreaterEqual(payload["count"], 1)
        self.assertEqual(payload["items"][0]["category"], "facts")

    def test_search_json_outputs_results(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fake_st = types.ModuleType("sentence_transformers")

            def _ok_model(_name: str) -> _FakeSentenceTransformer:
                return _FakeSentenceTransformer(_name)

            fake_st.SentenceTransformer = _ok_model

            with _cwd(td):
                with mock.patch.dict("sys.modules", {"sentence_transformers": fake_st}):
                    self.assertEqual(self.runner.invoke(app, ["init", "."], env={"LORE_NO_COLOR": "1"}).exit_code, 0)
                    self.assertEqual(self.runner.invoke(app, ["add", "facts", "semantic memory"], env={"LORE_NO_COLOR": "1"}).exit_code, 0)
                    result = self.runner.invoke(app, ["search", "semantic", "--json-compact"], env={"LORE_NO_COLOR": "1"})

        self.assertEqual(result.exit_code, 0)
        self.assertNotIn("\n", result.stdout.strip())
        payload = json.loads(result.stdout)
        self.assertEqual(payload["query"], "semantic")
        self.assertGreaterEqual(payload["count"], 1)

    def test_lint_json_outputs_summary(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            with _cwd(td):
                self.assertEqual(self.runner.invoke(app, ["init", "."], env={"LORE_NO_COLOR": "1"}).exit_code, 0)
                self.assertEqual(self.runner.invoke(app, ["add", "facts", "lint memory"], env={"LORE_NO_COLOR": "1"}).exit_code, 0)
                result = self.runner.invoke(app, ["lint", "--json"], env={"LORE_NO_COLOR": "1"})

        self.assertEqual(result.exit_code, 0)
        payload = json.loads(result.stdout)
        self.assertIn("summary", payload)
        self.assertEqual(payload["summary"]["error"], 0)


class CliEmptyStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = CliRunner()
        _reset_search_cache()

    def tearDown(self) -> None:
        _reset_search_cache()

    def test_list_empty_state_shows_next_steps(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            init_store(Path(td))
            with _cwd(td):
                result = self.runner.invoke(app, ["list"], env={"LORE_NO_COLOR": "1"})

        self.assertEqual(result.exit_code, 0)
        output = _clean(result.stdout)
        self.assertIn("No memories found.", output)
        self.assertIn("lore add", output)
        self.assertIn("lore onboard", output)

    def test_search_empty_state_shows_guidance(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            init_store(Path(td))
            with _cwd(td):
                result = self.runner.invoke(app, ["search", "missing context"], env={"LORE_NO_COLOR": "1"})

        self.assertEqual(result.exit_code, 0)
        output = _clean(result.stdout)
        self.assertIn("No results found for 'missing context'", output)
        self.assertIn("lore list", output)
        self.assertIn("lore add", output)

    def test_associate_empty_state_shows_guidance(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            init_store(Path(td))
            with _cwd(td):
                result = self.runner.invoke(app, ["associate", "1"], env={"LORE_NO_COLOR": "1"})

        self.assertEqual(result.exit_code, 0)
        output = _clean(result.stdout)
        self.assertIn("No memories found.", output)
        self.assertIn("at least two spells", output)


if __name__ == "__main__":
    unittest.main()
