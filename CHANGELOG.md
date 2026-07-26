# Changelog

## Unreleased

- **Chained conversions** — when there's no direct converter, the engine now
  finds a route through intermediate formats (e.g. `md → txt → pdf`,
  `csv → md → txt → pdf`) and runs it automatically. Added
  `Registry.find_path()`; the CLI falls back to it and prints the path taken.
- Added a `fileforge doctor` command — reports which optional packages
  (Pillow, pypdf, ffmpeg, …) are installed and lists exactly which conversion
  routes are usable right now (`--list` for the full per-route breakdown).
- Added converters:
  - Images (Pillow): `jpg→webp`, `jpeg→webp`, `webp→jpg`, `bmp→jpg`,
    `gif→png`, `tiff→png`, `heic→png`, `png→ico`, and image → PDF
    (`png/jpg/jpeg/bmp/gif/tiff/webp → pdf`).
  - Audio (ffmpeg): `wav↔mp3`, `flac→mp3`/`wav`, `wav→flac`, `m4a→mp3`,
    `ogg→mp3`, `mp3→ogg`.
  - Dev/data (pure-Python): `json↔jsonl`, `csv/tsv/json → md` (Markdown
    tables), `csv/json → html` (HTML tables), `ini↔json`, `ini↔toml`,
    `.env↔json`, `har→csv`, `gpx→geojson`, `kml→geojson`.
  - Subtitles (pure-Python): `srt↔vtt`.
  - Graphics: `png/jpg → b64` (data URI), `png→txt` (ASCII art), and the
    dependency-gated `txt→png` (QR code, needs `qrcode`), `svg→png`
    (`cairosvg`), `pdf→png` (`pymupdf`).
  - `pdf→txt` — extract a PDF's embedded text (pypdf).
- New optional extras: `qr`, `svg`, `render`.

## v2.0.0 — Discovery/Suggestion layer, desktop & Android apps

### Discovery & suggestion layer (new)
- Added `fileforge.discovery` — alias normalization (`File Forge`/`File-Forge`/
  `fileforge`/… → canonical `fileforge`) and filesystem instance discovery with
  role identification. CLI: `fileforge-discover`.
- Added `fileforge.suggestions` — directory scan (extension frequency/samples),
  conversion suggestions from real registry routes plus a generic route table,
  and `run_conversions.sh` / `.ps1` driver-script generation. CLI: `fileforge-suggest`.
- Added `fileforge.unified_cli` — merges alias resolution, directory analysis,
  and routes into a personalized conversion matrix + recommendations. CLI:
  `fileforge-cli`.
- New console scripts wired into `pyproject.toml`; docs: `DISCOVERY.md`,
  `CONVERSIONS.md`, `USER_FLOW.md`.

### Windows desktop app
- Added `windows/` — `FileForge.exe`: directory browser, file-type summary,
  ranked conversion-suggestion panel, threaded conversion with progress, and a
  history/logging tab. Tkinter GUI over a headless, unit-tested controller;
  packaged with PyInstaller. Docs: `windows/WINDOWS_SETUP.md`.

### Android app (re-branded)
- Added `android2/` — `com.fileforge2.app`: Compose Convert + History tabs,
  suggestion-ranked target picker, and persisted conversion history. Bridge
  extended with `ranked_targets` / `suggest_dir`. Docs: `android2/ANDROID_SETUP.md`.
- Retired the original `android/` app (`com.k1lllagt.fileforge`).

### Setup, CI & release tooling
- Added `bootstrap.sh` (OS detection + subsystem verification) and `setup/`
  scripts for Linux/Windows/Android; docs: `BOOTSTRAP.md`.
- Added GitHub Actions workflows to build `FileForge.exe` (windows-latest) and
  the Android APK (ubuntu + JDK 17 + Android SDK 34 + Chaquopy, embedding a
  locally-built engine wheel), plus a `release-binaries` workflow that attaches
  both binaries to the GitHub Release.

### Maintenance
- Added tests for the discovery/suggestion layer and the Windows controller.
- Removed committed release-artifact zips and one-off migration scripts.

## v1.0.0 — Initial Public Release
- Added config, encoding, and markup converters
- Expanded data converter with streaming + normalization
- Introduced cloud-api/app/api.py (FastAPI routing + metering hooks)
- Updated CLI with new commands and pipeline chaining
- Updated pyproject.toml with new dependencies and entry points
