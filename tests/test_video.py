import pytest

from fileforge.core.registry import load_builtin_converters, registry
from fileforge.licensing import License, Tier
from fileforge.pro import video


@pytest.fixture(autouse=True, scope="module")
def _load():
    load_builtin_converters()


def test_presets_exist():
    for name in ("small", "balanced", "web-720p", "web-1080p", "gif", "audio-only"):
        assert name in video.PRESETS


def test_build_command_is_well_formed():
    cmd = video.build_command("in.mov", "out.mp4", video.PRESETS["web-720p"])
    assert cmd[0] == "ffmpeg"
    assert "-i" in cmd and "in.mov" in cmd and "out.mp4" in cmd
    assert "libx264" in cmd
    assert cmd.index("in.mov") < cmd.index("out.mp4")  # input before output


def test_video_routes_are_pro_tier():
    conv = registry.get("mov", "mp4")
    assert conv is not None
    assert conv.tier == "pro"


def test_video_routes_still_tagged_pro_in_registry():
    # The tier tag is retained (dormant) even though nothing is gated anymore.
    assert registry.get("mov", "mp4").tier == "pro"


def test_unknown_preset_rejected():
    from fileforge.core.registry import ConversionError
    free = License(Tier.FREE, "x", True)
    with pytest.raises(ConversionError):
        video.compress("a.mov", "b.mp4", preset="nope", license=free)


def test_compress_allowed_on_free_tier():
    # FileForge is free: no license is required. With a valid preset the only
    # thing that can stop the conversion is a missing ffmpeg binary, never a
    # license — so we must NOT get a PermissionError.
    from fileforge.core.registry import ConversionError
    free = License(Tier.FREE, "anon", True)
    try:
        video.compress("a.mov", "b.mp4", preset="small", license=free)
    except PermissionError:
        raise AssertionError("free tier should not be blocked")
    except (ConversionError, Exception):
        pass  # ffmpeg missing / no such file is fine; gating is what we test
