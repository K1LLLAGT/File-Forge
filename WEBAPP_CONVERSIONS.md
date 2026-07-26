# Web Dashboard — Compatible Conversions

Every conversion the web dashboard (`backend/`, `app/`) can actually perform
right now, generated from the real dispatch logic in `engine.py` — not a
hand-maintained list that can drift out of sync with the code. Check the
live version anytime with `curl http://127.0.0.1:8091/formats`, or ask the
doctor script (`./scripts/fileforge-doctor.sh`) whether the tools behind
these routes are actually installed.

This is the **web dashboard's** conversion list. The separate CLI/apps
product (`src/fileforge`, `fileforge convert ...`) has its own, overlapping
but not identical list — see the root [CONVERSIONS.md](CONVERSIONS.md) for
that one.

## How a conversion gets picked

`engine.py` tries three tiers, in order, and stops at the first one that
can handle the pair:

1. **A handful of guaranteed special cases** — svg→png, heic→jpg,
   video→gif, video→any-audio-format, office-doc→pdf, {docx,md,txt}→html,
   md→pdf, zip/tar extraction. These never depend on the optional
   `src/fileforge` package being installed.
2. **The `src/fileforge` registry fallback**, if installed — a much larger
   set of specific converters (subtitles, config/data formats, markup,
   encoding, PDF text extraction, and more), including **chained**
   conversions when no single converter exists (e.g. `ini → yaml` actually
   runs `ini → json → yaml` automatically).
3. **Generic ImageMagick/ffmpeg fallback** — if neither of the above knows
   the pair but the target is a standard image/video/audio format, this
   just tries the obvious tool. Last resort, no extra dependency needed.

## Tier 1 — always available, no optional package needed

| From | To | Tool |
|---|---|---|
| any video | gif | ffmpeg |
| any video | any audio format | ffmpeg (`-vn`, extract audio track) |
| svg | png | ImageMagick |
| heic | jpg | ImageMagick |
| docx / pptx / xlsx / doc / ppt / xls | pdf | LibreOffice (via proot Ubuntu) |
| docx / md / txt | html | Pandoc |
| md | pdf | Pandoc |
| zip | (extracted) | unzip |
| tar | (extracted) | tar |
| any image | png / jpg / jpeg / webp / gif / bmp / tiff | ImageMagick |
| any video | mp4 / mkv / mov / avi / webm | ffmpeg |
| any audio | mp3 / wav / flac / aac / ogg / m4a | ffmpeg |

## Tier 2 — via the `src/fileforge` registry fallback

Requires `pip install -e ".[yaml,markdown,xml,toml,xlsx,pdf]"` (see
`scripts/install_conversion_tools.sh`, which does this automatically).

**Images (extra pairs)**

| From | To | Notes |
|---|---|---|
| bmp | jpg, png, pdf | Pillow |
| gif | png, pdf | Pillow |
| heic | png | Pillow |
| jpeg / jpg | png, webp, pdf, base64 | Pillow |
| png | bmp, gif, ico, jpg, tiff, webp, pdf, base64 | Pillow |
| tiff | png, pdf | Pillow |
| webp | jpg, png, pdf, base64 | Pillow |

**Video/Audio (extra pairs)**

| From | To | Notes |
|---|---|---|
| avi, mkv, mov, webm, mp4 | mp4 | ffmpeg, "balanced" CRF preset (compress/transcode in place) |
| flac | mp3, wav | ffmpeg |
| m4a | mp3 | ffmpeg |
| mp3 | ogg, wav | ffmpeg |
| ogg | mp3 | ffmpeg |
| wav | flac, mp3 | ffmpeg |

**Documents & PDF**

| From | To | Notes |
|---|---|---|
| txt | pdf | Pure-Python PDF writer, zero dependencies |
| pdf | txt | Text extraction, via pypdf |
| pdf | png | First-page render, via pymupdf — **native C++ build, uncertain on Termux ARM64; failed on this project's test device without a working `libiconv`+cmake+swig chain.** Not blocking anything else. |
| png | txt | ASCII art (not OCR — see "Not available" below) |

**Subtitles**

| From | To |
|---|---|
| srt | vtt |
| vtt | srt |

**Config & structured data** — json, yaml, toml, xml, csv, tsv, xlsx, ini,
env, jsonl freely interconvert where it makes sense:

| From | To |
|---|---|
| csv | html, md, tsv, xlsx, json |
| ini | json, toml |
| json | ini, toml, xml, yaml, jsonl, csv, html, md, tsv, xlsx, env |
| jsonl | json |
| toml | ini, yaml, json |
| tsv | csv, md, xlsx, json |
| xlsx | csv, tsv, yaml, json |
| xml | json |
| yaml | toml, json, xlsx |
| env | json |

**Markup**

| From | To |
|---|---|
| html | txt, md |
| markdown / md | html, txt |

**Encoding**

| From | To |
|---|---|
| txt | base64 |
| base64 | txt |

**Geo & dev-data**

| From | To |
|---|---|
| gpx | geojson |
| kml | geojson |
| har (browser network log) | csv |

**Fun / graphics**

| From | To |
|---|---|
| txt (a URL or short text) | png (QR code) |

## Chained conversions (automatic)

If no single converter exists for a pair, the registry looks for a path
through intermediate formats (up to 3 hops) and runs each step
automatically. Example actually tested: `ini → yaml` has no direct
converter, so it silently runs `ini → json → yaml`.

## Not available (and why)

- **OCR** (image → real text extraction) — `tesseract` is installed by
  `install_conversion_tools.sh`, but **not wired into a route**: `png→txt`
  is already claimed by ASCII art above, and the current `/convert` API
  (a single target-extension string) has no way to say "OCR this, not
  ASCII art." Needs a dedicated `/ocr/image` endpoint.
- **Text-to-speech** — untested on Termux; `pyttsx3` has no known working
  backend on Android (no espeak/SAPI/NSSpeech equivalent). Not attempted
  without real-device verification first.
- **PDF merge / split** — takes multiple files in or produces multiple
  files out, which doesn't fit the current single-file `/convert` shape.
  Needs a dedicated endpoint, not a `(source_ext, target_ext)` route.
