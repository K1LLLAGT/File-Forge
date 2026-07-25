# FileForge

**A multi-tier file-conversion product ecosystem** — one shared engine powering
a free CLI, a Pro desktop/Android build, a Cloud API, and Enterprise licensing.

![status](https://img.shields.io/badge/status-active-brightgreen)
![python](https://img.shields.io/badge/python-3.9%2B-blue)
![license](https://img.shields.io/badge/license-MIT%20(core)-green)
![PyPI](https://img.shields.io/pypi/v/pyfile-convert)

> The free CLI is fully functional and MIT-licensed. Pro / Cloud / Enterprise
> features unlock over the **same engine** with a license key.

---

## Quick start (free CLI)

```bash
pip install -e .            # or: pip install pyfile-convert  (once published; import/command stay `fileforge`)
fileforge list             # show conversions available to your tier
fileforge convert notes.md notes.html
fileforge convert data.json data.csv
fileforge convert report.txt report.pdf     # pure-Python PDF, no deps
```

Optional accelerators:

```bash
pip install -e '.[images]'   # PNG/JPG/WEBP/... via Pillow
pip install -e '.[pdf]'      # PDF merge/split (Pro)
pip install -e '.[ocr]'      # Tesseract OCR (Pro)
pip install -e '.[cloud]'    # run the Cloud API locally
```

## Download the apps

Prebuilt binaries are attached to the latest release
([**releases/latest**](https://github.com/K1LLLAGT/File-Forge/releases/latest)):

| Platform | Download | Notes |
|----------|----------|-------|
| **Windows 11** | [FileForge.exe](https://github.com/K1LLLAGT/File-Forge/releases/download/v2.0.0/FileForge-v2.0.0.exe) | Standalone desktop app (folder browser, ranked suggestions, progress, history). No Python required. |
| **Android** | [FileForge2 APK](https://github.com/K1LLLAGT/File-Forge/releases/download/v2.0.0/FileForge2-v2.0.0-debug.apk) | `com.fileforge2.app`. **Debug** build (unsigned) — enable "install from unknown sources" to sideload. |

Both are built in CI on their native toolchains and bundle the same conversion
engine as the CLI. See the [v2.0.0 release notes](https://github.com/K1LLLAGT/File-Forge/releases/tag/v2.0.0)
for the full changelog.

## What's in the box

| Path                | Tier / Strategy                    | What it is                                   |
|---------------------|------------------------------------|----------------------------------------------|
| `src/fileforge/`    | Free CLI + shared engine           | Conversion registry, converters, licensing   |
| `src/fileforge/pro/`| Pro (batch, OCR, PDF, TTS)         | License-gated advanced features              |
| `cloud-api/`        | Strategy 3 & 7 — Cloud API         | FastAPI convert/formats/usage + metering     |
| `desktop/`          | Strategy 6 — Desktop GUI           | Tkinter reference GUI (PyQt/Electron in Pro) |
| `windows/`          | FileForge 2.0 — Windows app        | PyInstaller `FileForge.exe` (browser + suggestions + history) |
| `android2/`         | Strategy 2 — Android GUI           | `com.fileforge2.app` — Compose + Chaquopy (ranked targets + history) |
| `magisk-module/`    | Strategy 9 — Magisk module         | Flashable system-wide install                |
| `scripts/`          | Fulfillment / packaging            | License issuing, Magisk zip builder          |

## FileForge 2.0 — discovery & suggestion layer

Three extra CLIs sit *on top of* the conversion engine to help you find
FileForge checkouts and figure out what to convert:

```bash
fileforge-discover                 # find & normalize FileForge instances on disk
fileforge-suggest ./assets         # scan a directory, suggest conversions
fileforge-cli --dir . --discover   # unified report: aliases + matrix + recommendations
```

`fileforge-suggest --emit-scripts ./out --source png --target jpg` writes
`run_conversions.sh` / `run_conversions.ps1` that drive `fileforge convert`.
Docs: [DISCOVERY.md](DISCOVERY.md), [CONVERSIONS.md](CONVERSIONS.md),
[USER_FLOW.md](USER_FLOW.md). One-shot setup: `./bootstrap.sh`
([BOOTSTRAP.md](BOOTSTRAP.md)).

Two apps are built on this layer: a Windows desktop app packaged as
`FileForge.exe` ([windows/](windows/), [WINDOWS_SETUP.md](windows/WINDOWS_SETUP.md))
and a re-branded Android build `com.fileforge2.app`
([android2/](android2/), [ANDROID_SETUP.md](android2/ANDROID_SETUP.md)).

## Tiers

| Tier           | Package                                      |
|----------------|----------------------------------------------|
| **Free**       | CLI tool                                     |
| **Pro**        | Advanced features, GUI, automation, cloud    |
| **Enterprise** | Licensing, API access, support, custom builds|


## Everything is free

FileForge is **completely free** — every feature (batch, parallel processing,
OCR, PDF merge/split, video presets, TTS) is available to everyone with no
license required:

```bash
fileforge batch ./images png jpg --recursive --workers 8
fileforge video clip.mov out.mp4 --preset web-720p
```

The Ed25519 licensing system and the license server are **kept in the repo but
dormant** — `licensing.require()` is a no-op, so nothing is gated. If you ever
want to reintroduce paid tiers, restore the tier check in
`src/fileforge/licensing.py` (the original code is preserved in a comment there)
and re-enable the `license-server/`.

## Run the Cloud API locally

```bash
pip install -e '.[cloud]'
cd cloud-api && uvicorn app.main:app --reload
# POST a file:
curl -s -H 'X-API-Key: demo-lifetime' \
     -F file=@notes.md 'http://127.0.0.1:8000/v1/convert?target=html' -o out.html
```

## Development

```bash
pip install -e '.[dev]'
pytest -q
```

## License

Core engine and CLI: **MIT** (see `LICENSE`). Pro/Cloud/Enterprise builds and
assets are commercial; see the monetization plan.
