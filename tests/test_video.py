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


def test_free_tier_list_excludes_video():
    free = registry.routes(tier="free")
    assert all(c.tier == "free" for c in free)
    assert registry.get("mov", "mp4") not in free


def test_unknown_preset_rejected():
    from fileforge.core.registry import ConversionError
    ent = License(Tier.ENTERPRISE, "x", True)
    with pytest.raises(ConversionError):
        video.compress("a.mov", "b.mp4", preset="nope", license=ent)


def test_compress_requires_pro_license():
    free = License(Tier.FREE, "anon", True)
    with pytest.raises(PermissionError):
        video.compress("a.mov", "b.mp4", preset="small", license=free)
