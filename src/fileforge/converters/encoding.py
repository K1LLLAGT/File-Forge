"""Encoding converters: Base64 encode/decode for text files.

All routes here are free-tier and depend only on the standard library.
"""

from __future__ import annotations

import base64
from pathlib import Path

from fileforge.core.registry import ConversionError, registry


@registry.add("txt", "b64", description="Plain text -> Base64 encoded")
def txt_to_b64(source: Path, target: Path, **_) -> Path:
    data = Path(source).read_bytes()
    encoded = base64.b64encode(data).decode("ascii")
    Path(target).write_text(encoded, encoding="utf-8")
    return Path(target)


@registry.add("b64", "txt", description="Base64 encoded -> plain text")
def b64_to_txt(source: Path, target: Path, **_) -> Path:
    encoded = Path(source).read_text(encoding="utf-8").strip()
    try:
        decoded = base64.b64decode(encoded)
        Path(target).write_bytes(decoded)
    except Exception as exc:
        raise ConversionError(f"invalid base64: {exc}") from exc
    return Path(target)
