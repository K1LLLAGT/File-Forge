"""Developer / data-wrangling converters — all pure-standard-library.

Covers the "custom" everyday conversions that don't need third-party deps:
JSON⇄JSONL, tabular → Markdown/HTML tables, INI⇄JSON/TOML, .env⇄JSON,
HAR → CSV, and GPX/KML → GeoJSON.
"""

from __future__ import annotations

import configparser
import csv
import io
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List

from fileforge.core.registry import ConversionError, registry


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #

def _load_json(source: Path):
    return json.loads(Path(source).read_text(encoding="utf-8"))


def _read_rows(source: Path, delimiter: str) -> List[dict]:
    text = Path(source).read_text(encoding="utf-8")
    return list(csv.DictReader(io.StringIO(text), delimiter=delimiter))


def _rows_from_json(data) -> List[dict]:
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list) or not all(isinstance(r, dict) for r in data):
        raise ConversionError("expected a JSON array of objects (or one object)")
    return data


def _columns(rows: List[dict]) -> List[str]:
    cols: List[str] = []
    for row in rows:
        for k in row:
            if k not in cols:
                cols.append(k)
    return cols


# --------------------------------------------------------------------------- #
# JSON ⇄ JSONL
# --------------------------------------------------------------------------- #

@registry.add("json", "jsonl", description="JSON array -> newline-delimited JSON")
def json_to_jsonl(source: Path, target: Path, **_) -> Path:
    data = _load_json(source)
    if not isinstance(data, list):
        raise ConversionError("json -> jsonl needs a top-level JSON array")
    lines = [json.dumps(item, ensure_ascii=False) for item in data]
    Path(target).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target


@registry.add("jsonl", "json", description="Newline-delimited JSON -> JSON array")
def jsonl_to_json(source: Path, target: Path, **_) -> Path:
    items = []
    for line in Path(source).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            items.append(json.loads(line))
    Path(target).write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")
    return target


# --------------------------------------------------------------------------- #
# Tabular -> Markdown / HTML tables
# --------------------------------------------------------------------------- #

def _render_markdown(rows: List[dict]) -> str:
    if not rows:
        return ""
    cols = _columns(rows)
    def esc(v): return str(v).replace("|", "\\|").replace("\n", " ")
    head = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join(["---"] * len(cols)) + " |"
    body = ["| " + " | ".join(esc(row.get(c, "")) for c in cols) + " |" for row in rows]
    return "\n".join([head, sep, *body]) + "\n"


def _render_html(rows: List[dict]) -> str:
    if not rows:
        return "<table></table>\n"
    import html as _html
    cols = _columns(rows)
    out = ["<table>", "  <thead>", "    <tr>"]
    out += [f"      <th>{_html.escape(c)}</th>" for c in cols]
    out += ["    </tr>", "  </thead>", "  <tbody>"]
    for row in rows:
        out.append("    <tr>")
        out += [f"      <td>{_html.escape(str(row.get(c, '')))}</td>" for c in cols]
        out.append("    </tr>")
    out += ["  </tbody>", "</table>"]
    return "\n".join(out) + "\n"


@registry.add("csv", "md", description="CSV -> Markdown table")
def csv_to_md(source: Path, target: Path, **_) -> Path:
    Path(target).write_text(_render_markdown(_read_rows(source, ",")), encoding="utf-8")
    return target


@registry.add("tsv", "md", description="TSV -> Markdown table")
def tsv_to_md(source: Path, target: Path, **_) -> Path:
    Path(target).write_text(_render_markdown(_read_rows(source, "\t")), encoding="utf-8")
    return target


@registry.add("json", "md", description="JSON array of objects -> Markdown table")
def json_to_md(source: Path, target: Path, **_) -> Path:
    Path(target).write_text(_render_markdown(_rows_from_json(_load_json(source))), encoding="utf-8")
    return target


