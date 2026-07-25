# Discovery & Normalization Layer

FileForge checkouts accumulate many spellings over time — `File Forge`,
`FileForge`, `File-Forge`, `fileforge`, `~/file-forge`, and more. The discovery
layer resolves every one of those to a **single canonical identity** and walks
the filesystem to find the concrete instances of the project, tagging each with
the roles it plays.

- Library: [`src/fileforge/discovery.py`](src/fileforge/discovery.py)
- CLI: `fileforge-discover`

## Canonical identity

| Field            | Value           |
|------------------|-----------------|
| `CANONICAL_NAME` | `FileForge 2.0` |
| `CANONICAL_ID`   | `fileforge`     |

Every alias resolves to `CANONICAL_ID`.

## Alias resolution logic

Matching is **case-, whitespace-, and separator-insensitive**. Internally a
single regex treats any run of space / `-` / `_` / `.` between `file` and
`forge` as a separator, and tolerates a trailing `2` or `2.0`:

```
file[\s\-_.]*forge(?:\s*2(?:\.0)?)?
```

Path-like inputs are expanded (`~`) and only the final path component is tested,
so `~/dev/file-forge/` resolves just like `File Forge`.

```python
from fileforge.discovery import normalize_alias, is_alias

normalize_alias("File Forge")     # -> "fileforge"
normalize_alias("~/file-forge/")  # -> "fileforge"
normalize_alias("forge-file")     # -> None
is_alias("FileForge2")            # -> True
```

## Discovery methodology

`discover(roots, max_depth=4)` walks each root with `os.walk`, pruning noise
directories (`.git`, `node_modules`, `__pycache__`, `.venv`, `build`, …) and
enforcing a depth limit. A directory is recorded as an **instance** when either:

1. its **name** is a FileForge alias (`matched_via="name"`), **or**
2. it contains an **instance marker** (`matched_via="marker"`), one of:
   `pyproject.toml`, `src/fileforge`, `android2/app/src/main/python/ffbridge.py`,
   `desktop/fileforge_gui.py`.

Default roots (when none are given) are the current directory, `$HOME`, and the
common `~/file-forge` / `~/fileforge` project dirs — de-duplicated and filtered
to those that exist.

## Role identification

Each instance is tagged with every role whose marker files it contains. A
monorepo checkout carries several at once.

| Role        | Detected by (any of)                                        |
|-------------|-------------------------------------------------------------|
| `android`   | `build.gradle.kts`, `AndroidManifest.xml`, `settings.gradle.kts` |
| `desktop`   | `fileforge_gui.py`, `build_windows.ps1`, `FileForge.exe`    |
| `cloud`     | `cloud-api`, `app/api.py`, `app/metering.py`                |
| `backend`   | `src/fileforge/core/registry.py`, `src/fileforge`           |
| `licensing` | `license-server`, `licensing.py`                            |
| `packaging` | `magisk-module`, `module.prop`, `build_magisk_zip.sh`       |
| `web`       | `index.html`, `package.json`, `vite.config.ts`              |
| `cli`       | `pyproject.toml`, `cli.py`                                   |
| `docs`      | `README.md`, `ARCHITECTURE.md`                              |

## CLI usage

```bash
fileforge-discover                     # scan default roots (text report)
fileforge-discover ~/code ~/projects   # scan specific roots
fileforge-discover --json              # machine-readable output
fileforge-discover --max-depth 6       # deeper walk
fileforge-discover --normalize "File Forge"   # resolve one alias and exit
```

Exit code is `0` when at least one instance is found (or the alias resolves),
`1` otherwise — handy in scripts.

### JSON shape

```json
{
  "canonical_name": "FileForge 2.0",
  "canonical_id": "fileforge",
  "aliases": ["File Forge", "FileForge", "File-Forge", "..."],
  "roots": ["/home/you", "/home/you/file-forge"],
  "roles": ["backend", "cli", "cloud"],
  "instances": [
    {
      "path": "/home/you/file-forge",
      "canonical": "fileforge",
      "matched_via": "name",
      "roles": ["backend", "cli", "cloud"],
      "markers": ["pyproject.toml", "src/fileforge"]
    }
  ]
}
```

## Extensibility

- **New aliases**: add spellings to `KNOWN_ALIASES` (display only) and, if a new
  separator style is needed, widen the `_ALIAS_RE` character class.
- **New roles**: append a `(role, markers)` tuple to `_ROLE_MARKERS`. Order is
  irrelevant — an instance collects every role whose markers it matches.
- **New instance markers**: extend `_INSTANCE_MARKERS` so marker-only checkouts
  (e.g. a bare monorepo root) are detected.
- **Skip more noise**: add directory names to `_SKIP_DIRS`.
