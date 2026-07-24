"""Structured-data converters: JSON, CSV, TSV, YAML.

All routes here are free-tier and depend only on the standard library,
except YAML which uses PyYAML when it is installed.
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

from fileforge.core.registry import ConversionError, registry


def _read_tabular(rows, target: Path, delimiter: str) -> Path:
    if not rows:
        target.write_text("", encoding="utf-8")
        return target
    fieldnames = list({k: None for row in rows for k in row.keys()})
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, delimiter=delimiter)
    writer.writeheader()
    writer.writerows(rows)
    target.write_text(buf.getvalue(), encoding="utf-8")
    return target


@registry.add("json", "csv", description="JSON array of objects -> CSV")
def json_to_csv(source: Path, target: Path, **_) -> Path:
    data = json.loads(Path(source).read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        raise ConversionError("JSON must be an object or array of objects")
    return _read_tabular(data, Path(target), ",")


@registry.add("json", "tsv", description="JSON array of objects -> TSV")
def json_to_tsv(source: Path, target: Path, **_) -> Path:
    data = json.loads(Path(source).read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = [data]
    return _read_tabular(data, Path(target), "\t")


@registry.add("csv", "json", description="CSV -> pretty JSON array")
def csv_to_json(source: Path, target: Path, **_) -> Path:
    with Path(source).open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    Path(target).write_text(json.dumps(rows, indent=2), encoding="utf-8")
    return Path(target)


@registry.add("csv", "tsv", description="CSV -> TSV")
def csv_to_tsv(source: Path, target: Path, **_) -> Path:
    with Path(source).open(encoding="utf-8", newline="") as fh:
        rows = list(csv.reader(fh))
    buf = io.StringIO()
    csv.writer(buf, delimiter="\t").writerows(rows)
    Path(target).write_text(buf.getvalue(), encoding="utf-8")
    return Path(target)


@registry.add("json", "yaml", description="JSON -> YAML", requires=["yaml"])
def json_to_yaml(source: Path, target: Path, **_) -> Path:
    import yaml  # optional dependency

    data = json.loads(Path(source).read_text(encoding="utf-8"))
    Path(target).write_text(
        yaml.safe_dump(data, sort_keys=False), encoding="utf-8"
    )
    return Path(target)


@registry.add("yaml", "json", description="YAML -> pretty JSON", requires=["yaml"])
def yaml_to_json(source: Path, target: Path, **_) -> Path:
    import yaml  # optional dependency

    data = yaml.safe_load(Path(source).read_text(encoding="utf-8"))
    Path(target).write_text(json.dumps(data, indent=2), encoding="utf-8")
    return Path(target)