@registry.add("csv", "html", description="CSV -> HTML table")
def csv_to_html(source: Path, target: Path, **_) -> Path:
    Path(target).write_text(_render_html(_read_rows(source, ",")), encoding="utf-8")
    return target


@registry.add("json", "html", description="JSON array of objects -> HTML table")
def json_to_html(source: Path, target: Path, **_) -> Path:
    Path(target).write_text(_render_html(_rows_from_json(_load_json(source))), encoding="utf-8")
    return target


# --------------------------------------------------------------------------- #
# INI ⇄ JSON / TOML
# --------------------------------------------------------------------------- #

def _ini_to_dict(source: Path) -> dict:
    parser = configparser.ConfigParser()
    parser.optionxform = str  # preserve key case
    parser.read(source, encoding="utf-8")
    data = {s: dict(parser.items(s)) for s in parser.sections()}
    if parser.defaults():
        data["DEFAULT"] = dict(parser.defaults())
    return data


@registry.add("ini", "json", description="INI config -> JSON")
def ini_to_json(source: Path, target: Path, **_) -> Path:
    Path(target).write_text(json.dumps(_ini_to_dict(source), indent=2), encoding="utf-8")
    return target


@registry.add("json", "ini", description="JSON (object of objects) -> INI")
def json_to_ini(source: Path, target: Path, **_) -> Path:
    data = _load_json(source)
    if not isinstance(data, dict):
        raise ConversionError("json -> ini needs a top-level object of sections")
    parser = configparser.ConfigParser()
    parser.optionxform = str
    for section, values in data.items():
        if not isinstance(values, dict):
            raise ConversionError(f"section '{section}' must map to an object")
        parser[section] = {k: str(v) for k, v in values.items()}
    buf = io.StringIO()
    parser.write(buf)
    Path(target).write_text(buf.getvalue(), encoding="utf-8")
    return target


@registry.add("ini", "toml", description="INI config -> TOML", requires=["tomli_w"])
def ini_to_toml(source: Path, target: Path, **_) -> Path:
    import tomli_w
    Path(target).write_bytes(tomli_w.dumps(_ini_to_dict(source)).encode("utf-8"))
    return target


@registry.add("toml", "ini", description="TOML -> INI", requires=["tomli"])
def toml_to_ini(source: Path, target: Path, **_) -> Path:
    import tomli
    data = tomli.loads(Path(source).read_text(encoding="utf-8"))
    parser = configparser.ConfigParser()
    parser.optionxform = str
    for section, values in data.items():
        if isinstance(values, dict):
            parser[section] = {k: str(v) for k, v in values.items()}
    buf = io.StringIO()
    parser.write(buf)
    Path(target).write_text(buf.getvalue(), encoding="utf-8")
    return target


# --------------------------------------------------------------------------- #
# .env ⇄ JSON
# --------------------------------------------------------------------------- #

def _parse_env(text: str) -> dict:
    out = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):]
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        val = val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        out[key.strip()] = val
    return out


@registry.add("env", "json", description="dotenv (.env) -> JSON")
def env_to_json(source: Path, target: Path, **_) -> Path:
    data = _parse_env(Path(source).read_text(encoding="utf-8"))
    Path(target).write_text(json.dumps(data, indent=2), encoding="utf-8")
    return target


@registry.add("json", "env", description="JSON object -> dotenv (.env)")
def json_to_env(source: Path, target: Path, **_) -> Path:
    data = _load_json(source)
    if not isinstance(data, dict):
        raise ConversionError("json -> env needs a flat JSON object")
    lines = []
    for k, v in data.items():
        val = "" if v is None else str(v)
        if re.search(r"\s|#|\"|'", val):
            val = '"' + val.replace('"', '\\"') + '"'
        lines.append(f"{k}={val}")
    Path(target).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target


# --------------------------------------------------------------------------- #
# HAR -> CSV (extract network requests)
# --------------------------------------------------------------------------- #

