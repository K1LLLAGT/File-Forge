"""OCR (Pro tier) — image/scanned-PDF -> text via Tesseract (pytesseract)."""

from __future__ import annotations

from pathlib import Path

from fileforge.core.registry import ConversionError
from fileforge.licensing import License, Tier, require


def ocr_image(source: Path, target: Path, *, lang: str = "eng", license: License | None = None) -> Path:
    require(Tier.PRO, license)
    try:
        import pytesseract  # optional dependency
        from PIL import Image  # optional dependency
    except ImportError as exc:  # pragma: no cover
        raise ConversionError(
            "OCR needs Tesseract + pytesseract + Pillow — "
            "install the binary and `pip install fileforge[ocr]`"
        ) from exc

    text = pytesseract.image_to_string(Image.open(source), lang=lang)
    Path(target).write_text(text, encoding="utf-8")
    return Path(target)
