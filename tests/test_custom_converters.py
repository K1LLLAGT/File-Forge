"""Tests for the 'custom' converter batch (dev/data, subtitles, graphics) and
the chained-conversion feature."""

import json

import pytest

from fileforge.core.registry import load_builtin_converters, registry


@pytest.fixture(autouse=True, scope="module")
def _load():
    load_builtin_converters()


def _conv(src, tgt, src_file, dst_file):
    return registry.get(src, tgt).fn(src_file, dst_file)


# --------------------------------------------------------------------------- #
# JSON <-> JSONL
# --------------------------------------------------------------------------- #

def test_json_jsonl_roundtrip(tmp_path):
    src = tmp_path / "a.json"
    src.write_text(json.dumps([{"x": 1}, {"x": 2}]))
    jl = tmp_path / "a.jsonl"
    _conv("json", "jsonl", src, jl)
    assert jl.read_text().splitlines() == ['{"x": 1}', '{"x": 2}']
    back = tmp_path / "b.json"
    _conv("jsonl", "json", jl, back)
    assert json.loads(back.read_text()) == [{"x": 1}, {"x": 2}]


# --------------------------------------------------------------------------- #
# Tables: Markdown + HTML
# --------------------------------------------------------------------------- #

def test_csv_to_markdown_table(tmp_path):
    src = tmp_path / "t.csv"
    src.write_text("name,age\nAda,36\n")
    out = tmp_path / "t.md"
    _conv("csv", "md", src, out)
    lines = out.read_text().splitlines()
    assert lines[0] == "| name | age |"
    assert lines[1] == "| --- | --- |"
    assert lines[2] == "| Ada | 36 |"


def test_json_to_html_table(tmp_path):
    src = tmp_path / "t.json"
    src.write_text(json.dumps([{"a": 1, "b": "<x>"}]))
    out = tmp_path / "t.html"
    _conv("json", "html", src, out)
    html = out.read_text()
    assert "<table>" in html and "<th>a</th>" in html
    assert "&lt;x&gt;" in html  # HTML-escaped


# --------------------------------------------------------------------------- #
# INI <-> JSON / TOML
# --------------------------------------------------------------------------- #

def test_ini_to_json(tmp_path):
    src = tmp_path / "c.ini"
    src.write_text("[server]\nhost = localhost\nport = 8080\n")
    out = tmp_path / "c.json"
    _conv("ini", "json", src, out)
    assert json.loads(out.read_text()) == {"server": {"host": "localhost", "port": "8080"}}


def test_json_to_ini_roundtrip(tmp_path):
    src = tmp_path / "c.json"
    src.write_text(json.dumps({"db": {"name": "x", "pool": "5"}}))
    ini = tmp_path / "c.ini"
    _conv("json", "ini", src, ini)
    assert "[db]" in ini.read_text()
    back = tmp_path / "c2.json"
    _conv("ini", "json", ini, back)
    assert json.loads(back.read_text()) == {"db": {"name": "x", "pool": "5"}}


def test_ini_toml_routes_registered():
    assert registry.get("ini", "toml").requires == ("tomli_w",)
    assert registry.get("toml", "ini").requires == ("tomli",)


# --------------------------------------------------------------------------- #
# .env <-> JSON
# --------------------------------------------------------------------------- #

def test_env_to_json(tmp_path):
    src = tmp_path / "x.env"
    src.write_text('API_KEY="secret val"\n# c\nexport PORT=3000\n')
    out = tmp_path / "x.json"
    _conv("env", "json", src, out)
    assert json.loads(out.read_text()) == {"API_KEY": "secret val", "PORT": "3000"}


def test_json_to_env(tmp_path):
    src = tmp_path / "x.json"
    src.write_text(json.dumps({"A": "1", "B": "two words"}))
    out = tmp_path / "x.env"
    _conv("json", "env", src, out)
    text = out.read_text()
    assert "A=1" in text
    assert 'B="two words"' in text  # quoted because it has a space


# --------------------------------------------------------------------------- #
# HAR -> CSV
# --------------------------------------------------------------------------- #

def test_har_to_csv(tmp_path):
    har = {"log": {"entries": [
        {"request": {"method": "GET", "url": "http://x/a"},
         "response": {"status": 200, "content": {"mimeType": "text/html", "size": 10}},
         "time": 12.34, "timings": {"wait": 5.0}, "startedDateTime": "2026-01-01"}
    ]}}
    src = tmp_path / "h.har"
    src.write_text(json.dumps(har))
    out = tmp_path / "h.csv"
    _conv("har", "csv", src, out)
    rows = out.read_text().splitlines()
    assert rows[0].startswith("method,url,status")
    assert "GET,http://x/a,200" in rows[1]


# --------------------------------------------------------------------------- #
# GPX / KML -> GeoJSON
# --------------------------------------------------------------------------- #

