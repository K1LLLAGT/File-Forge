#!/data/data/com.termux/files/usr/bin/bash
#
# fileforge-launcher.sh — brings up the whole FileForge stack:
#   Redis -> FastAPI backend -> Redis queue worker -> Next.js frontend
# then opens the Conversion Dashboard.
#
# This is the single, unified project root — there is no separate
# ~/fileforge-web-site anymore; backend/, app/, components/, cli/ all
# live under this one directory.

set -uo pipefail

FILEFORGE_ROOT="$(cd "$(dirname "$0")" && pwd)"
export FILEFORGE_API="http://127.0.0.1:8090"
export FILEFORGE_BACKEND_URL="http://127.0.0.1:8091"

PIDS=()

cleanup() {
  echo ""
  echo "[fileforge-launcher] shutting down..."
  for pid in "${PIDS[@]:-}"; do
    kill "$pid" >/dev/null 2>&1 || true
  done
}
trap cleanup EXIT INT TERM

echo "[fileforge-launcher] root: $FILEFORGE_ROOT"

# --- Redis ---
if redis-cli ping >/dev/null 2>&1; then
  echo "[fileforge-launcher] Redis already running."
else
  echo "[fileforge-launcher] Starting Redis..."
  redis-server --daemonize yes
  sleep 1
  if ! redis-cli ping >/dev/null 2>&1; then
    echo "[fileforge-launcher] WARNING: Redis did not come up. Queue features will fail." >&2
  fi
fi

# --- FastAPI backend ---
echo "[fileforge-launcher] Starting FastAPI backend on :8091..."
(cd "$FILEFORGE_ROOT/backend" && ./run_backend.sh) &
PIDS+=($!)

# --- Redis queue worker ---
echo "[fileforge-launcher] Starting queue worker..."
(cd "$FILEFORGE_ROOT/backend" && ./run_worker.sh) &
PIDS+=($!)

# --- Next.js frontend ---
echo "[fileforge-launcher] Starting Next.js frontend on :8090..."
(cd "$FILEFORGE_ROOT" && npm run dev) &
PIDS+=($!)

echo "[fileforge-launcher] Waiting for services to come up..."
sleep 5

echo "[fileforge-launcher] Opening Conversion Dashboard..."
if command -v termux-open-url >/dev/null 2>&1; then
  termux-open-url "http://127.0.0.1:8090/conversion-dashboard"
else
  echo "[fileforge-launcher] termux-open-url not found — open this manually:"
  echo "  http://127.0.0.1:8090/conversion-dashboard"
fi

echo "[fileforge-launcher] System launched. CLI: $FILEFORGE_ROOT/cli/fileforge-cli"
echo "[fileforge-launcher] Press Ctrl+C to stop all services."

wait
