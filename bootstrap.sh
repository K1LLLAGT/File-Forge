#!/usr/bin/env bash
# FileForge 2.0 — cross-platform bootstrap.
#
# Detects the host (Linux / Android-Termux / WSL / macOS), runs the matching
# setup script, and then verifies that the discovery, suggestion and
# conversion subsystems import and answer.
#
#   ./bootstrap.sh                 # detect + setup + verify
#   ./bootstrap.sh --verify-only   # skip setup, just run the checks
#   ./bootstrap.sh --no-verify     # setup only
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DO_SETUP=1
DO_VERIFY=1

for arg in "$@"; do
    case "$arg" in
        --verify-only) DO_SETUP=0 ;;
        --no-verify)   DO_VERIFY=0 ;;
        -h|--help)
            grep '^#' "$0" | sed 's/^# \{0,1\}//' | head -n 10
            exit 0
            ;;
        *) echo "unknown arg: $arg" >&2; exit 2 ;;
    esac
done

# --------------------------------------------------------------------------- #
# OS detection
# --------------------------------------------------------------------------- #
detect_os() {
    local uname_s
    uname_s="$(uname -s 2>/dev/null || echo unknown)"
    if [ -n "${TERMUX_VERSION:-}" ] || [ -d /data/data/com.termux ]; then
        echo "android"
    elif grep -qiE '(microsoft|wsl)' /proc/version 2>/dev/null; then
        echo "wsl"
    elif [ "$uname_s" = "Darwin" ]; then
        echo "macos"
    elif [ "$uname_s" = "Linux" ]; then
        echo "linux"
    else
        echo "unknown"
    fi
}

OS="$(detect_os)"
echo "==> Detected platform: $OS"

# --------------------------------------------------------------------------- #
# Setup dispatch
# --------------------------------------------------------------------------- #
run_setup() {
    case "$OS" in
        linux|wsl|android|macos)
            # Termux/macOS have no dedicated script yet; the Linux script is
            # POSIX enough to work on all of them.
            echo "==> Running setup/setup_linux.sh"
            bash "$HERE/setup/setup_linux.sh"
            ;;
        *)
            echo "warn: no setup script for '$OS'." >&2
            echo "      On Windows run:  ./setup/setup_windows.ps1" >&2
            echo "      For Android see:  ./setup/setup_android.md" >&2
            return 1
            ;;
    esac
}

# --------------------------------------------------------------------------- #
# Verification
# --------------------------------------------------------------------------- #
run_verify() {
    echo "==> Verifying subsystems"
    local py="python3"
    command -v python >/dev/null 2>&1 && py="python"
    # If a venv exists, use it.
    if [ -f "$HERE/.venv/bin/activate" ]; then
        # shellcheck disable=SC1091
        source "$HERE/.venv/bin/activate"
        py="python"
    fi

    PYTHONPATH="$HERE/src${PYTHONPATH:+:$PYTHONPATH}" "$py" - <<'PYCODE'
import sys

def check(label, fn):
    try:
        fn()
        print(f"    ok: {label}")
    except Exception as exc:  # pragma: no cover - diagnostic path
        print(f"    FAIL: {label} -> {exc}")
        sys.exit(1)

def discovery_ok():
    from fileforge.discovery import normalize_alias
    assert normalize_alias("File Forge") == "fileforge"

def suggestions_ok():
    from fileforge.suggestions import scan_directory, suggest
    scan = scan_directory(".")
    suggest(scan)

def conversions_ok():
    from fileforge.core.registry import load_builtin_converters, registry
    load_builtin_converters()
    assert registry.routes(), "no converters registered"

check("discovery", discovery_ok)
check("suggestions", suggestions_ok)
check("conversions", conversions_ok)
print("==> All subsystems verified.")
PYCODE
}

# --------------------------------------------------------------------------- #
# Optional: clone/update ~/file-forge
# --------------------------------------------------------------------------- #
sync_home_checkout() {
    # Opt-in via FILEFORGE_SYNC=1 to keep a ~/file-forge checkout current.
    [ "${FILEFORGE_SYNC:-0}" = "1" ] || return 0
    local dest="$HOME/file-forge"
    local repo="${FILEFORGE_REPO:-https://github.com/K1LLLAGT/File-Forge.git}"
    if [ -d "$dest/.git" ]; then
        echo "==> Updating $dest"
        git -C "$dest" pull --ff-only || echo "warn: pull failed" >&2
    else
        echo "==> Cloning $repo -> $dest"
        git clone "$repo" "$dest" || echo "warn: clone failed" >&2
    fi
}

# --------------------------------------------------------------------------- #
main() {
    sync_home_checkout
    if [ "$DO_SETUP" = "1" ]; then
        run_setup || echo "warn: setup step reported an issue" >&2
    fi
    if [ "$DO_VERIFY" = "1" ]; then
        run_verify
    fi
    echo "==> Bootstrap complete."
}

main
