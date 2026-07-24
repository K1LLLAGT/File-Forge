"""Kotlin <-> FileForge bridge (runs inside Chaquopy's embedded CPython).

Keeps the Android/Kotlin side simple: it calls three small functions instead of
poking at the registry directly. All real work happens in the published
``fileforge`` package that Chaquopy installed from PyPI (pyfile-convert).
"""

from pathlib import Path

from fileforge.core.registry import load_builtin_converters, registry

_loaded = False


def _ensure() -> None:
    global _loaded
    if not _loaded:
        load_builtin_converters()
        _loaded = True


def targets_for(ext: str):
    """List of target extensions a given source extension can convert to."""
    _ensure()
    return registry.targets_for(ext.lower().lstrip("."))


def can_convert(src_ext: str, dst_ext: str) -> bool:
    _ensure()
    conv = registry.get(src_ext.lower().lstrip("."), dst_ext.lower().lstrip("."))
    return conv is not None and conv.available()


def convert(src_path: str, dst_path: str) -> str:
    """Convert src_path -> dst_path (extensions inferred). Returns dst_path.
    Raises ValueError with a readable message on any failure."""
    _ensure()
    src, dst = Path(src_path), Path(dst_path)
    s_ext = src.suffix.lower().lstrip(".")
    d_ext = dst.suffix.lower().lstrip(".")
    conv = registry.get(s_ext, d_ext)
    if conv is None:
        raise ValueError(f"No converter for {s_ext} -> {d_ext}")
    if not conv.available():
        raise ValueError(f"Needs optional dependency: {', '.join(conv.requires)}")
    conv.fn(src, dst)
    return str(dst)
