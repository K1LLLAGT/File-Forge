"""FileForge command-line interface (free tier entry point).

    fileforge convert input.png output.jpg
    fileforge convert notes.md notes.html
    fileforge list
    fileforge list --source png
    fileforge batch ./images png jpg --recursive --workers 8   # Pro
    fileforge license --status

Pro subcommands (batch, ocr, pdf) resolve their gate through the license
key in $FILEFORGE_LICENSE and fail with a clear upgrade message otherwise.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fileforge import __version__
from fileforge.core.registry import ConversionError, load_builtin_converters, registry
from fileforge.licensing import current_license


def _do_convert(args: argparse.Namespace) -> int:
    source, target = Path(args.source), Path(args.target)
    if not source.exists():
        print(f"error: no such file: {source}", file=sys.stderr)
        return 2
    src_ext = source.suffix.lstrip(".").lower()
    tgt_ext = (args.to or target.suffix.lstrip(".")).lower()
    conv = registry.get(src_ext, tgt_ext)
    if conv is None:
        print(f"error: no converter for {src_ext} -> {tgt_ext}", file=sys.stderr)
        alts = registry.targets_for(src_ext)
        if alts:
            print(f"  {src_ext} can convert to: {', '.join(alts)}", file=sys.stderr)
        return 3
    if not conv.available():
        print(
            f"error: converter {src_ext}->{tgt_ext} needs optional deps: "
            f"{', '.join(conv.requires)}",
            file=sys.stderr,
        )
        return 4
    try:
        out = conv.fn(source, target, quality=args.quality)
    except ConversionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 5
    print(f"ok: {source} -> {out}")
    return 0


def _do_list(args: argparse.Namespace) -> int:
    lic = current_license()
    routes = registry.routes(tier=lic.tier.name.lower())
    if args.source:
        routes = [c for c in routes if c.source_ext == args.source.lower()]
    if not routes:
        print("no matching converters")
        return 0
    print(f"available conversions (tier: {lic.name}):")
    for c in routes:
        flag = "" if c.available() else "  [needs: %s]" % ", ".join(c.requires)
        star = "" if c.tier == "free" else f"  ({c.tier})"
        print(f"  {c.source_ext:>6} -> {c.target_ext:<6} {c.description}{star}{flag}")
    return 0


def _do_batch(args: argparse.Namespace) -> int:
    from fileforge.pro.batch import convert_batch  # imported lazily (Pro)

    def _progress(res) -> None:
        mark = "ok " if res.ok else "ERR"
        detail = res.target if res.ok else res.error
        print(f"  [{mark}] {res.source} -> {detail}")

    try:
        results = convert_batch(
            Path(args.directory), args.source_ext, args.target_ext,
            out_dir=Path(args.out) if args.out else None,
            recursive=args.recursive, workers=args.workers,
            on_progress=_progress,
        )
    except PermissionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 6
    except ConversionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 5
    ok = sum(1 for r in results if r.ok)
    print(f"done: {ok}/{len(results)} converted")
    return 0 if ok == len(results) else 7


def _do_license(args: argparse.Namespace) -> int:
    lic = current_license()
    status = "valid" if lic.valid else "invalid/absent (running FREE)"
    print(f"tier:    {lic.name}")
    print(f"subject: {lic.subject}")
    print(f"key:     {status}")
    return 0


def _do_video(args: argparse.Namespace) -> int:
    from fileforge.pro.video import PRESETS, compress  # lazily imported (Pro)

    if args.list_presets:
        print("video presets:")
        for p in PRESETS.values():
            print(f"  {p.name:<11} {p.description}")
        return 0
    if not args.source or not args.target:
        print("error: source and target are required (or use --list-presets)", file=sys.stderr)
        return 2
    try:
        out = compress(args.source, args.target, preset=args.preset)
    except PermissionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 6
    except ConversionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 5
    print(f"ok: {args.source} -> {out} (preset: {args.preset})")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="fileforge", description="FileForge file converter")
    p.add_argument("--version", action="version", version=f"fileforge {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    c = sub.add_parser("convert", help="convert a single file")
    c.add_argument("source")
    c.add_argument("target")
    c.add_argument("--to", help="target format override (else inferred from target ext)")
    c.add_argument("--quality", type=int, default=90, help="quality for lossy image targets")
    c.set_defaults(func=_do_convert)

    l = sub.add_parser("list", help="list available conversions for your tier")
    l.add_argument("--source", help="filter by source extension")
    l.set_defaults(func=_do_list)

    b = sub.add_parser("batch", help="batch-convert a directory (Pro)")
    b.add_argument("directory")
    b.add_argument("source_ext")
    b.add_argument("target_ext")
    b.add_argument("--out", help="output directory (default: in place)")
    b.add_argument("--recursive", action="store_true")
    b.add_argument("--workers", type=int, default=None)
    b.set_defaults(func=_do_batch)

    lic = sub.add_parser("license", help="show license/tier status")
    lic.add_argument("--status", action="store_true")
    lic.set_defaults(func=_do_license)

    v = sub.add_parser("video", help="compress/transcode video with a preset (Pro)")
    v.add_argument("source", nargs="?")
    v.add_argument("target", nargs="?")
    v.add_argument("--preset", default="balanced", help="preset name (see --list-presets)")
    v.add_argument("--list-presets", action="store_true", help="list available presets")
    v.set_defaults(func=_do_video)
    return p


def main(argv: list[str] | None = None) -> int:
    load_builtin_converters()
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
