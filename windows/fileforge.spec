# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for FileForge.exe (Windows 11 desktop app).

Build with:  pyinstaller windows/fileforge.spec   (run from repo root)

The converters are imported dynamically at runtime via ``pkgutil`` in
``load_builtin_converters()``, so PyInstaller's static analysis cannot see
them. We therefore collect every ``fileforge`` submodule explicitly.
"""

from PyInstaller.utils.hooks import collect_submodules

# Pull in fileforge.converters.* (registered lazily) and the 2.0 layer modules.
hiddenimports = collect_submodules("fileforge")

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
