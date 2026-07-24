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


def _format_file_size(bytes_: int) -> str:
    """Format bytes to human-readable size."""
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes_ < 1024:
            return f"{bytes_:.1f}{unit}"
        bytes_ /= 1024
    return f"{bytes_:.1f}TB"


def _do_convert(args: argparse.Namespace) -> int:
    source, target = Path(args.source), Path(args.target)
    if not source.exists():
        print(f"error: no such file: {source}", file=sys.stderr)
        return 2
    
    # Check file size and warn if large
    file_size = source.stat().st_size
    if file_size > 500 * 1024 * 1024:  # 500MB
        print(f"warning: large file ({_format_file_size(file_size)}), conversion may take a while", file=sys.stderr)
    
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
    
    # Check if this is a Pro feature
    if conv.tier != "free":
        license_obj = current_license()
        if not license_obj or license_obj.tier.value < 1:  # FREE = 0, PRO = 1
            print(
                f"error: {src_ext} -> {tgt_ext} is a Pro feature (tier: {conv.tier})",
                file=sys.stderr,
            )
            print(
                f"  Upgrade to Pro: https://fileforge.gumroad.com/l/pro",
                file=sys.stderr,
            )
            print(
                f"  Already a Pro user? Activate your key: fileforge license --activate <key>",
                file=sys.stderr,
            )
            return 7
    
    try:
        out = conv.fn(source, target, quality=args.quality)
        elapsed = ""  # Could add timing here if needed
        print(f"ok: {source} -> {out}{elapsed}")
        return 0
    except ConversionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 5
    except Exception as exc:
        print(f"error: conversion failed: {exc}", file=sys.stderr)
        return 6


def _do_list(args: argparse.Namespace) -> int:
    routes = registry.routes()  # FileForge is free — every conversion is available
    if args.source:
        routes = [c for c in routes if c.source_ext == args.source.lower()]
    if not routes:
        print("no matching converters")
        return 0
    print("available conversions:")
    for c in routes:
        flag = "" if c.available() else "  [needs: %s]" % ", ".join(c.requires)
        tier_badge = "" if c.tier == "free" else f" [{c.tier.upper()}]"
        print(f"  {c.source_ext:>6} -> {c.target_ext:<6} {c.description}{tier_badge}{flag}")
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
    fail = len(results) - ok
    print(f"batch: {ok} ok, {fail} failed")
    return 0 if fail == 0 else 1


def _do_license(args: argparse.Namespace) -> int:
    from fileforge.licensing import generate_keypair, verify_license
    import os
    
    if args.status:
        lic = current_license()
        if lic:
            print(f"tier: {lic.name}")
            print(f"subject: {lic.subject}")
            print(f"valid: {lic.valid}")
        else:
            print("no active license (running free tier)")
        return 0
    
    if args.activate:
        # Try to verify and store the license
        key = args.activate
        try:
            lic = verify_license(key)
            if lic and lic.valid:
                # In production, would store to $HOME/.fileforge/license
                print(f"license activated: {lic.name}")
                return 0
            else:
                print("error: invalid or expired license", file=sys.stderr)
                return 1
        except Exception as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
    
    return 0


def main() -> int:
    load_builtin_converters()
    parser = argparse.ArgumentParser(
        prog="fileforge",
        description="FileForge — free, batteries-included file converter",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", help="subcommand")

    # convert
    convert_parser = subparsers.add_parser("convert", help="convert a file")
    convert_parser.add_argument("source", help="source file")
    convert_parser.add_argument("target", help="target file (format from extension)")
    convert_parser.add_argument("-t", "--to", help="target format (override extension)")
    convert_parser.add_argument(
        "-q", "--quality", type=int, default=90, help="quality for lossy formats (default: 90)"
    )
    convert_parser.set_defaults(func=_do_convert)

    # list
    list_parser = subparsers.add_parser("list", help="list available converters")
    list_parser.add_argument("--source", help="filter by source format")
    list_parser.set_defaults(func=_do_list)

    # batch (Pro)
    batch_parser = subparsers.add_parser("batch", help="batch convert a directory (Pro)")
    batch_parser.add_argument("directory", help="source directory")
    batch_parser.add_argument("source_ext", help="source format")
    batch_parser.add_argument("target_ext", help="target format")
    batch_parser.add_argument("--out", help="output directory (default: same as source)")
    batch_parser.add_argument("--recursive", action="store_true", help="recurse into subdirs")
    batch_parser.add_argument("--workers", type=int, default=4, help="thread pool size")
    batch_parser.set_defaults(func=_do_batch)

    # license
    license_parser = subparsers.add_parser("license", help="manage license")
    license_parser.add_argument("--status", action="store_true", help="show license status")
    license_parser.add_argument("--activate", help="activate a license key")
    license_parser.set_defaults(func=_do_license)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
