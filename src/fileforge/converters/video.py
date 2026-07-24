"""Video compression + transcoding presets (Pro tier).

Shells out to the ``ffmpeg`` binary (no Python wrapper needed at runtime),
which is how the plan's "video compression presets" feature ships. Each preset
is a named, tuned set of ffmpeg args so users pick an outcome ("small",
"web-720p") instead of memorising codecs.

    from fileforge.converters.video import compress, PRESETS
    compress("in.mov", "out.mp4", preset="web-720p")

If ffmpeg is not on PATH a clear ConversionError explains how to install it.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from fileforge.core.registry import ConversionError, registry
from fileforge.licensing import License, Tier, require


@dataclass(frozen=True)
class VideoPreset:
    name: str
    description: str
    args: List[str]          # ffmpeg args inserted between input and output
    container: str = "mp4"   # default output extension


# Tuned presets. CRF-based x264 for predictable quality/size trade-offs.
PRESETS: Dict[str, VideoPreset] = {
    "small": VideoPreset(
        "small", "Aggressive size reduction (CRF 30, 480p cap)",
        ["-vcodec", "libx264", "-crf", "30", "-preset", "slow",
         "-vf", "scale='min(854,iw)':-2", "-acodec", "aac", "-b:a", "96k"],
    ),
    "balanced": VideoPreset(
        "balanced", "Good quality at a smaller size (CRF 26, 720p cap)",
        ["-vcodec", "libx264", "-crf", "26", "-preset", "medium",
         "-vf", "scale='min(1280,iw)':-2", "-acodec", "aac", "-b:a", "128k"],
    ),
    "web-720p": VideoPreset(
        "web-720p", "Web-optimized 720p, fast-start MP4 (CRF 23)",
        ["-vcodec", "libx264", "-crf", "23", "-preset", "medium",
         "-vf", "scale=-2:720", "-movflags", "+faststart",
         "-acodec", "aac", "-b:a", "128k"],
    ),
    "web-1080p": VideoPreset(
        "web-1080p", "Web-optimized 1080p, fast-start MP4 (CRF 22)",
        ["-vcodec", "libx264", "-crf", "22", "-preset", "medium",
         "-vf", "scale=-2:1080", "-movflags", "+faststart",
         "-acodec", "aac", "-b:a", "160k"],
    ),
    "gif": VideoPreset(
        "gif", "Convert a short clip to an optimized GIF",
        ["-vf", "fps=12,scale=480:-1:flags=lanczos"], container="gif",
    ),
    "audio-only": VideoPreset(
        "audio-only", "Strip video, export MP3 audio",
        ["-vn", "-acodec", "libmp3lame", "-q:a", "2"], container="mp3",
    ),
}


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def build_command(source: Path, target: Path, preset: VideoPreset,
                  overwrite: bool = True) -> List[str]:
    """The exact ffmpeg argv this preset would run (also used by tests)."""
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error"]
    cmd += ["-y"] if overwrite else ["-n"]
    cmd += ["-i", str(source), *preset.args, str(target)]
    return cmd


def compress(
    source: str | Path,
    target: str | Path,
    *,
    preset: str = "balanced",
    license: License | None = None,
) -> Path:
    require(Tier.PRO, license)
    if preset not in PRESETS:
        raise ConversionError(
            f"unknown preset '{preset}'. Choose from: {', '.join(PRESETS)}"
        )
    if not ffmpeg_available():
        raise ConversionError(
            "video presets need the ffmpeg binary on PATH — "
            "install it (e.g. `pkg install ffmpeg`, `apt install ffmpeg`, "
            "`brew install ffmpeg`)"
        )
    source, target = Path(source), Path(target)
    cmd = build_command(source, target, PRESETS[preset])
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise ConversionError(f"ffmpeg failed: {proc.stderr.strip() or proc.returncode}")
    return target


def _register_routes() -> None:
    """Expose common video routes in the registry so `fileforge list` shows
    them (tier=pro). The engine dispatches these through ``compress``."""
    def _make(preset_name: str):
        def _fn(src: Path, dst: Path, **opts):
            return compress(src, dst, preset=opts.get("preset", preset_name))
        return _fn

    for src in ("mov", "mkv", "avi", "webm", "mp4"):
        registry.add(src, "mp4", tier="pro",
                     description="Video compress/transcode (ffmpeg)",
                     requires=())(_make("balanced"))
    registry.add("mp4", "gif", tier="pro",
                 description="Video -> optimized GIF (ffmpeg)")(_make("gif"))
    registry.add("mp4", "mp3", tier="pro",
                 description="Video -> MP3 audio (ffmpeg)")(_make("audio-only"))


_register_routes()
