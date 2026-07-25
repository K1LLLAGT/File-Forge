"""PDF merge / split (Pro tier). Uses ``pypdf`` when available."""

from __future__ import annotations

from pathlib import Path
from typing import List, Sequence

from fileforge.core.registry import ConversionError, registry
from fileforge.licensing import License, Tier, require


def _pypdf():
    try:
        import pypdf  # optional dependency
        return pypdf
    except ImportError as exc:  # pragma: no cover
        raise ConversionError(
            "PDF merge/split needs pypdf — install with `pip install fileforge[pdf]`"
        ) from exc


def merge_pdfs(inputs: Sequence[Path], target: Path, *, license: License | None = None) -> Path:
    require(Tier.PRO, license)
    pypdf = _pypdf()
    writer = pypdf.PdfWriter()
    for path in inputs:
        reader = pypdf.PdfReader(str(path))
        for page in reader.pages:
            writer.add_page(page)
    with open(target, "wb") as fh:
        writer.write(fh)
    return Path(target)


def split_pdf(source: Path, out_dir: Path, *, license: License | None = None) -> List[Path]:
    require(Tier.PRO, license)
    pypdf = _pypdf()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    reader = pypdf.PdfReader(str(source))
    outputs: List[Path] = []
    for i, page in enumerate(reader.pages, start=1):
        writer = pypdf.PdfWriter()
        writer.add_page(page)
        dst = out_dir / f"{Path(source).stem}_p{i:03d}.pdf"
        with open(dst, "wb") as fh:
            writer.write(fh)
        outputs.append(dst)
    return outputs


def extract_text(source: Path, target: Path, **options) -> Path:
    """Extract a PDF's embedded text into a plain-text file (one blank line
    between pages). Works on text-based PDFs; scanned/image PDFs yield little
    or nothing — use the OCR path for those."""
    pypdf = _pypdf()
    reader = pypdf.PdfReader(str(source))
    pages = [(page.extract_text() or "").rstrip() for page in reader.pages]
    Path(target).write_text("\n\n".join(pages) + "\n", encoding="utf-8")
    return Path(target)


def _register_routes() -> None:
    # Text extraction is a free, everyday operation; merge/split stay in the
    # Pro-tagged (dormant) functions above.
    registry.add(
        "pdf", "txt",
        description="PDF -> extracted plain text (pypdf)",
        requires=["pypdf"],
    )(extract_text)


_register_routes()
