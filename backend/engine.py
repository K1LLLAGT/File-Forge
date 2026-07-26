"""
engine.py — FileForge conversion abstraction layer.

Wraps external CLI tools (ffmpeg, ImageMagick, Pandoc, LibreOffice, unzip/tar)
behind a small, consistent Python API. Every other backend module
(batch, ff_queue, compression, thumbnails, server) calls into this file
instead of shelling out directly, so there is exactly one place that
knows how to invoke each tool.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

FFMPEG = "ffmpeg"
IMAGEMAGICK = "convert"
LIBREOFFICE = "libreoffice"
UNOCONV = "unoconv"
PANDOC = "pandoc"
UNZIP = "unzip"
TAR = "tar"

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tiff"}
VIDEO_EXTS = {".mp4", ".mkv", ".mov", ".avi", ".webm"}
AUDIO_EXTS = {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"}
DOC_EXTS = {".docx", ".pptx", ".xlsx", ".doc", ".ppt", ".xls"}

# Optional: the separate src/fileforge CLI/library ships a much broader
# conversion registry (PDF text extraction, subtitles, config formats,
# markup, encoding, structured data, dev-data formats, QR/ASCII-art, SVG
# and PDF rasterization). If it's installed (`pip install -e .` from the
# repo root — see scripts/install_conversion_tools.sh), convert_generic()
# falls back to it for any pair not already handled directly above. This
# is a deliberate exception to "the web app and the CLI/apps product share
# no code" — reusing a well-tested registry beats re-implementing PDF/OCR/
# subtitle/config logic a second time from scratch.
try:
    from fileforge.core.registry import registry as _fileforge_registry
    from fileforge.core.registry import load_builtin_converters as _load_fileforge_converters

    _load_fileforge_converters()
    _FILEFORGE_AVAILABLE = True
except ImportError:
    _fileforge_registry = None
    _FILEFORGE_AVAILABLE = False


class ConversionError(RuntimeError):
    """Raised when an external tool fails or is missing."""


def _require_tool(binary: str) -> None:
    if shutil.which(binary) is None:
        raise ConversionError(
            f"Required tool '{binary}' was not found on PATH. "
            f"Run scripts/install_conversion_tools.sh to install it."
        )


def run(cmd: list[str]) -> None:
    """Run an external command, raising ConversionError with useful context on failure."""
    _require_tool(cmd[0])
    try:
        subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode(errors="replace") if exc.stderr else ""
        raise ConversionError(f"{cmd[0]} failed: {stderr.strip()[:500]}") from exc


# -----------------------------
# IMAGE CONVERSIONS
# -----------------------------
def convert_image(input_path: str, output_path: str) -> None:
    run([IMAGEMAGICK, input_path, output_path])


def convert_svg_to_png(input_path: str, output_path: str) -> None:
    run([IMAGEMAGICK, input_path, output_path])


def convert_heic_to_jpg(input_path: str, output_path: str) -> None:
    run([IMAGEMAGICK, input_path, output_path])


# -----------------------------
# VIDEO CONVERSIONS
# -----------------------------
def convert_video(input_path: str, output_path: str) -> None:
    run([FFMPEG, "-y", "-i", input_path, output_path])


def convert_video_to_gif(input_path: str, output_path: str) -> None:
    # A video file is not a static image ImageMagick can sensibly read, so
    # this must be special-cased ahead of the generic "-> image format"
    # catch below — otherwise convert_generic would wrongly hand an .mp4
    # to ImageMagick instead of ffmpeg. Filter matches the fileforge
    # registry's own "gif" video preset (fps=12, 480px wide, lanczos scale).
    run([FFMPEG, "-y", "-i", input_path, "-vf", "fps=12,scale=480:-1:flags=lanczos", output_path])


def extract_audio(input_path: str, output_path: str) -> None:
    run([FFMPEG, "-y", "-i", input_path, "-vn", output_path])


# -----------------------------
# AUDIO CONVERSIONS
# -----------------------------
def convert_audio(input_path: str, output_path: str) -> None:
    run([FFMPEG, "-y", "-i", input_path, output_path])


# -----------------------------
# DOCUMENT CONVERSIONS
# -----------------------------
def convert_doc_to_pdf(input_path: str, output_dir: str) -> str:
    run([LIBREOFFICE, "--headless", "--convert-to", "pdf", "--outdir", output_dir, input_path])
    return os.path.join(output_dir, os.path.splitext(os.path.basename(input_path))[0] + ".pdf")


def convert_doc_to_html(input_path: str, output_path: str) -> None:
    run([PANDOC, input_path, "-o", output_path])


def convert_md_to_pdf(input_path: str, output_path: str) -> None:
    run([PANDOC, input_path, "-o", output_path])


# -----------------------------
# ARCHIVE OPERATIONS
# -----------------------------
def extract_zip(input_path: str, output_dir: str) -> None:
    run([UNZIP, input_path, "-d", output_dir])


def extract_tar(input_path: str, output_dir: str) -> None:
    run([TAR, "-xf", input_path, "-C", output_dir])


# -----------------------------
# fileforge PACKAGE FALLBACK (subtitles, config/data formats, markup,
# encoding, PDF text extraction, QR/ASCII art, SVG/PDF rasterization, etc.)
# -----------------------------
def _convert_via_fileforge_registry(input_path: str, output_path: str, in_ext: str, out_ext: str) -> bool:
    """Try the src/fileforge registry. Returns True if it handled the
    conversion, False if fileforge isn't installed or has no route at all
    (direct or chained) for this pair — caller should then raise."""
    if not _FILEFORGE_AVAILABLE:
        return False

    src, tgt = in_ext.lstrip("."), out_ext.lstrip(".")

    converter = _fileforge_registry.get(src, tgt)
    if converter is not None and converter.available():
        converter.fn(Path(input_path), Path(output_path))
        return True

    chain = _fileforge_registry.find_path(src, tgt)
    if chain:
        current_input = Path(input_path)
        tmp_dir = Path(output_path).parent
        for i, hop in enumerate(chain):
            is_last = i == len(chain) - 1
            hop_output = Path(output_path) if is_last else tmp_dir / f".hop{i}-{hop.target_ext}.{hop.target_ext}"
            hop.fn(current_input, hop_output)
            current_input = hop_output
        return True

    return False


# -----------------------------
# GENERIC DISPATCHER
# -----------------------------
def convert_generic(input_path: str, output_path: str) -> None:
    """Pick the right conversion routine based on input/output extensions."""
    in_ext = os.path.splitext(input_path)[1].lower()
    out_ext = os.path.splitext(output_path)[1].lower()

    # Special-cased conversions first (format-specific tool choice)
    if in_ext == ".svg" and out_ext == ".png":
        return convert_svg_to_png(input_path, output_path)
    if in_ext == ".heic" and out_ext == ".jpg":
        return convert_heic_to_jpg(input_path, output_path)
    if in_ext in VIDEO_EXTS and out_ext == ".gif":
        return convert_video_to_gif(input_path, output_path)
    if in_ext in VIDEO_EXTS and out_ext in AUDIO_EXTS:
        return extract_audio(input_path, output_path)
    if in_ext in DOC_EXTS and out_ext == ".pdf":
        return convert_doc_to_pdf(input_path, os.path.dirname(output_path))
    if in_ext in {".docx", ".md", ".txt"} and out_ext == ".html":
        return convert_doc_to_html(input_path, output_path)
    if in_ext == ".md" and out_ext == ".pdf":
        return convert_md_to_pdf(input_path, output_path)
    if out_ext == ".unzipped":
        return extract_zip(input_path, os.path.dirname(output_path))
    if out_ext == ".untar":
        return extract_tar(input_path, os.path.dirname(output_path))

    # Try the src/fileforge registry next, before the generic family catches
    # below — it has specific, correct converters for pairs the generic
    # catches would otherwise mishandle (e.g. txt->png is meant to produce a
    # QR code, not have ImageMagick try to render raw text as an image;
    # pdf->png needs a real PDF renderer, not ImageMagick's inconsistent
    # Ghostscript delegate). It also covers pairs the generic catches don't
    # know about at all (subtitles, config/data formats, markup, encoding,
    # PDF text extraction, ASCII art, SVG/PDF rasterization).
    if _convert_via_fileforge_registry(input_path, output_path, in_ext, out_ext):
        return

    # Last-resort generic family conversions: no specific converter exists
    # above (special-cased or via the registry) for this exact pair, but the
    # target is a standard image/video/audio format ImageMagick/ffmpeg can
    # usually produce from a same-family source without needing any extra
    # Python dependency installed.
    if out_ext in IMAGE_EXTS:
        return convert_image(input_path, output_path)
    if out_ext in VIDEO_EXTS:
        return convert_video(input_path, output_path)
    if out_ext in AUDIO_EXTS:
        return convert_audio(input_path, output_path)

    raise ConversionError(f"Unsupported conversion: {input_path} -> {output_path}")
