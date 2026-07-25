# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for FileForge.exe (Windows 11 desktop app).

Build with:  pyinstaller windows/fileforge.spec   (run from repo root)

The converters are imported dynamically at runtime via ``pkgutil`` in
``load_builtin_converters()``, so PyInstaller's static analysis cannot see
them. We therefore collect every ``fileforge`` submodule explicitly.
"""

from PyInstaller.utils.hooks import collect_submodules

# The converters register themselves lazily via pkgutil, so PyInstaller's
# static analysis can't see them — collect them explicitly. Everything else the
# app uses (core.registry, suggestions) is imported statically and picked up by
# normal analysis, so we deliberately scope this to the converters package
# rather than all of ``fileforge`` (which would also drag in optional,
# unrelated modules like licensing).
hiddenimports = collect_submodules("fileforge.converters")

block_cipher = None


a = Analysis(
    ["fileforge_app.py"],
    pathex=["."],                      # windows/ dir (spec is run from here)
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="FileForge",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,                     # GUI app: no console window
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,                         # drop a .ico path here to brand the exe
)
