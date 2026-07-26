"""thumbnails.py — image and video thumbnail generation."""

from __future__ import annotations

from engine import run

FFMPEG = "ffmpeg"
IMAGEMAGICK = "convert"


def image_thumbnail(input_path: str, output_path: str, size: str = "256x256") -> None:
    run([IMAGEMAGICK, input_path, "-thumbnail", size, output_path])


def video_thumbnail(input_path: str, output_path: str, time: str = "00:00:01") -> None:
    run([FFMPEG, "-y", "-ss", time, "-i", input_path, "-vframes", "1", output_path])
