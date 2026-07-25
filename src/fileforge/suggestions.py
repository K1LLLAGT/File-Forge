"""FileForge conversion-suggestion engine.

Scans a directory, tallies file extensions, and proposes conversions. Two
sources feed the suggestions:

1. **Engine routes** — every ``(source, target)`` registered in the shared
   :mod:`fileforge.core.registry`. These are conversions FileForge can perform
   for real, right now.
2. **Generic routes** — well-known conversions people commonly want
   (``png→jpg``, ``mp4→gif``, ``docx→pdf`` …). These are surfaced even when no
   engine converter is registered yet, and are clearly flagged as such.

The engine can also emit runnable driver scripts (``run_conversions.sh`` and
``run_conversions.ps1``) that call ``fileforge convert`` for each planned file.

Public API
----------
- :func:`scan_directory`  — build extension→frequency / extension→samples maps.
- :func:`suggest`         — turn a scan into a list of :class:`Suggestion`.
- :func:`build_plan`      — pick concrete files for chosen conversions.
- :func:`render_bash` / :func:`render_powershell` — driver-script text.
- :func:`main`            — ``fileforge-suggest`` console entry point.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

# --------------------------------------------------------------------------- #
# Generic conversion knowledge (independent of what the engine registers)
# --------------------------------------------------------------------------- #

#: Common conversions people expect, keyed by source extension. These are used
#: as fallbacks/suggestions even when the engine has no converter registered.
GENERIC_ROUTES: Dict[str, List[str]] = {
    "png": ["jpg", "webp", "gif", "bmp", "tiff", "pdf"],
    "jpg": ["png", "webp", "pdf"],
    "jpeg": ["png", "webp", "pdf"],
    "webp": ["png", "jpg"],
    "heic": ["jpg", "png"],
    "bmp": ["png", "jpg"],
    "gif": ["png", "mp4"],
    "mp4": ["gif", "mp3", "webm"],
    "mov": ["mp4", "gif"],
    "mkv": ["mp4"],
    "avi": ["mp4"],
    "webm": ["mp4"],
    "wav": ["mp3", "flac"],
    "flac": ["mp3", "wav"],
    "docx": ["pdf", "txt", "md"],
    "doc": ["pdf", "docx"],
    "odt": ["pdf", "docx"],
    "pptx": ["pdf"],
    "xlsx": ["csv", "json", "tsv", "yaml"],
    "csv": ["json", "xlsx", "tsv"],
    "json": ["csv", "yaml", "xml", "toml", "xlsx"],
    "yaml": ["json", "toml"],
    "toml": ["json", "yaml"],
    "xml": ["json"],
    "md": ["html", "pdf", "txt"],
    "markdown": ["html", "pdf", "txt"],
    "html": ["md", "txt", "pdf"],
    "txt": ["pdf", "md", "b64"],
    "pdf": ["txt", "png"],
}


@dataclass
class Suggestion:
    """One proposed conversion route for extensions present in a directory."""

    source_ext: str
    target_ext: str
    count: int                     # how many source files exist
    supported: bool                # engine has a registered converter
    tier: str = "free"             # engine tier, or "generic" when unsupported
    description: str = ""
    samples: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "source_ext": self.source_ext,
            "target_ext": self.target_ext,
            "count": self.count,
            "supported": self.supported,
            "tier": self.tier,
            "description": self.description,
            "samples": self.samples,
        }


@dataclass
class DirectoryScan:
    """Result of :func:`scan_directory`."""

    root: Path
    frequency: Dict[str, int] = field(default_factory=dict)
    samples: Dict[str, List[str]] = field(default_factory=dict)
    total_files: int = 0

    def to_dict(self) -> dict:
        return {
            "root": str(self.root),
            "total_files": self.total_files,
            "frequency": self.frequency,
            "samples": self.samples,
        }


# --------------------------------------------------------------------------- #
# Scanning
# --------------------------------------------------------------------------- #

_SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}


def scan_directory(
    directory: os.PathLike | str = ".",
    *,
    recursive: bool = False,
    max_samples: int = 3,
) -> DirectoryScan:
    """Walk *directory* and build extension→frequency and extension→samples maps."""
    root = Path(directory).expanduser()
    scan = DirectoryScan(root=root)
    freq: Dict[str, int] = defaultdict(int)
    samples: Dict[str, List[str]] = defaultdict(list)

    if recursive:
        walker = (p for p in root.rglob("*") if p.is_file())
    else:
        walker = (p for p in root.iterdir() if p.is_file())

    for path in walker:
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        ext = path.suffix.lstrip(".").lower()
        if not ext:
            continue
        freq[ext] += 1
        scan.total_files += 1
        if len(samples[ext]) < max_samples:
            try:
                samples[ext].append(str(path.relative_to(root)))
            except ValueError:
                samples[ext].append(str(path))

    scan.frequency = dict(sorted(freq.items(), key=lambda kv: (-kv[1], kv[0])))
    scan.samples = {k: samples[k] for k in scan.frequency}
    return scan


# --------------------------------------------------------------------------- #
# Suggesting
# --------------------------------------------------------------------------- #


def _load_registry():
    """Import and populate the shared registry lazily (keeps import cost low)."""
    from fileforge.core.registry import load_builtin_converters, registry

    load_builtin_converters()
    return registry


def suggest(
    scan: DirectoryScan,
    *,
    include_generic: bool = True,
) -> List[Suggestion]:
    """Turn a :class:`DirectoryScan` into ranked :class:`Suggestion` objects.

    Engine-supported routes come first (highest source-file count first), then
    generic routes for extensions the engine cannot yet handle.
    """
    registry = _load_registry()
    out: List[Suggestion] = []
    emitted: set[Tuple[str, str]] = set()

    for ext, count in scan.frequency.items():
        samples = scan.samples.get(ext, [])

        # 1) Real engine routes for this source extension.
        for target in registry.targets_for(ext):
            conv = registry.get(ext, target)
            if conv is None:
                continue
            out.append(
                Suggestion(
                    source_ext=ext,
                    target_ext=target,
                    count=count,
                    supported=True,
                    tier=conv.tier,
                    description=conv.description,
                    samples=samples,
                )
            )
            emitted.add((ext, target))

        # 2) Generic routes not already covered by the engine.
        if include_generic:
            for target in GENERIC_ROUTES.get(ext, []):
                if (ext, target) in emitted:
                    continue
                supported = registry.get(ext, target) is not None
                if supported:
                    continue  # already emitted above; skip duplicates
                out.append(
                    Suggestion(
                        source_ext=ext,
                        target_ext=target,
                        count=count,
                        supported=False,
                        tier="generic",
                        description="common conversion (no engine route yet)",
                        samples=samples,
                    )
                )
                emitted.add((ext, target))

    # Supported first, then by how many files the conversion would touch.
    out.sort(key=lambda s: (not s.supported, -s.count, s.source_ext, s.target_ext))
    return out


# --------------------------------------------------------------------------- #
# Planning + driver-script generation
# --------------------------------------------------------------------------- #


@dataclass
class PlanItem:
    source: str
    target: str
    source_ext: str
    target_ext: str
    supported: bool


def build_plan(
    scan: DirectoryScan,
    source_ext: str,
    target_ext: str,
    *,
    recursive: bool = False,
) -> List[PlanItem]:
    """Enumerate concrete source→target file pairs for one conversion route."""
    src = source_ext.lstrip(".").lower()
    tgt = target_ext.lstrip(".").lower()
    registry = _load_registry()
    supported = registry.get(src, tgt) is not None

    root = scan.root
    files = (
        (p for p in root.rglob(f"*.{src}") if p.is_file())
        if recursive
        else (p for p in root.glob(f"*.{src}") if p.is_file())
    )
    plan: List[PlanItem] = []
    for path in sorted(files):
        target_path = path.with_suffix(f".{tgt}")
        plan.append(
            PlanItem(
                source=str(path),
                target=str(target_path),
                source_ext=src,
                target_ext=tgt,
                supported=supported,
            )
        )
    return plan


def render_bash(plan: Sequence[PlanItem]) -> str:
    """Render a POSIX ``run_conversions.sh`` driver for *plan*."""
    lines = [
        "#!/usr/bin/env bash",
        "# Generated by fileforge-suggest. Runs one `fileforge convert` per file.",
        "set -euo pipefail",
        "",
        'FILEFORGE="${FILEFORGE:-fileforge}"',
        "",
    ]
    for item in plan:
        s = shlex.quote(item.source)
        t = shlex.quote(item.target)
        if not item.supported:
            lines.append(
                f"# NOTE: {item.source_ext}->{item.target_ext} is a generic "
                "suggestion with no engine route yet."
            )
        lines.append(f'echo "converting {item.source} -> {item.target}"')
        lines.append(f'"$FILEFORGE" convert {s} {t}')
        lines.append("")
    lines.append('echo "done."')
    return "\n".join(lines) + "\n"


def render_powershell(plan: Sequence[PlanItem]) -> str:
    """Render a Windows ``run_conversions.ps1`` driver for *plan*."""
    lines = [
        "# Generated by fileforge-suggest. Runs one `fileforge convert` per file.",
        "$ErrorActionPreference = 'Stop'",
        "$FileForge = if ($env:FILEFORGE) { $env:FILEFORGE } else { 'fileforge' }",
        "",
    ]
    for item in plan:
        s = item.source.replace("'", "''")
        t = item.target.replace("'", "''")
        if not item.supported:
            lines.append(
                f"# NOTE: {item.source_ext}->{item.target_ext} is a generic "
                "suggestion with no engine route yet."
            )
        lines.append(f"Write-Host \"converting {item.source} -> {item.target}\"")
        lines.append(f"& $FileForge convert '{s}' '{t}'")
        lines.append("")
    lines.append("Write-Host 'done.'")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- #
# Rendering + interactive mode
# --------------------------------------------------------------------------- #


def _render_text(scan: DirectoryScan, suggestions: Sequence[Suggestion]) -> str:
    lines = [
        f"scanned: {scan.root}  ({scan.total_files} files, "
        f"{len(scan.frequency)} extensions)",
        "",
    ]
    if not scan.frequency:
        lines.append("no files with recognizable extensions found.")
        return "\n".join(lines)

    lines.append("extensions found:")
    for ext, count in scan.frequency.items():
        sample = scan.samples.get(ext, [])
        preview = f"  e.g. {', '.join(sample)}" if sample else ""
        lines.append(f"  .{ext:<8} x{count}{preview}")
    lines.append("")

    lines.append("suggested conversions:")
    if not suggestions:
        lines.append("  (none)")
    for s in suggestions:
        flag = "" if s.supported else "  [generic — no engine route]"
        tier = "" if s.tier in ("free", "generic") else f" [{s.tier.upper()}]"
        lines.append(
            f"  {s.source_ext:>6} -> {s.target_ext:<6} "
            f"(x{s.count}){tier}{flag}"
        )
    return "\n".join(lines)


def _interactive(scan: DirectoryScan, suggestions: List[Suggestion]) -> List[PlanItem]:
    """Prompt the user to choose a route, then build a plan for it."""
    print(_render_text(scan, suggestions))
    print()
    src = input("source extension to convert (e.g. png): ").strip().lstrip(".").lower()
    tgt = input("target extension (e.g. jpg): ").strip().lstrip(".").lower()
    if not src or not tgt:
        print("nothing selected.")
        return []
    if src not in scan.frequency:
        print(f"warning: no .{src} files were found in {scan.root}")
    plan = build_plan(scan, src, tgt)
    if not plan:
        print(f"no .{src} files to convert.")
    else:
        print(f"\nplan: {len(plan)} file(s) {src} -> {tgt}")
        for item in plan:
            print(f"  {item.source} -> {item.target}")
    return plan


def _write_scripts(plan: Sequence[PlanItem], out_dir: Path) -> List[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    sh_path = out_dir / "run_conversions.sh"
    ps_path = out_dir / "run_conversions.ps1"
    sh_path.write_text(render_bash(plan), encoding="utf-8")
    ps_path.write_text(render_powershell(plan), encoding="utf-8")
    try:
        sh_path.chmod(0o755)
    except OSError:
        pass
    return [sh_path, ps_path]


# --------------------------------------------------------------------------- #
# CLI — ``fileforge-suggest``
# --------------------------------------------------------------------------- #


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Entry point for the ``fileforge-suggest`` console script."""
    parser = argparse.ArgumentParser(
        prog="fileforge-suggest",
        description="Scan a directory and suggest file conversions.",
    )
    parser.add_argument("directory", nargs="?", default=".", help="directory to scan")
    parser.add_argument("--recursive", action="store_true", help="recurse into subdirs")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    parser.add_argument(
        "--no-generic",
        action="store_true",
        help="only show conversions the engine can actually perform",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="ask for a route and print a conversion plan",
    )
    parser.add_argument(
        "--emit-scripts",
        nargs="?",
        const=".",
        metavar="OUT_DIR",
        help="write run_conversions.sh/.ps1 (needs --source/--target or --interactive)",
    )
    parser.add_argument("--source", help="source extension for a plan (e.g. png)")
    parser.add_argument("--target", help="target extension for a plan (e.g. jpg)")
    args = parser.parse_args(argv)

    scan = scan_directory(args.directory, recursive=args.recursive)
    suggestions = suggest(scan, include_generic=not args.no_generic)

    # Interactive / explicit plan mode.
    plan: List[PlanItem] = []
    if args.interactive:
        plan = _interactive(scan, suggestions)
    elif args.source and args.target:
        plan = build_plan(scan, args.source, args.target, recursive=args.recursive)

    if args.emit_scripts is not None:
        if not plan:
            print(
                "error: --emit-scripts needs a plan "
                "(use --interactive, or --source and --target).",
                file=sys.stderr,
            )
            return 2
        written = _write_scripts(plan, Path(args.emit_scripts))
        for p in written:
            print(f"wrote {p}")
        return 0

    if args.json:
        payload = {
            "scan": scan.to_dict(),
            "suggestions": [s.to_dict() for s in suggestions],
        }
        if plan:
            payload["plan"] = [vars(p) for p in plan]
        print(json.dumps(payload, indent=2))
    elif not args.interactive:
        print(_render_text(scan, suggestions))

    return 0


if __name__ == "__main__":
    sys.exit(main())
