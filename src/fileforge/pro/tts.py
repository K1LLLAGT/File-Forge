"""Document -> audio (Pro tier). Text-to-speech via pyttsx3 (offline) with an
optional cloud voice fallback handled by the Cloud API client."""

from __future__ import annotations

from pathlib import Path

from fileforge.core.registry import ConversionError
from fileforge.licensing import License, Tier, require


def text_to_audio(source: Path, target: Path, *, license: License | None = None) -> Path:
    require(Tier.PRO, license)
    try:
        import pyttsx3  # optional dependency
    except ImportError as exc:  # pragma: no cover
        raise ConversionError(
            "TTS needs pyttsx3 — install with `pip install fileforge[tts]`"
        ) from exc

    text = Path(source).read_text(encoding="utf-8", errors="replace")
    engine = pyttsx3.init()
    engine.save_to_file(text, str(target))
    engine.runAndWait()
    return Path(target)
