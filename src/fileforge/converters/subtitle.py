"""Subtitle converters: SRT ⇄ WebVTT. Pure standard library.

SRT uses ``,`` as the millisecond separator and numeric cue indices; WebVTT
uses ``.`` and a ``WEBVTT`` header. The cue text itself is carried across
unchanged.
"""

from __future__ import annotations

import re
from pathlib import Path

from fileforge.core.registry import registry

# Matches a timestamp like 00:01:02,500 (SRT) or 00:01:02.500 (VTT).
_TS = re.compile(r"(\d{2}:\d{2}:\d{2})[,.](\d{3})")


def _blocks(text: str):
    """Yield subtitle blocks (lists of lines) split on blank lines."""
    block: list[str] = []
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if line.strip() == "":
            if block:
                yield block
                block = []
        else:
            block.append(line)
    if block:
        yield block


@registry.add("srt", "vtt", description="SubRip (SRT) -> WebVTT")
def srt_to_vtt(source: Path, target: Path, **_) -> Path:
    text = Path(source).read_text(encoding="utf-8-sig")
    out = ["WEBVTT", ""]
    for block in _blocks(text):
        # Drop a leading numeric index line if present.
        if block and block[0].strip().isdigit():
            block = block[1:]
        if not block:
            continue
        block[0] = _TS.sub(lambda m: f"{m.group(1)}.{m.group(2)}", block[0])
        out.extend(block)
        out.append("")
    Path(target).write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")
    return target


@registry.add("vtt", "srt", description="WebVTT -> SubRip (SRT)")
def vtt_to_srt(source: Path, target: Path, **_) -> Path:
    text = Path(source).read_text(encoding="utf-8-sig")
    out: list[str] = []
    index = 1
    for block in _blocks(text):
        # Skip the WEBVTT header and any NOTE/STYLE/REGION blocks.
        if block[0].strip().upper().startswith(("WEBVTT", "NOTE", "STYLE", "REGION")):
            continue
        # A VTT cue may start with an optional identifier line before the
        # timing line; find the line that contains a timestamp.
        ts_idx = next((i for i, ln in enumerate(block) if "-->" in ln), None)
        if ts_idx is None:
            continue
        timing = _TS.sub(lambda m: f"{m.group(1)},{m.group(2)}", block[ts_idx])
        cue_text = block[ts_idx + 1:]
        out.append(str(index))
        out.append(timing)
        out.extend(cue_text)
        out.append("")
        index += 1
    Path(target).write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")
    return target
