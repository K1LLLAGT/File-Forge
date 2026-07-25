#!/usr/bin/env bash
# FileForge 2.0 — Linux/WSL setup.
# Installs the FileForge engine (editable) plus the discovery/suggestion CLIs.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${PYTHON:-python3}"

echo "==> FileForge 2.0 setup (Linux/WSL)"
echo "    repo root: $HERE"

if ! command -v "$PY" >/dev/null 2>&1; then
    echo "error: $PY not found. Install Python 3.9+ and re-run." >&2
    exit 1
fi

echo "==> Python: $("$PY" --version)"

# Prefer a virtual environment unless the caller opts out.
if [ "${FILEFORGE_NO_VENV:-0}" != "1" ]; then
    VENV="$HERE/.venv"
    if [ ! -d "$VENV" ]; then
        echo "==> Creating virtualenv at $VENV"
        "$PY" -m venv "$VENV"
    fi
    # shellcheck disable=SC1091
    source "$VENV/bin/activate"
    PY="python"
fi

echo "==> Upgrading pip"
"$PY" -m pip install --quiet --upgrade pip

# Optional extras: pass e.g. FILEFORGE_EXTRAS="images,pdf,cloud"
EXTRAS="${FILEFORGE_EXTRAS:-}"
if [ -n "$EXTRAS" ]; then
    echo "==> Installing FileForge with extras: [$EXTRAS]"
    "$PY" -m pip install --quiet -e "$HERE[$EXTRAS]"
else
    echo "==> Installing FileForge (core)"
    "$PY" -m pip install --quiet -e "$HERE"
fi

echo "==> Verifying console entry points"
for cmd in fileforge fileforge-discover fileforge-suggest fileforge-cli; do
    if command -v "$cmd" >/dev/null 2>&1; then
        echo "    ok: $cmd"
    else
        echo "    warn: $cmd not on PATH (activate the venv: source $HERE/.venv/bin/activate)"
    fi
done

echo "==> Done. Try:"
echo "    fileforge list"
echo "    fileforge-discover"
echo "    fileforge-suggest ."
echo "    fileforge-cli --dir . --discover"
