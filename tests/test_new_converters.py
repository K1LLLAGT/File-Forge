"""Tests for the added converters (image routes, audio, pdf->txt) and the
`fileforge doctor` command."""

import pytest

from fileforge.core.registry import ConversionError, load_builtin_converters, registry
from fileforge.converters import audio


@pytest.fixture(autouse=True, scope="module")
def _load():
    load_builtin_converters()


# --------------------------------------------------------------------------- #
# New image routes (Pillow is a test dependency via the [images] extra)
# --------------------------------------------------------------------------- #

pytest.importorskip("PIL")


@pytest.mark.parametrize(
    "src_ext,tgt_ext",
    [("png", "webp"), ("png", "ico"), ("jpg", "webp"), ("webp", "jpg"),
     ("gif", "png"), ("bmp", "jpg"), ("tiff", "png")],
)
def test_new_image_routes_registered(src_ext, tgt_ext):
    conv = registry.get(src_ext, tgt_ext)
    assert conv is not None
    assert conv.requires == ("PIL",)


def _make_image(path, mode="RGBA", size=(24, 24)):
    from PIL import Image

    Image.new(mode, size, 0).save(path)


def test_png_to_webp_and_ico_produce_files(tmp_path):
    src = tmp_path / "a.png"
    _make_image(src)
    for tgt_ext in ("webp", "ico", "jpg"):
        dst = tmp_path / f"a.{tgt_ext}"
        registry.get("png", tgt_ext).fn(src, dst)
        assert dst.exists() and dst.stat().st_size > 0


def test_gif_to_png_roundtrip(tmp_path):
    src = tmp_path / "a.gif"
    _make_image(src, mode="P", size=(16, 16))
    dst = tmp_path / "a.png"
    registry.get("gif", "png").fn(src, dst)
    from PIL import Image

    assert Image.open(dst).format == "PNG"


# --------------------------------------------------------------------------- #
# Audio (ffmpeg) — command building + registration, no ffmpeg needed
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "src_ext,tgt_ext",
    [("wav", "mp3"), ("mp3", "wav"), ("flac", "mp3"), ("mp3", "ogg"),
     ("m4a", "mp3"), ("ogg", "mp3")],
)
def test_audio_routes_registered_pro(src_ext, tgt_ext):
    conv = registry.get(src_ext, tgt_ext)
    assert conv is not None
    assert conv.tier == "pro"
    assert "ffmpeg" in conv.description.lower()


def test_audio_build_command_well_formed():
    cmd = audio.build_command("in.wav", "out.mp3")
    assert cmd[0] == "ffmpeg"
    assert "-i" in cmd and "in.wav" in cmd and "out.mp3" in cmd
    assert "libmp3lame" in cmd
    assert cmd.index("in.wav") < cmd.index("out.mp3")  # input before output


def test_audio_unsupported_target_rejected():
    with pytest.raises(ConversionError):
        audio.build_command("in.wav", "out.xyz")


def test_audio_conversion_not_license_gated():
    # FileForge is free: a missing ffmpeg binary is the only expected failure,
    # never a PermissionError.
    from fileforge.licensing import License, Tier

    free = License(Tier.FREE, "anon", True)
    try:
        audio.convert_audio("a.wav", "b.mp3", license=free)
    except PermissionError:
        raise AssertionError("free tier should not be blocked")
    except ConversionError:
        pass  # ffmpeg missing is fine — that's what we tolerate


# --------------------------------------------------------------------------- #
# PDF -> text
# --------------------------------------------------------------------------- #


def test_pdf_to_txt_route_registered():
    conv = registry.get("pdf", "txt")
    assert conv is not None
    assert conv.requires == ("pypdf",)
    assert conv.tier == "free"


def test_pdf_to_txt_extract_signature():
    # Real extraction needs a working pypdf (and its cryptography backend),
    # which not every environment provides; here we assert the callable is
    # wired to the route. The extraction path itself is exercised end-to-end
    # in environments where pypdf imports cleanly.
    from fileforge.converters import pdf

    assert registry.get("pdf", "txt").fn is pdf.extract_text


# --------------------------------------------------------------------------- #
# doctor command
# --------------------------------------------------------------------------- #


def test_doctor_runs(capsys):
    # doctor loads converters itself; drive the handler with a Namespace.
    import fileforge.cli as cli

    cli.load_builtin_converters()
    ns = cli.argparse.Namespace(list=False)
    rc = cli._do_doctor(ns)
    out = capsys.readouterr().out
    assert rc == 0
    assert "doctor" in out
    assert "conversions:" in out
    assert "ffmpeg" in out


def test_doctor_list_shows_routes(capsys):
    import fileforge.cli as cli

    ns = cli.argparse.Namespace(list=True)
    cli._do_doctor(ns)
    out = capsys.readouterr().out
    assert "->" in out  # route arrows in the listing
