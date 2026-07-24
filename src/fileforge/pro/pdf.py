"""PDF merge / split (Pro tier). Uses ``pypdf`` when available."""

from __future__ import annotations

from pathlib import Path
from typing import List, Sequence

from fileforge.core.registry import ConversionError
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
