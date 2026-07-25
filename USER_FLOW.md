# Unified User Flow (`fileforge-cli`)

`fileforge-cli` ties the three subsystems together into a single report:

- **Discovery** — resolve any aliases you supply, and (optionally) enumerate
  FileForge instances under the target directory.
- **Directory analysis** — scan and tally file extensions.
- **Suggestions + routes** — produce a personalized conversion matrix and a
  ranked list of recommended, engine-supported conversions.

- Library: [`src/fileforge/unified_cli.py`](src/fileforge/unified_cli.py)
- CLI: `fileforge-cli`

## The flow

```
 aliases ─┐
          ├─► discovery.normalize_alias ─► alias resolution table
 --dir  ──┤
          ├─► suggestions.scan_directory ─► extension frequencies
          │
 --ext  ──┴─► _build_matrix ─┬─► personalized conversion matrix
                             └─► recommendations (supported, ranked)
                                        │
                             --emit-scripts ─► run_conversions.sh / .ps1
```

## Outputs

### 1. Alias resolution
Every `--alias` you pass is resolved to the canonical id (or reported as *not a
FileForge alias*).

### 2. Personalized conversion matrix
One row per source extension present (or per `--ext` you request), listing the
engine-supported targets and — separately — the generic targets with no engine
route yet:

```
personalized conversion matrix:
  .png      (x12) -> bmp, gif, jpg, tiff, webp   [generic: pdf]
  .csv      (x3)  -> json, tsv, xlsx
```

If you request an extension that has **no files** in the directory, it still
appears with `count=0` so you can see what *would* be possible.

### 3. Recommended conversions
The top engine-supported routes, ranked by how many files they touch:

```
recommended conversions:
     png -> jpg    (x12)  PNG -> JPG (Pillow)
     csv -> json   (x3)   CSV -> pretty JSON array
```

## Usage

```bash
# Analyze the current directory
fileforge-cli --dir .

# Resolve aliases while you're at it
fileforge-cli --alias "File Forge" --alias fileforge --dir .

# Focus the matrix on specific extensions
fileforge-cli --dir ./media --ext png --ext mp4

# Also enumerate FileForge instances under the directory
fileforge-cli --dir ~/code --discover

# Machine-readable
fileforge-cli --dir . --json

# Guided prompts
fileforge-cli --interactive

# Emit driver scripts for the top recommendation
fileforge-cli --dir ./assets --ext png --emit-scripts ./out
```

## JSON shape

```json
{
  "directory": "/path/analyzed",
  "aliases": { "File Forge": "fileforge", "nope": null },
  "instances": [ { "path": "...", "roles": ["backend"] } ],
  "matrix": [
    { "source_ext": "png", "targets": ["jpg", "webp"],
      "generic_targets": ["pdf"], "count": 12 }
  ],
  "recommendations": [
    { "source_ext": "png", "target_ext": "jpg", "count": 12,
      "supported": true, "tier": "free", "description": "PNG -> JPG (Pillow)" }
  ]
}
```

## Where it fits

`fileforge-cli` is the front door for the discovery/suggestion layer; the plain
`fileforge` command remains the converter that actually performs the work. A
typical session:

```bash
fileforge-cli --dir ./assets --ext png --emit-scripts ./out   # plan
bash ./out/run_conversions.sh                                 # execute
```
