# FileForge

**A multi-tier file-conversion product ecosystem** — one shared engine powering
a free CLI, a Pro desktop/Android build, a Cloud API, and Enterprise licensing.

![status](https://img.shields.io/badge/status-active-brightgreen)
![python](https://img.shields.io/badge/python-3.9%2B-blue)
![license](https://img.shields.io/badge/license-MIT%20(core)-green)

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

## What's in the box

| Path                | Tier / Strategy                    | What it is                                   |
|---------------------|------------------------------------|----------------------------------------------|
| `src/fileforge/`    | Free CLI + shared engine           | Conversion registry, converters, licensing   |
| `src/fileforge/pro/`| Pro (batch, OCR, PDF, TTS)         | License-gated advanced features              |
| `cloud-api/`        | Strategy 3 & 7 — Cloud API         | FastAPI convert/formats/usage + metering     |
| `desktop/`          | Strategy 6 — Desktop GUI           | Tkinter reference GUI (PyQt/Electron in Pro) |
| `android/`          | Strategy 2 — Android GUI           | Compose + Chaquopy architecture & skeleton   |
| `magisk-module/`    | Strategy 9 — Magisk module         | Flashable system-wide install                |
| `scripts/`          | Fulfillment / packaging            | License issuing, Magisk zip builder          |
| `docs/monetization-plan.md` | Business document          | Full 10-strategy monetization & roadmap      |

## Tiers

| Tier           | Package                                      |
|----------------|----------------------------------------------|
| **Free**       | CLI tool                                     |
| **Pro**        | Advanced features, GUI, automation, cloud    |
| **Enterprise** | Licensing, API access, support, custom builds|

See **[docs/monetization-plan.md](docs/monetization-plan.md)** for the complete
pricing, feature matrix, distribution, marketing, revenue projections, and
six-month execution roadmap.

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
