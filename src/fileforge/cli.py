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


def _run_chain(source, target, src_ext, tgt_ext, chain) -> int:
    """Execute a multi-step conversion chain through temporary intermediates."""
    import os
    import tempfile

    steps = " -> ".join([src_ext] + [c.target_ext for c in chain])
    print(f"no direct {src_ext} -> {tgt_ext} converter; chaining via: {steps}")
    current = Path(source)
    temps = []
    try:
        for i, conv in enumerate(chain):
            if i == len(chain) - 1:
                out = Path(target)
            else:
                fd, name = tempfile.mkstemp(suffix=f".{conv.target_ext}")
                os.close(fd)
                out = Path(name)
                temps.append(out)
            conv.fn(current, out)
            current = out
        print(f"ok: {source} -> {target} (via {steps})")
        return 0
    except ConversionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 5
    except Exception as exc:  # noqa: BLE001
        print(f"error: chained conversion failed: {exc}", file=sys.stderr)
        return 6
    finally:
        for t in temps:
            try:
                t.unlink()
            except OSError:
                pass


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
        # No direct converter — try a chained route (e.g. md -> txt -> pdf).
        chain = registry.find_path(src_ext, tgt_ext)
        if chain:
            return _run_chain(source, target, src_ext, tgt_ext, chain)
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
    from fileforge.converters.batch import convert_batch  # imported lazily (Pro)

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


# Optional Python dependency -> (pip extra, human label). Drives `doctor`.
_OPTIONAL_DEPS = {
    "PIL": ("images", "Pillow — image conversions"),
    "pypdf": ("pdf", "pypdf — PDF text extraction / merge / split"),
    "pytesseract": ("ocr", "pytesseract — OCR"),
    "openpyxl": ("xlsx", "openpyxl — Excel (.xlsx)"),
    "yaml": ("yaml", "PyYAML — YAML"),
    "xmltodict": ("xml", "xmltodict — XML"),
    "tomli": ("toml", "tomli — TOML"),
    "pyttsx3": ("tts", "pyttsx3 — text to speech"),
}


def _needs_ffmpeg(conv) -> bool:
    return "ffmpeg" in conv.description.lower()


def _do_doctor(args: argparse.Namespace) -> int:
    """Report which optional deps are installed and which conversions are
    actually usable right now — so 'no converter'/'needs deps' surprises are
    diagnosable in one command."""
    import importlib.util
    import shutil

    has_ffmpeg = shutil.which("ffmpeg") is not None

    def ready(conv) -> bool:
        if not conv.available():          # required Python modules present?
            return False
        if _needs_ffmpeg(conv) and not has_ffmpeg:
            return False
        return True

    routes = registry.routes()
    ready_routes = [c for c in routes if ready(c)]
    blocked = [c for c in routes if not ready(c)]

    print(f"FileForge {__version__} — doctor\n")

    print("optional Python packages:")
    for mod, (extra, label) in _OPTIONAL_DEPS.items():
        ok = importlib.util.find_spec(mod) is not None
        mark = "ok " if ok else "  —"
        hint = "" if ok else f"    → pip install 'pyfile-convert[{extra}]'"
        print(f"  [{mark}] {label}{hint}")

    print("\nsystem tools:")
    mark = "ok " if has_ffmpeg else "  —"
    hint = "" if has_ffmpeg else "    → install ffmpeg (apt / brew / pkg)"
    print(f"  [{mark}] ffmpeg — video & audio conversions{hint}")

    print(f"\nconversions: {len(ready_routes)}/{len(routes)} ready to use")

    if args.list:
        if ready_routes:
            print("\nready:")
            for c in ready_routes:
                print(f"  {c.source_ext:>6} -> {c.target_ext}")
        if blocked:
            print("\nneeds a dependency:")
            for c in blocked:
                if c.requires:
                    need = ", ".join(c.requires)
                elif _needs_ffmpeg(c):
                    need = "ffmpeg"
                else:
                    need = "?"
                print(f"  {c.source_ext:>6} -> {c.target_ext:<6} [needs: {need}]")
    elif blocked:
        print(f"  {len(blocked)} route(s) need extra deps — "
              f"run `fileforge doctor --list` for details")

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

    # doctor
    doctor_parser = subparsers.add_parser(
        "doctor", help="report installed deps and which conversions are usable"
    )
    doctor_parser.add_argument(
        "--list", action="store_true", help="list every route and its status"
    )
    doctor_parser.set_defaults(func=_do_doctor)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