def test_gpx_to_geojson(tmp_path):
    src = tmp_path / "g.gpx"
    src.write_text(
        '<gpx><wpt lat="1.0" lon="2.0"><name>P1</name></wpt>'
        '<trk><trkseg><trkpt lat="1" lon="2"/><trkpt lat="1.1" lon="2.1"/>'
        "</trkseg></trk></gpx>"
    )
    out = tmp_path / "g.geojson"
    _conv("gpx", "geojson", src, out)
    fc = json.loads(out.read_text())
    assert fc["type"] == "FeatureCollection"
    kinds = {f["geometry"]["type"] for f in fc["features"]}
    assert kinds == {"Point", "LineString"}


def test_kml_to_geojson(tmp_path):
    src = tmp_path / "k.kml"
    src.write_text(
        '<kml><Placemark><name>Home</name><Point>'
        "<coordinates>2.0,1.0,0</coordinates></Point></Placemark></kml>"
    )
    out = tmp_path / "k.geojson"
    _conv("kml", "geojson", src, out)
    fc = json.loads(out.read_text())
    assert fc["features"][0]["geometry"] == {"type": "Point", "coordinates": [2.0, 1.0]}
    assert fc["features"][0]["properties"]["name"] == "Home"


# --------------------------------------------------------------------------- #
# Subtitles SRT <-> VTT
# --------------------------------------------------------------------------- #

SRT = ("1\n00:00:01,000 --> 00:00:02,500\nHello\n\n"
       "2\n00:00:03,000 --> 00:00:04,000\nWorld\n")


def test_srt_to_vtt(tmp_path):
    src = tmp_path / "s.srt"
    src.write_text(SRT)
    out = tmp_path / "s.vtt"
    _conv("srt", "vtt", src, out)
    text = out.read_text()
    assert text.startswith("WEBVTT")
    assert "00:00:01.000 --> 00:00:02.500" in text  # '.' not ','
    assert "1\n00:00:01" not in text  # numeric index dropped


def test_vtt_srt_roundtrip(tmp_path):
    src = tmp_path / "s.srt"
    src.write_text(SRT)
    vtt = tmp_path / "s.vtt"
    _conv("srt", "vtt", src, vtt)
    back = tmp_path / "s2.srt"
    _conv("vtt", "srt", vtt, back)
    text = back.read_text()
    assert "1\n00:00:01,000 --> 00:00:02,500\nHello" in text
    assert "2\n00:00:03,000 --> 00:00:04,000\nWorld" in text


# --------------------------------------------------------------------------- #
# Graphics
# --------------------------------------------------------------------------- #

pytest.importorskip("PIL")


def _png(path, size=(16, 16)):
    from PIL import Image

    Image.new("RGBA", size, (0, 128, 255, 255)).save(path)


def test_image_to_pdf(tmp_path):
    src = tmp_path / "x.png"
    _png(src)
    out = tmp_path / "x.pdf"
    _conv("png", "pdf", src, out)
    assert out.read_bytes()[:5] == b"%PDF-"


def test_png_to_base64_datauri(tmp_path):
    src = tmp_path / "x.png"
    _png(src)
    out = tmp_path / "x.b64"
    _conv("png", "b64", src, out)
    assert out.read_text().startswith("data:image/png;base64,")


def test_png_to_ascii(tmp_path):
    src = tmp_path / "x.png"
    _png(src, size=(20, 20))
    out = tmp_path / "x.txt"
    _conv("png", "txt", src, out)
    lines = out.read_text().splitlines()
    assert len(lines) >= 1 and all(len(ln) <= 100 for ln in lines)


def test_dependency_gated_graphics_routes_registered():
    assert registry.get("txt", "png").requires == ("qrcode",)
    assert registry.get("svg", "png").requires == ("cairosvg",)
    assert registry.get("pdf", "png").requires == ("fitz",)


# --------------------------------------------------------------------------- #
# Chained conversions
# --------------------------------------------------------------------------- #

def test_find_path_md_to_pdf():
    path = registry.find_path("md", "pdf")
    assert path is not None
    assert [c.route for c in path] == [("md", "txt"), ("txt", "pdf")]


def test_find_path_none_when_unreachable():
    assert registry.find_path("png", "totallybogusext") is None


def test_find_path_same_ext_is_empty():
    assert registry.find_path("txt", "txt") == []


def test_chained_md_to_pdf_via_cli(tmp_path, capsys):
    from fileforge.cli import _do_convert
    import argparse

    src = tmp_path / "doc.md"
    src.write_text("# Title\n\nHello **world**\n")
    dst = tmp_path / "doc.pdf"
    ns = argparse.Namespace(source=str(src), target=str(dst), to=None, quality=90)
    rc = _do_convert(ns)
    out = capsys.readouterr().out
    assert rc == 0
    assert "chaining via: md -> txt -> pdf" in out
    assert dst.read_bytes()[:5] == b"%PDF-"
