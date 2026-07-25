# Conversion Suggestion Engine

Scans a directory, tallies file extensions, and proposes conversions drawn from
two sources: the **real engine routes** registered in
[`fileforge.core.registry`](src/fileforge/core/registry.py), and a curated set
of **generic** conversions people commonly want. It can also emit runnable
driver scripts.

- Library: [`src/fileforge/suggestions.py`](src/fileforge/suggestions.py)
- CLI: `fileforge-suggest`

## How suggestions are produced

1. **Scan** — `scan_directory(path, recursive=False)` builds two maps:
   `extension → frequency` and `extension → sample files` (up to 3 samples),
   skipping noise directories and extension-less files.
2. **Suggest** — `suggest(scan)` produces, for each extension found:
   - every engine route `registry.targets_for(ext)` — `supported = True`,
     carrying the engine's real `tier` and `description`;
   - then generic routes from `GENERIC_ROUTES` that the engine can't yet do —
     `supported = False`, `tier = "generic"`.

Results are ranked **supported-first**, then by how many files each route would
touch. Pass `include_generic=False` (CLI: `--no-generic`) to show only
conversions FileForge can actually perform.

## Generic route table

`GENERIC_ROUTES` covers the everyday cases regardless of what the engine
registers — for example:

| Source | Common targets            |
|--------|---------------------------|
| `png`  | `jpg`, `webp`, `gif`, `pdf` |
| `mp4`  | `gif`, `mp3`, `webm`      |
| `docx` | `pdf`, `txt`, `md`        |
| `csv`  | `json`, `xlsx`, `tsv`     |
| `md`   | `html`, `pdf`, `txt`      |

Generic routes are always clearly flagged (`[generic — no engine route]`) so
they are never mistaken for something the engine can run today.

## CLI usage

```bash
fileforge-suggest                      # scan the current directory
fileforge-suggest ./assets --recursive # walk subdirectories
fileforge-suggest . --no-generic       # only engine-supported routes
fileforge-suggest . --json             # machine-readable output
```

### Interactive mode

```bash
fileforge-suggest . --interactive
# prints the extension summary + suggestions, then asks:
#   source extension to convert (e.g. png): png
#   target extension (e.g. jpg):            jpg
# and prints the concrete file-by-file plan.
```

### Emitting driver scripts

Turn a chosen route into runnable scripts that call `fileforge convert` once
per file:

```bash
# non-interactive: pick the route explicitly
fileforge-suggest ./assets --source png --target jpg --emit-scripts ./out

# writes:
#   ./out/run_conversions.sh    (POSIX; chmod +x)
#   ./out/run_conversions.ps1   (Windows PowerShell)
```

Both scripts honour a `FILEFORGE` environment variable so you can point them at
a specific binary (e.g. the PyInstaller build), and generic/unsupported routes
are annotated with a `# NOTE:` line rather than silently failing.

Example `run_conversions.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
FILEFORGE="${FILEFORGE:-fileforge}"

echo "converting assets/a.png -> assets/a.jpg"
"$FILEFORGE" convert assets/a.png assets/a.jpg
```

## Programmatic use

```python
from fileforge.suggestions import scan_directory, suggest, build_plan, render_bash

scan = scan_directory("./assets", recursive=True)
for s in suggest(scan):
    tag = "" if s.supported else " (generic)"
    print(s.source_ext, "->", s.target_ext, f"x{s.count}{tag}")

plan = build_plan(scan, "png", "jpg")
print(render_bash(plan))
```

## Extending

- Add rows to `GENERIC_ROUTES` for more common conversions.
- Register a real converter in `fileforge.converters.*` and it is picked up
  automatically as a **supported** suggestion — no change needed here.