@registry.add("har", "csv", description="Browser HAR -> CSV of requests")
def har_to_csv(source: Path, target: Path, **_) -> Path:
    har = _load_json(source)
    entries = har.get("log", {}).get("entries", [])
    rows = []
    for e in entries:
        req, res, timings = e.get("request", {}), e.get("response", {}), e.get("timings", {})
        rows.append({
            "method": req.get("method", ""),
            "url": req.get("url", ""),
            "status": res.get("status", ""),
            "mimeType": res.get("content", {}).get("mimeType", ""),
            "size_bytes": res.get("content", {}).get("size", ""),
            "time_ms": round(e.get("time", 0), 1),
            "wait_ms": round(timings.get("wait", 0), 1) if timings.get("wait", -1) >= 0 else "",
            "started": e.get("startedDateTime", ""),
        })
    cols = ["method", "url", "status", "mimeType", "size_bytes", "time_ms", "wait_ms", "started"]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=cols)
    writer.writeheader()
    writer.writerows(rows)
    Path(target).write_text(buf.getvalue(), encoding="utf-8")
    return target


# --------------------------------------------------------------------------- #
# GPX / KML -> GeoJSON
# --------------------------------------------------------------------------- #

def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]  # strip XML namespace


def _feature(geometry_type, coords, props=None):
    return {"type": "Feature", "properties": props or {},
            "geometry": {"type": geometry_type, "coordinates": coords}}


@registry.add("gpx", "geojson", description="GPS track (GPX) -> GeoJSON")
def gpx_to_geojson(source: Path, target: Path, **_) -> Path:
    root = ET.fromstring(Path(source).read_text(encoding="utf-8"))
    features = []
    # waypoints
    for el in root.iter():
        if _local(el.tag) == "wpt":
            lat, lon = float(el.get("lat")), float(el.get("lon"))
            name = next((c.text for c in el if _local(c.tag) == "name"), None)
            features.append(_feature("Point", [lon, lat], {"name": name} if name else {}))
    # tracks / segments -> LineString
    for trk in (el for el in root.iter() if _local(el.tag) == "trkseg"):
        line = []
        for pt in (c for c in trk if _local(c.tag) == "trkpt"):
            line.append([float(pt.get("lon")), float(pt.get("lat"))])
        if line:
            features.append(_feature("LineString", line))
    fc = {"type": "FeatureCollection", "features": features}
    Path(target).write_text(json.dumps(fc, indent=2), encoding="utf-8")
    return target


@registry.add("kml", "geojson", description="KML -> GeoJSON")
def kml_to_geojson(source: Path, target: Path, **_) -> Path:
    root = ET.fromstring(Path(source).read_text(encoding="utf-8"))
    features = []
    for pm in (el for el in root.iter() if _local(el.tag) == "Placemark"):
        name = next((c.text for c in pm if _local(c.tag) == "name"), None)
        props = {"name": name} if name else {}
        for geom in pm.iter():
            lt = _local(geom.tag)
            if lt == "Point":
                coord = next((c.text for c in geom if _local(c.tag) == "coordinates"), "")
                pt = _parse_kml_coords(coord)
                if pt:
                    features.append(_feature("Point", pt[0], props))
            elif lt in ("LineString", "LinearRing"):
                coord = next((c.text for c in geom if _local(c.tag) == "coordinates"), "")
                pts = _parse_kml_coords(coord)
                if pts:
                    kind = "LineString" if lt == "LineString" else "Polygon"
                    features.append(_feature(kind, pts if kind == "LineString" else [pts], props))
    fc = {"type": "FeatureCollection", "features": features}
    Path(target).write_text(json.dumps(fc, indent=2), encoding="utf-8")
    return target


def _parse_kml_coords(text: str):
    pts = []
    for tok in (text or "").split():
        parts = tok.split(",")
        if len(parts) >= 2:
            pts.append([float(parts[0]), float(parts[1])])
    return pts
