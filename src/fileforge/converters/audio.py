"""Audio transcoding (Pro tier).

Shells out to the ``ffmpeg`` binary — the same approach as ``video.py`` — so
there is no Python audio dependency at runtime. Each target format maps to a
tuned set of ffmpeg codec args.

    from fileforge.converters.audio import convert_audio
    convert_audio("track.wav", "track.mp3")

If ffmpeg is not on PATH a clear ConversionError explains how to install it.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Dict, List

from fileforge.core.registry import ConversionError, registry
from fileforge.licensing import License, Tier, require

# Target extension -> ffmpeg codec/quality args.
_TARGET_ARGS: Dict[str, List[str]] = {
    "mp3": ["-acodec", "libmp3lame", "-q:a", "2"],
    "wav": ["-acodec", "pcm_s16le"],
    "flac": ["-acodec", "flac"],
    "ogg": ["-acodec", "libvorbis", "-q:a", "5"],
    "m4a": ["-acodec", "aac", "-b:a", "192k"],
}

# Source -> target routes advertised in the registry (`fileforge list`).
_ROUTES = [
    ("wav", "mp3"),
    ("mp3", "wav"),
    ("flac", "mp3"),
    ("wav", "flac"),
    ("flac", "wav"),
    ("m4a", "mp3"),
    ("ogg", "mp3"),
    ("mp3", "ogg"),
]


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def build_command(source: Path, target: Path, overwrite: bool = True) -> List[str]:
    """The exact ffmpeg argv a conversion would run (also used by tests)."""
    tgt_ext = Path(target).suffix.lower().lstrip(".")
    if tgt_ext not in _TARGET_ARGS:
        raise ConversionError(
            f"unsupported audio target '.{tgt_ext}'. "
            f"Choose from: {', '.join(sorted(_TARGET_ARGS))}"
        )
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error"]
    cmd += ["-y"] if overwrite else ["-n"]
    # -vn drops any cover-art/video stream so we get audio only.
    cmd += ["-i", str(source), "-vn", *_TARGET_ARGS[tgt_ext], str(target)]
    return cmd


def convert_audio(
    source: str | Path,
    target: str | Path,
    *,
    license: License | None = None,
) -> Path:
    require(Tier.PRO, license)
    if not ffmpeg_available():
        raise ConversionError(
            "audio conversion needs the ffmpeg binary on PATH — "
            "install it (e.g. `apt install ffmpeg`, `brew install ffmpeg`, "
            "`pkg install ffmpeg`)"
        )
    source, target = Path(source), Path(target)
    cmd = build_command(source, target)
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise ConversionError(f"ffmpeg failed: {proc.stderr.strip() or proc.returncode}")
    return target


def _register_routes() -> None:
    def _fn(src: Path, dst: Path, **opts):
        return convert_audio(src, dst)

    for src, tgt in _ROUTES:
        registry.add(
            src, tgt, tier="pro",
            description=f"{src.upper()} -> {tgt.upper()} audio (ffmpeg)",
        )(_fn)


_register_routes()
