import json

import pytest

from fileforge.core.registry import load_builtin_converters, registry
from fileforge.licensing import Tier, issue_key, validate_key, current_license


@pytest.fixture(autouse=True, scope="module")
def _load():
    load_builtin_converters()


def test_json_to_csv_roundtrip(tmp_path):
    src = tmp_path / "data.json"
    src.write_text(json.dumps([{"a": 1, "b": 2}, {"a": 3, "b": 4}]))
    dst = tmp_path / "data.csv"
    registry.get("json", "csv").fn(src, dst)
    lines = dst.read_text().strip().splitlines()
    assert lines[0] == "a,b"
    assert lines[1] == "1,2"


def test_csv_to_json(tmp_path):
    src = tmp_path / "t.csv"
    src.write_text("name,age\nAda,36\n")
    dst = tmp_path / "t.json"
    registry.get("csv", "json").fn(src, dst)
    data = json.loads(dst.read_text())
    assert data == [{"name": "Ada", "age": "36"}]


def test_md_to_html(tmp_path):
    src = tmp_path / "n.md"
    src.write_text("# Title\n\nHello **world** and `code`.")
    dst = tmp_path / "n.html"
    registry.get("md", "html").fn(src, dst)
    html = dst.read_text()
    assert "<h1>Title</h1>" in html
    assert "<strong>world</strong>" in html


def test_html_to_txt(tmp_path):
    src = tmp_path / "p.html"
    src.write_text("<h1>Hi</h1><p>a<br>b</p><script>x=1</script>")
    dst = tmp_path / "p.txt"
    registry.get("html", "txt").fn(src, dst)
    text = dst.read_text()
    assert "Hi" in text and "x=1" not in text


def test_txt_to_pdf_is_valid_pdf(tmp_path):
    src = tmp_path / "doc.txt"
    src.write_text("hello pdf\n" * 100)
    dst = tmp_path / "doc.pdf"
    registry.get("txt", "pdf").fn(src, dst)
    blob = dst.read_bytes()
    assert blob.startswith(b"%PDF-1.4")
    assert blob.rstrip().endswith(b"%%EOF")


def test_registry_targets_for():
    assert "csv" in registry.targets_for("json")


def test_image_routes_registered_even_without_pillow():
    conv = registry.get("png", "jpg")
    assert conv is not None
    assert conv.tier == "free"
