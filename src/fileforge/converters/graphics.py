"""Graphics-oriented "custom" converters.

- ``png/jpg -> b64``: a ready-to-embed ``data:`` URI (pure standard library).
- ``png -> txt``: ASCII-art rendering (Pillow).
- ``txt -> png``: a QR code for the file's text/URL (needs the ``qrcode`` lib).
- ``svg -> png``: rasterize vector art (needs ``cairosvg``).
- ``pdf -> png``: render the first page (needs ``pymupdf``).

The last three declare their optional deps via ``requires`` so they appear in
``fileforge doctor`` / ``fileforge list`` and light up automatically once the
dependency is installed — no base-install bloat.
"""

from __future__ import annotations

import base64
from pathlib import Path

from fileforge.core.registry import ConversionError, registry

_MIME = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp"}


def _to_data_uri(source: Path, target: Path) -> Path:
    src = Path(source)
    ext = src.suffix.lower().lstrip(".")
    mime = _MIME.get(ext, "application/octet-stream")
    b64 = base64.b64encode(src.read_bytes()).decode("ascii")
    Path(target).write_text(f"data:{mime};base64,{b64}\n", encoding="utf-8")
    return target


for _src in ("png", "jpg", "jpeg", "webp"):
    registry.add(_src, "b64", description=f"{_src.upper()} -> base64 data: URI")(_to_data_uri)


# --------------------------------------------------------------------------- #
# ASCII art  (png -> txt)
# --------------------------------------------------------------------------- #

_ASCII_RAMP = "@%#*+=-:. "  # dark -> light


@registry.add("png", "txt", description="PNG -> ASCII art (text)", requires=["PIL"])
def png_to_ascii(source: Path, target: Path, *, width: int = 100, **_) -> Path:
    from PIL import Image

    img = Image.open(source).convert("L")
    w, h = img.size
    # Characters are ~twice as tall as wide, so halve the row count.
    new_w = min(width, w) or 1
    new_h = max(1, int(new_w * h / w * 0.5))
    img = img.resize((new_w, new_h))
    px = img.tobytes()  # one byte per pixel in mode "L"
    n = len(_ASCII_RAMP)
    chars = [_ASCII_RAMP[min(n - 1, p * n // 256)] for p in px]
    lines = ["".join(chars[i:i + new_w]) for i in range(0, len(chars), new_w)]
    Path(target).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target


# --------------------------------------------------------------------------- #
# QR code  (txt -> png)
# --------------------------------------------------------------------------- #

@registry.add("txt", "png", description="Text/URL -> QR code PNG", requires=["qrcode"])
def txt_to_qr(source: Path, target: Path, **_) -> Path:
    try:
        import qrcode
    except ImportError as exc:  # pragma: no cover
        raise ConversionError(
            "QR generation needs the qrcode package — `pip install qrcode`"
        ) from exc
    data = Path(source).read_text(encoding="utf-8").strip()
    if not data:
        raise ConversionError("txt -> png (QR) needs non-empty text")
    qrcode.make(data).save(target)
    return Path(target)


# --------------------------------------------------------------------------- #
# SVG -> PNG  (cairosvg)
# --------------------------------------------------------------------------- #

@registry.add("svg", "png", description="SVG -> PNG (rasterize)", requires=["cairosvg"])
def svg_to_png(source: Path, target: Path, **_) -> Path:
    try:
        import cairosvg
    except ImportError as exc:  # pragma: no cover
        raise ConversionError(
            "svg -> png needs cairosvg — `pip install cairosvg`"
        ) from exc
    cairosvg.svg2png(url=str(source), write_to=str(target))
    return Path(target)


# --------------------------------------------------------------------------- #
# PDF -> PNG  (first page, pymupdf)
# --------------------------------------------------------------------------- #

@registry.add("pdf", "png", description="PDF first page -> PNG (pymupdf)", requires=["fitz"])
def pdf_to_png(source: Path, target: Path, *, dpi: int = 150, **_) -> Path:
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:  # pragma: no cover
        raise ConversionError(
            "pdf -> png needs PyMuPDF — `pip install pymupdf`"
        ) from exc
    doc = fitz.open(str(source))
    if doc.page_count == 0:
        raise ConversionError("pdf -> png: document has no pages")
    page = doc.load_page(0)
    page.get_pixmap(dpi=dpi).save(str(target))
    return Path(target)
