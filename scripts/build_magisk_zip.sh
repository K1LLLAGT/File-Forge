#!/usr/bin/env bash
# Package the Magisk module into a flashable zip and bundle the Python engine
# so `fileforge` works system-wide on-device.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MODULE="$ROOT/magisk-module"
STAGE="$(mktemp -d)"
VERSION="$(grep '^version=' "$MODULE/module.prop" | cut -d= -f2)"
OUT="$ROOT/dist/fileforge-magisk-${VERSION}.zip"

mkdir -p "$ROOT/dist"
cp -r "$MODULE/." "$STAGE/"
# Bundle the conversion engine into the module payload dir.
mkdir -p "$STAGE/pkg"
cp -r "$ROOT/src/fileforge" "$STAGE/pkg/"

( cd "$STAGE" && zip -r9 "$OUT" . -x '.*' >/dev/null )
rm -rf "$STAGE"
echo "built: $OUT"
