"""Tests for the discovery, suggestion and unified-CLI layers."""

from pathlib import Path

import pytest

from fileforge import discovery, suggestions, unified_cli


# --------------------------------------------------------------------------- #
# Discovery / alias normalization
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "alias",
    [
        "File Forge",
        "FileForge",
        "File-Forge",
        "file-forge",
        "fileforge",
        "file_forge",
        "FileForge 2.0",
        "FileForge2",
        "~/file-forge",
        "/home/dev/File-Forge/",
    ],
)
def test_known_aliases_normalize(alias):
    assert discovery.normalize_alias(alias) == discovery.CANONICAL_ID
    assert discovery.is_alias(alias) is True


@pytest.mark.parametrize("nope", ["", "forge-file", "fileforget", "random", "file"])
def test_non_aliases_reject(nope):
    assert discovery.normalize_alias(nope) is None
    assert discovery.is_alias(nope) is False


def test_identify_roles(tmp_path):
    (tmp_path / "AndroidManifest.xml").write_text("<manifest/>")
    (tmp_path / "pyproject.toml").write_text("[project]")
    roles = discovery.identify_roles(tmp_path)
    assert "android" in roles
    assert "cli" in roles


def test_discover_finds_marker_instance(tmp_path):
    inst = tmp_path / "file-forge"
    (inst / "src" / "fileforge").mkdir(parents=True)
    (inst / "pyproject.toml").write_text("[project]")
    result = discovery.discover([tmp_path], max_depth=3)
    paths = [p.path.name for p in result.instances]
    assert "file-forge" in paths
    assert result.canonical_id == "fileforge"


def test_discover_result_to_dict_is_json_safe(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]")
    result = discovery.discover([tmp_path], max_depth=2)
    import json

    json.dumps(result.to_dict())  # must not raise


# --------------------------------------------------------------------------- #
# Suggestions
# --------------------------------------------------------------------------- #


@pytest.fixture
def sample_dir(tmp_path):
    for name in ("a.png", "b.png", "c.csv", "d.md", "e.mp4", "noext"):
        (tmp_path / name).write_text("x")
    return tmp_path


def test_scan_counts_extensions(sample_dir):
    scan = suggestions.scan_directory(sample_dir)
    assert scan.frequency["png"] == 2
    assert scan.frequency["csv"] == 1
    assert "noext" not in scan.frequency  # no extension -> ignored
    assert scan.total_files == 5


def test_suggest_returns_supported_and_generic(sample_dir):
    scan = suggestions.scan_directory(sample_dir)
    sugg = suggestions.suggest(scan)
    routes = {(s.source_ext, s.target_ext): s for s in sugg}
    # Engine-supported route exists and is flagged supported.
    assert routes[("png", "jpg")].supported is True
    assert routes[("csv", "json")].supported is True
    # A generic route with no engine converter is flagged unsupported.
    assert routes[("png", "pdf")].supported is False
    # Supported routes are ranked ahead of generic ones.
    first_generic = next(i for i, s in enumerate(sugg) if not s.supported)
    last_supported = max(i for i, s in enumerate(sugg) if s.supported)
    assert last_supported < first_generic


def test_no_generic_flag(sample_dir):
    scan = suggestions.scan_directory(sample_dir)
    sugg = suggestions.suggest(scan, include_generic=False)
    assert all(s.supported for s in sugg)


def test_build_plan_and_scripts(sample_dir):
    scan = suggestions.scan_directory(sample_dir)
    plan = suggestions.build_plan(scan, "png", "jpg")
    assert len(plan) == 2
    assert all(item.target.endswith(".jpg") for item in plan)

    sh = suggestions.render_bash(plan)
    ps = suggestions.render_powershell(plan)
    assert sh.startswith("#!/usr/bin/env bash")
    assert "fileforge" in sh
    assert "convert" in ps
    # Every planned file appears in both scripts.
    for item in plan:
        assert item.source in sh
        assert item.source in ps


def test_write_scripts_are_created(sample_dir, tmp_path):
    scan = suggestions.scan_directory(sample_dir)
    plan = suggestions.build_plan(scan, "png", "jpg")
    out = tmp_path / "scripts"
    written = suggestions._write_scripts(plan, out)
    assert (out / "run_conversions.sh").exists()
    assert (out / "run_conversions.ps1").exists()
    assert len(written) == 2


# --------------------------------------------------------------------------- #
# Unified CLI
# --------------------------------------------------------------------------- #


def test_unified_report_matrix_and_recs(sample_dir):
    report = unified_cli.build_report(
        str(sample_dir), aliases=["File Forge", "nope"], exts=["png", "csv"]
    )
    assert report.aliases["File Forge"] == "fileforge"
    assert report.aliases["nope"] is None
    # Matrix only contains the requested extensions.
    matrix_exts = {cell.source_ext for cell in report.matrix}
    assert matrix_exts <= {"png", "csv"}
    png_cell = next(c for c in report.matrix if c.source_ext == "png")
    assert "jpg" in png_cell.targets
    # Recommendations are all engine-supported.
    assert all(r["supported"] for r in report.recommendations)


def test_unified_report_json_safe(sample_dir):
    import json

    report = unified_cli.build_report(str(sample_dir))
    json.dumps(report.to_dict())


def test_unified_report_requested_ext_with_no_files(tmp_path):
    (tmp_path / "only.txt").write_text("hi")
    report = unified_cli.build_report(str(tmp_path), exts=["png"])
    # png has no files here but should still show possible targets.
    png_cell = next((c for c in report.matrix if c.source_ext == "png"), None)
    assert png_cell is not None
    assert png_cell.count == 0
    assert png_cell.targets  # engine can convert png to something


# --------------------------------------------------------------------------- #
# CLI entry points (argv-driven, no interaction)
# --------------------------------------------------------------------------- #


def test_discover_cli_normalize(capsys):
    rc = discovery.main(["--normalize", "file-forge"])
    assert rc == 0
    assert "fileforge" in capsys.readouterr().out


def test_suggest_cli_json(sample_dir, capsys):
    rc = suggestions.main([str(sample_dir), "--json"])
    assert rc == 0
    import json

    payload = json.loads(capsys.readouterr().out)
    assert payload["scan"]["total_files"] == 5


def test_unified_cli_json(sample_dir, capsys):
    rc = unified_cli.main(["--dir", str(sample_dir), "--json", "--ext", "png"])
    assert rc == 0
    import json

    payload = json.loads(capsys.readouterr().out)
    assert payload["directory"].endswith(str(sample_dir).split("/")[-1])
