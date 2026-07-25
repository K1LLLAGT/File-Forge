"""FileForge unified interaction layer (``fileforge-cli``).

Ties the three standalone subsystems together into one flow:

- :mod:`fileforge.discovery`   — normalize aliases, enumerate instances.
- :mod:`fileforge.suggestions` — scan a directory, propose conversions.
- :mod:`fileforge.core.registry` — the real conversion routes.

Given a set of user-provided aliases and/or extensions plus a directory, it
produces a **personalized conversion matrix**, a ranked list of recommended
conversions, and (optionally) runnable driver scripts.

Usage
-----
    fileforge-cli --dir ./assets
    fileforge-cli --alias "File Forge" --alias fileforge
    fileforge-cli --dir . --ext png --ext csv --emit-scripts out/
    fileforge-cli --interactive
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from fileforge import discovery, suggestions


@dataclass
class MatrixCell:
    """One entry in the personalized conversion matrix."""

    source_ext: str
    targets: List[str] = field(default_factory=list)          # engine-supported
    generic_targets: List[str] = field(default_factory=list)  # common, no route
    count: int = 0

    def to_dict(self) -> dict:
        return {
            "source_ext": self.source_ext,
            "targets": self.targets,
            "generic_targets": self.generic_targets,
            "count": self.count,
        }


@dataclass
class UnifiedReport:
    directory: str
    aliases: Dict[str, Optional[str]] = field(default_factory=dict)
    instances: List[dict] = field(default_factory=list)
    matrix: List[MatrixCell] = field(default_factory=list)
    recommendations: List[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "directory": self.directory,
            "aliases": self.aliases,
            "instances": self.instances,
            "matrix": [c.to_dict() for c in self.matrix],
            "recommendations": self.recommendations,
        }


def _build_matrix(
    scan: suggestions.DirectoryScan,
    sugg: Sequence[suggestions.Suggestion],
    *,
    only_exts: Optional[Sequence[str]] = None,
) -> List[MatrixCell]:
    """Fold the flat suggestion list into a per-source-extension matrix."""
    wanted = {e.lstrip(".").lower() for e in only_exts} if only_exts else None
    cells: Dict[str, MatrixCell] = {}
    for s in sugg:
        if wanted is not None and s.source_ext not in wanted:
            continue
        cell = cells.setdefault(
            s.source_ext,
            MatrixCell(source_ext=s.source_ext, count=s.count),
        )
        if s.supported:
            if s.target_ext not in cell.targets:
                cell.targets.append(s.target_ext)
        else:
            if s.target_ext not in cell.generic_targets:
                cell.generic_targets.append(s.target_ext)

    # Include user-requested extensions that had zero files, so the matrix
    # still tells the user what *would* be possible.
    if wanted:
        registry = suggestions._load_registry()
        for ext in wanted:
            if ext in cells:
                continue
            targets = registry.targets_for(ext)
            generic = [
                t for t in suggestions.GENERIC_ROUTES.get(ext, [])
                if registry.get(ext, t) is None
            ]
            if targets or generic:
                cells[ext] = MatrixCell(
                    source_ext=ext,
                    targets=sorted(targets),
                    generic_targets=generic,
                    count=0,
                )

    return sorted(cells.values(), key=lambda c: (-c.count, c.source_ext))


def build_report(
    directory: str = ".",
    *,
    aliases: Optional[Sequence[str]] = None,
    exts: Optional[Sequence[str]] = None,
    recursive: bool = False,
    include_generic: bool = True,
    discover_instances: bool = False,
) -> UnifiedReport:
    """Assemble the full unified report from all subsystems."""
    report = UnifiedReport(directory=str(Path(directory).expanduser()))

    # 1) Resolve any user-provided aliases.
    for alias in aliases or []:
        report.aliases[alias] = discovery.normalize_alias(alias)

    # 2) Optionally enumerate FileForge instances on disk.
    if discover_instances:
        result = discovery.discover([directory])
        report.instances = [i.to_dict() for i in result.instances]

    # 3) Scan + suggest.
    scan = suggestions.scan_directory(directory, recursive=recursive)
    sugg = suggestions.suggest(scan, include_generic=include_generic)

    # 4) Personalized matrix (filtered to user's extensions if given).
    report.matrix = _build_matrix(scan, sugg, only_exts=exts)

    # 5) Top recommendations: supported routes with the most files.
    recs = [s for s in sugg if s.supported]
    if exts:
        wanted = {e.lstrip(".").lower() for e in exts}
        recs = [s for s in recs if s.source_ext in wanted]
    report.recommendations = [s.to_dict() for s in recs[:10]]
    return report


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #


def _render_text(report: UnifiedReport) -> str:
    lines = [f"FileForge unified report — {report.directory}", ""]

    if report.aliases:
        lines.append("alias resolution:")
        for alias, canon in report.aliases.items():
            lines.append(f"  '{alias}' -> {canon or '(not a FileForge alias)'}")
        lines.append("")

    if report.instances:
        lines.append(f"discovered instances: {len(report.instances)}")
        for inst in report.instances:
            roles = ", ".join(inst["roles"]) or "unknown"
            lines.append(f"  • {inst['path']}  [{roles}]")
        lines.append("")

    lines.append("personalized conversion matrix:")
    if not report.matrix:
        lines.append("  (nothing to convert)")
    for cell in report.matrix:
        supported = ", ".join(cell.targets) or "—"
        line = f"  .{cell.source_ext:<8} (x{cell.count}) -> {supported}"
        if cell.generic_targets:
            line += f"   [generic: {', '.join(cell.generic_targets)}]"
        lines.append(line)
    lines.append("")

    lines.append("recommended conversions:")
    if not report.recommendations:
        lines.append("  (none — no engine-supported routes for these files)")
    for rec in report.recommendations:
        tier = "" if rec["tier"] == "free" else f" [{rec['tier'].upper()}]"
        lines.append(
            f"  {rec['source_ext']:>6} -> {rec['target_ext']:<6} "
            f"(x{rec['count']}){tier}  {rec['description']}"
        )
    return "\n".join(lines)


def _interactive() -> UnifiedReport:
    print("FileForge unified CLI — interactive mode\n")
    directory = input("directory to analyze [.]: ").strip() or "."
    alias_raw = input("known aliases (comma-separated, optional): ").strip()
    ext_raw = input("extensions to focus on (comma-separated, optional): ").strip()
    aliases = [a.strip() for a in alias_raw.split(",") if a.strip()]
    exts = [e.strip() for e in ext_raw.split(",") if e.strip()]
    report = build_report(
        directory, aliases=aliases, exts=exts or None, discover_instances=True
    )
    print()
    print(_render_text(report))
    return report


# --------------------------------------------------------------------------- #
# CLI — ``fileforge-cli``
# --------------------------------------------------------------------------- #


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Entry point for the ``fileforge-cli`` console script."""
    parser = argparse.ArgumentParser(
        prog="fileforge-cli",
        description="Unified FileForge: discovery + directory analysis + "
        "conversion suggestions in one report.",
    )
    parser.add_argument("--dir", default=".", help="directory to analyze")
    parser.add_argument(
        "--alias", action="append", default=[], help="a name/alias to resolve (repeatable)"
    )
    parser.add_argument(
        "--ext", action="append", default=[], help="focus the matrix on this extension (repeatable)"
    )
    parser.add_argument("--recursive", action="store_true", help="recurse into subdirs")
    parser.add_argument(
        "--discover", action="store_true", help="also enumerate FileForge instances under --dir"
    )
    parser.add_argument(
        "--no-generic", action="store_true", help="hide generic (unsupported) suggestions"
    )
    parser.add_argument("--json", action="store_true", help="emit JSON")
    parser.add_argument("--interactive", action="store_true", help="prompt for inputs")
    parser.add_argument(
        "--emit-scripts",
        metavar="OUT_DIR",
        help="write run_conversions.sh/.ps1 for the top recommendation",
    )
    args = parser.parse_args(argv)

    if args.interactive:
        report = _interactive()
    else:
        report = build_report(
            args.dir,
            aliases=args.alias,
            exts=args.ext or None,
            recursive=args.recursive,
            include_generic=not args.no_generic,
            discover_instances=args.discover,
        )
        if args.json:
            print(json.dumps(report.to_dict(), indent=2))
        else:
            print(_render_text(report))

    if args.emit_scripts:
        if not report.recommendations:
            print("error: nothing to emit — no supported recommendations.", file=sys.stderr)
            return 2
        top = report.recommendations[0]
        scan = suggestions.scan_directory(args.dir, recursive=args.recursive)
        plan = suggestions.build_plan(
            scan, top["source_ext"], top["target_ext"], recursive=args.recursive
        )
        written = suggestions._write_scripts(plan, Path(args.emit_scripts))
        for p in written:
            print(f"wrote {p}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
