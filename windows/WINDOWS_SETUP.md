# FileForge for Windows 11 — `FileForge.exe`

A native-feeling desktop app built on Python + Tkinter and packaged into a
single `FileForge.exe` with PyInstaller. It sits **on top of the FileForge 2.0
discovery/suggestion layer** — the same engine the CLI uses.

- App entry point: [`windows/fileforge_app.py`](fileforge_app.py) (Tkinter view)
- Logic/controller: [`windows/fileforge_core.py`](fileforge_core.py) (no Tk; unit-tested)
- PyInstaller spec: [`windows/fileforge.spec`](fileforge.spec)
- Scripts: [`setup_windows.ps1`](setup_windows.ps1), [`build_windows.ps1`](build_windows.ps1)

## Why this stack

Python + Tkinter + PyInstaller keeps the desktop app on the **exact same engine
code** as the CLI and Android bridge — one converter registry, one suggestion
engine, no reimplementation. Tkinter ships with CPython, so there is no GUI
toolkit to install, and PyInstaller yields a single self-contained `.exe` with
no Python prerequisite on the target machine.

## Features

| Feature | Where |
|---------|-------|
| Directory browser | "Choose folder…" toolbar button |
| File-type summary | left panel of the **Convert** tab (extension → count) |
| Conversion-suggestion panel | right panel — ranked, engine-aware (generic routes greyed out) |
| Conversion execution + progress | select a suggestion → **Convert** → progress bar (runs off the UI thread) |
| History / logging | **History** tab, backed by a rolling JSONL log |

The history log lives at `%LOCALAPPDATA%\FileForge\history.jsonl`
(`~/.fileforge/history.jsonl` on non-Windows).

## Run from source

```powershell
./windows/setup_windows.ps1        # .venv + engine + PyInstaller
python windows/fileforge_app.py    # launch the GUI
```

## Build the exe

```powershell
./windows/build_windows.ps1
# -> windows/dist/FileForge.exe
```

`build_windows.ps1` activates the repo `.venv` (if present), ensures the engine
and PyInstaller are installed, then runs `pyinstaller windows/fileforge.spec`.

### Notes on packaging

- The converters register themselves lazily via `pkgutil`, so PyInstaller's
  static analysis can't see them. The spec uses
  `collect_submodules("fileforge")` to bundle every submodule — **do not remove
  that** or on-device conversions will fail with "no converter for …".
- Optional accelerators (Pillow for images, pypdf for PDF) are installed by the
  setup script via the `[images,pdf]` extras and are picked up automatically.
  To brand the exe, set an `icon="path\\to\\app.ico"` in `fileforge.spec`.
- Building a Windows exe must be done **on Windows** — PyInstaller is not a
  cross-compiler.

## Verify without a display

The controller is decoupled from Tkinter and is covered by
`tests/test_windows_app.py`, so its scan → suggest → convert → history flow can
be tested headless (Linux/CI) even though the GUI itself needs a desktop
session.
