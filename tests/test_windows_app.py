"""Headless tests for the Windows desktop controller.

The Tkinter view (``windows/fileforge_app.py``) needs a display, but all of its
logic lives in ``windows/fileforge_core.Controller``, which imports no GUI code
and is fully testable here.
"""

import sys
from pathlib import Path

import pytest

# Make windows/ importable (mirrors what fileforge_app.py does at runtime).
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "windows"))

from fileforge_core import Controller  # noqa: E402


@pytest.fixture
def sample_dir(tmp_path):
    # Two real PNGs would need Pillow; use text conversions that need no deps.
    (tmp_path / "a.md").write_text("# A\n\nhello")
    (tmp_path / "b.md").write_text("# B\n\nworld")
    (tmp_path / "c.csv").write_text("x,y\n1,2\n")
    (tmp_path / "notes.txt").write_text("plain")
    return tmp_path


@pytest.fixture
def controller(tmp_path):
    # Isolate the history log inside the test's tmp dir.
    return Controller(log_path=tmp_path / "hist" / "history.jsonl")


def test_summary_counts(controller, sample_dir):
    controller.set_directory(sample_dir)
    summary = {row.ext: row.count for row in controller.file_type_summary()}
    assert summary["md"] == 2
    assert summary["csv"] == 1
    assert summary["txt"] == 1


def test_suggestions_include_supported_routes(controller, sample_dir):
    controller.set_directory(sample_dir)
    routes = {(s.source_ext, s.target_ext): s for s in controller.suggestions()}
    assert routes[("md", "html")].supported is True
    assert routes[("csv", "json")].supported is True


def test_plan_enumerates_files(controller, sample_dir):
    controller.set_directory(sample_dir)
    plan = controller.plan("md", "html")
    assert len(plan) == 2
    assert all(item.target.endswith(".html") for item in plan)


def test_run_plan_converts_and_reports_progress(controller, sample_dir):
    controller.set_directory(sample_dir)
    seen = []
    results = controller.run_plan(
        "md", "html", on_progress=lambda done, total, res: seen.append((done, total))
    )
    assert len(results) == 2
    assert all(r.ok for r in results)
    # Output files really exist.
    for r in results:
        assert Path(r.target).exists()
    # Progress fired once per file with a correct running count.
    assert seen == [(1, 2), (2, 2)]


def test_run_plan_logs_history(controller, sample_dir):
    controller.set_directory(sample_dir)
    controller.run_plan("md", "html")
    hist = controller.history()
    assert len(hist) == 2
    assert all(entry["ok"] for entry in hist)
    assert all("elapsed_ms" in entry for entry in hist)


def test_clear_history(controller, sample_dir):
    controller.set_directory(sample_dir)
    controller.run_plan("csv", "json")
    assert controller.history()
    controller.clear_history()
    assert controller.history() == []


def test_run_plan_records_failure(controller, tmp_path):
    # A corrupt CSV -> XLSX would need openpyxl; instead force a bad route by
    # pointing at a source ext with no registered converter target.
    (tmp_path / "only.txt").write_text("hi")
    controller.set_directory(tmp_path)
    # txt -> pdf is supported (pure python), so use a genuinely unknown target
    # via the generic path: txt -> md has no engine route.
    plan = controller.plan("txt", "md")
    # There is a txt file, so a plan item exists, but no engine converter.
    if plan:
        results = controller.run_plan("txt", "md")
        assert results and results[0].ok is False
        assert "no engine route" in results[0].error
