# Setup & Bootstrap

FileForge 2.0 ships a small, portable bootstrap that detects the host, runs the
right setup script, and verifies that the discovery, suggestion, and conversion
subsystems import and answer.

## Layout

```
bootstrap.sh              # OS detection + setup dispatch + verification
setup/
  setup_linux.sh          # Linux / WSL / macOS / Termux installer
  setup_windows.ps1       # Windows 11 installer
  setup_android.md        # Android Studio + Chaquopy instructions
```

## One-shot bootstrap

```bash
./bootstrap.sh                 # detect platform, run setup, verify
./bootstrap.sh --no-verify     # setup only
./bootstrap.sh --verify-only   # skip setup, just run the checks
```

### What it does

1. **Detects** the platform: `linux`, `wsl`, `android` (Termux), `macos`, or
   `unknown`. WSL is detected by scanning `/proc/version`; Termux by
   `$TERMUX_VERSION` / the Termux data dir.
2. **Runs setup** — dispatches to `setup/setup_linux.sh` for POSIX hosts. On
   Windows it points you at `setup/setup_windows.ps1`; for Android it points at
   `setup/setup_android.md`.
3. **Verifies** three subsystems in a subprocess and fails loudly if any break:
   - `discovery` — `normalize_alias("File Forge") == "fileforge"`
   - `suggestions` — scans the current directory and produces suggestions
   - `conversions` — loads the built-in converters and asserts the registry is
     non-empty

### Optional: sync a `~/file-forge` checkout

Opt in with an environment variable to clone or fast-forward a home checkout
before setup:

```bash
FILEFORGE_SYNC=1 ./bootstrap.sh
# override the source with FILEFORGE_REPO=<url>
```

## Linux / WSL / macOS / Termux — `setup/setup_linux.sh`

```bash
./setup/setup_linux.sh
```

- Creates a virtualenv at `.venv` (skip with `FILEFORGE_NO_VENV=1`).
- Installs the package editable: `pip install -e .`
- Extras via `FILEFORGE_EXTRAS`, e.g.:

  ```bash
  FILEFORGE_EXTRAS="images,pdf,cloud" ./setup/setup_linux.sh
  ```

- Verifies the four console entry points are on `PATH`:
  `fileforge`, `fileforge-discover`, `fileforge-suggest`, `fileforge-cli`.

## Windows 11 — `setup/setup_windows.ps1`

```powershell
./setup/setup_windows.ps1
```

- Finds a Python launcher (`py` / `python` / `python3`).
- Creates/activates a `.venv` (skip with `$env:FILEFORGE_NO_VENV = '1'`).
- Installs editable, honouring `$env:FILEFORGE_EXTRAS`.
- Verifies the console entry points.

For the packaged desktop `.exe`, see the desktop build tooling; this script sets
up the Python engine and CLIs that the desktop app reuses.

## Android — `setup/setup_android.md`

Android uses Android Studio + Gradle + Chaquopy rather than a shell installer.
The discovery/suggestion engine is pure-Python and runs inside Chaquopy
unchanged. See [`setup/setup_android.md`](setup/setup_android.md) and
[`android/README.md`](android/README.md).

## Verify anytime

```bash
./bootstrap.sh --verify-only
```

Expected output:

```
==> Verifying subsystems
    ok: discovery
    ok: suggestions
    ok: conversions
==> All subsystems verified.
```
