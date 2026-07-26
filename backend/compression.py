"""compression.py — ffmpeg-based video compression."""

from __future__ import annotations

from engine import run

FFMPEG = "ffmpeg"


def compress_video(input_path: str, output_path: str, preset: str = "medium", crf: int = 23) -> None:
    """Re-encode a video with libx264/aac at a given CRF and preset."""
    run([
        FFMPEG, "-y",
        "-i", input_path,
        "-vcodec", "libx264",
        "-preset", preset,
        "-crf", str(crf),
        "-acodec", "aac",
        output_path,
    ])
