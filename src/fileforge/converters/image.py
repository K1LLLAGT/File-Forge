"""Image converters. These require Pillow. When Pillow is not installed the
routes still register but ``Converter.available()`` reports False, so the CLI
can tell the user exactly which optional dependency to add.
"""

from __future__ import annotations

from pathlib import Path

from fileforge.core.registry import ConversionError, registry

# (source, target) pairs Pillow handles losslessly enough for the free tier.
_IMAGE_ROUTES = [
    ("png", "jpg"),
    ("jpg", "png"),
    ("jpeg", "png"),
    ("png", "webp"),
    ("webp", "png"),
    ("png", "bmp"),
    ("bmp", "png"),
    ("png", "gif"),
    ("png", "tiff"),
    ("heic", "jpg"),
]


def _convert_image(source: Path, target: Path, **options) -> Path:
    try:
        from PIL import Image  # optional dependency
    except ImportError as exc:  # pragma: no cover - depends on env
        raise ConversionError(
            "image conversion needs Pillow — install with `pip install fileforge[images]`"
        ) from exc

    img = Image.open(source)
    target_ext = target.suffix.lower().lstrip(".")
    if target_ext in {"jpg", "jpeg", "bmp"} and img.mode in {"RGBA", "P", "LA"}:
        img = img.convert("RGB")
    save_kwargs = {}
    if target_ext in {"jpg", "jpeg"}:
        save_kwargs["quality"] = int(options.get("quality", 90))
    img.save(target, **save_kwargs)
    return target


def _register() -> None:
    for src, tgt in _IMAGE_ROUTES:
        registry.add(
            src, tgt,
            description=f"{src.upper()} -> {tgt.upper()} (Pillow)",
            requires=["PIL"],
        )(_convert_image)


_register()
