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

    # General family-based conversions
    if out_ext in IMAGE_EXTS:
        return convert_image(input_path, output_path)
    if out_ext in VIDEO_EXTS:
        return convert_video(input_path, output_path)
    if out_ext in AUDIO_EXTS:
        return convert_audio(input_path, output_path)

    raise ConversionError(f"Unsupported conversion: {input_path} -> {output_path}")
