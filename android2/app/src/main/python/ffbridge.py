"""Kotlin <-> FileForge 2.0 bridge (runs inside Chaquopy's embedded CPython).

This is the re-branded FileForge 2.0 bridge. On top of the plain convert path
it exposes the FileForge 2.0 **suggestion layer** so the UI can offer ranked,
directory-aware target formats instead of a bare alphabetical list.

Kotlin calls a handful of small functions; all real work happens in the
published ``fileforge`` package (pyfile-convert) that Chaquopy installs.
"""

from pathlib import Path

from fileforge.core.registry import load_builtin_converters, registry
from fileforge.suggestions import GENERIC_ROUTES, scan_directory, suggest

_loaded = False


def _ensure() -> None:
    global _loaded
    if not _loaded:
        load_builtin_converters()
        _loaded = True


def targets_for(ext: str):
    """Engine-supported target extensions for a source extension."""
    _ensure()
    return registry.targets_for(ext.lower().lstrip("."))


def ranked_targets(ext: str):
    """Return targets for *ext*, engine-supported first then common/generic.

    Each item is a two-element ``[target, supported]`` list so Kotlin can read
    it with ``pair[0].toString()`` / ``pair[1].toBoolean()`` and grey out
    generic (not-yet-supported) routes.
    """
    _ensure()
    src = ext.lower().lstrip(".")
    supported = registry.targets_for(src)
    out = [[t, True] for t in supported]
    for t in GENERIC_ROUTES.get(src, []):
        if t not in supported:
            out.append([t, False])
    return out


def suggest_dir(directory: str, recursive: bool = False):
    """Scan a directory and return ranked conversion suggestions.

    Powers an optional "scan a folder" screen. Returns a list of dicts:
    ``{"source_ext","target_ext","count","supported","tier"}``.
    """
    _ensure()
    scan = scan_directory(directory, recursive=recursive)
    return [
        {
            "source_ext": s.source_ext,
            "target_ext": s.target_ext,
            "count": s.count,
            "supported": s.supported,
            "tier": s.tier,
        }
        for s in suggest(scan)
    ]


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
