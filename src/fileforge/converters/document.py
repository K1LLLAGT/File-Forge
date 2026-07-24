"""Document converters. TXT -> PDF is implemented as a pure-Python minimal
PDF writer so the free tier can produce real, spec-valid PDFs with no
third-party dependency. Richer PDF handling (merge/split, OCR) lives in the
Pro tier.
"""

from __future__ import annotations

from pathlib import Path

from fileforge.core.registry import registry

_PAGE_W, _PAGE_H = 612, 792  # US Letter, 72 dpi points
_MARGIN = 54
_LEADING = 14
_FONT_SIZE = 11
_MAX_LINES = int((_PAGE_H - 2 * _MARGIN) / _LEADING)


def _escape(text: str) -> str:
    return text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def _wrap(line: str, width: int = 95):
    if not line:
        return [""]
    chunks, current = [], ""
    for word in line.split(" "):
        if len(current) + len(word) + 1 > width and current:
            chunks.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
    chunks.append(current)
    return chunks


def _build_pdf(pages: list[list[str]]) -> bytes:
    objects: list[bytes] = []

    def add(obj: bytes) -> int:
        objects.append(obj)
        return len(objects)

    font_id = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>")

    kids, page_ids = [], []
    for lines in pages:
        stream_lines = [b"BT", f"/F1 {_FONT_SIZE} Tf".encode(), f"{_LEADING} TL".encode(),
                        f"{_MARGIN} {_PAGE_H - _MARGIN} Td".encode()]
        for ln in lines:
            stream_lines.append(f"({_escape(ln)}) Tj".encode())
            stream_lines.append(b"T*")
        stream_lines.append(b"ET")
        stream = b"\n".join(stream_lines)
        content_id = add(b"<< /Length %d >>\nstream\n%s\nendstream" % (len(stream), stream))
        page_id = add(b"")  # placeholder, patched below
        page_ids.append((page_id, content_id))
        kids.append(page_id)

    pages_id = add(b"")  # placeholder
    for page_id, content_id in page_ids:
        objects[page_id - 1] = (
            b"<< /Type /Page /Parent %d 0 R /MediaBox [0 0 %d %d] "
            b"/Resources << /Font << /F1 %d 0 R >> >> /Contents %d 0 R >>"
            % (pages_id, _PAGE_W, _PAGE_H, font_id, content_id)
        )
    kids_ref = b" ".join(b"%d 0 R" % k for k in kids)
    objects[pages_id - 1] = (
        b"<< /Type /Pages /Count %d /Kids [%s] >>" % (len(kids), kids_ref)
    )
    catalog_id = add(b"<< /Type /Catalog /Pages %d 0 R >>" % pages_id)

    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n%s\nendobj\n" % (i, obj)
    xref_pos = len(out)
    out += b"xref\n0 %d\n" % (len(objects) + 1)
    out += b"0000000000 65535 f \n"
    for off in offsets[1:]:
        out += b"%010d 00000 n \n" % off
    out += b"trailer\n<< /Size %d /Root %d 0 R >>\nstartxref\n%d\n%%%%EOF" % (
        len(objects) + 1, catalog_id, xref_pos,
    )
    return bytes(out)


@registry.add("txt", "pdf", description="Plain text -> paginated PDF (pure Python)")
def txt_to_pdf(source: Path, target: Path, **_) -> Path:
    text = Path(source).read_text(encoding="utf-8", errors="replace")
    wrapped: list[str] = []
    for raw in text.splitlines() or [""]:
        wrapped.extend(_wrap(raw.rstrip("\n")))
    pages = [wrapped[i:i + _MAX_LINES] for i in range(0, len(wrapped), _MAX_LINES)] or [[""]]
    Path(target).write_bytes(_build_pdf(pages))
    return Path(target)
