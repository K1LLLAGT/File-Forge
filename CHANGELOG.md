# Changelog

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
