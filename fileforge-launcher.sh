#!/data/data/com.termux/files/usr/bin/bash
#
# fileforge-launcher.sh — brings up the whole FileForge stack:
#   Redis -> FastAPI backend -> Redis queue worker -> Next.js frontend
# then opens the Conversion Dashboard.
#
# This is the single, unified project root — there is no separate
# ~/fileforge-web-site anymore; backend/, app/, components/, cli/ all
# live under this one directory.
#
# Usage:
#   ./fileforge-launcher.sh          normal mode — logs interleave in this terminal
#   ./fileforge-launcher.sh --debug  debug mode — each service logs to its own file
#                                    under logs/, uvicorn runs at --log-level debug,
#                                    and this terminal tails all three together
#                                    with clear ==> file <== headers instead of
#                                    silently mixing three processes' output.

set -uo pipefail

FILEFORGE_ROOT="$(cd "$(dirname "$0")" && pwd)"
export FILEFORGE_API="http://127.0.0.1:8090"
export FILEFORGE_BACKEND_URL="http://127.0.0.1:8091"

DEBUG=0
if [ "${1:-}" = "--debug" ]; then
  DEBUG=1
  export FILEFORGE_LOG_LEVEL="debug"
  LOG_DIR="$FILEFORGE_ROOT/logs"
  mkdir -p "$LOG_DIR"
  : > "$LOG_DIR/backend.log"
  : > "$LOG_DIR/worker.log"
  : > "$LOG_DIR/frontend.log"
  echo "[fileforge-launcher] debug mode: logging to $LOG_DIR/{backend,worker,frontend}.log"
fi

PIDS=()

cleanup() {
  command -v termux-wake-unlock >/dev/null 2>&1 && termux-wake-unlock
  echo ""
  echo "[fileforge-launcher] shutting down..."
  for pid in "${PIDS[@]:-}"; do
    kill "$pid" >/dev/null 2>&1 || true
  done
}
command -v termux-wake-lock >/dev/null 2>&1 && termux-wake-lock
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
if [ "$DEBUG" = "1" ]; then
  (cd "$FILEFORGE_ROOT/backend" && ./run_backend.sh) >> "$FILEFORGE_ROOT/logs/backend.log" 2>&1 &
else
  (cd "$FILEFORGE_ROOT/backend" && ./run_backend.sh) &
fi
PIDS+=($!)

# --- Redis queue worker ---
echo "[fileforge-launcher] Starting queue worker..."
if [ "$DEBUG" = "1" ]; then
  (cd "$FILEFORGE_ROOT/backend" && ./run_worker.sh) >> "$FILEFORGE_ROOT/logs/worker.log" 2>&1 &
else
  (cd "$FILEFORGE_ROOT/backend" && ./run_worker.sh) &
fi
PIDS+=($!)

# --- Next.js frontend ---
echo "[fileforge-launcher] Starting Next.js frontend on :8090..."
if [ "$DEBUG" = "1" ]; then
  (cd "$FILEFORGE_ROOT" && npm run dev) >> "$FILEFORGE_ROOT/logs/frontend.log" 2>&1 &
else
  (cd "$FILEFORGE_ROOT" && npm run dev) &
fi
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
echo "[fileforge-launcher] Doctor: $FILEFORGE_ROOT/scripts/fileforge-doctor.sh"
echo "[fileforge-launcher] Press Ctrl+C to stop all services."

if [ "$DEBUG" = "1" ]; then
  tail -n +1 -f "$FILEFORGE_ROOT/logs/backend.log" "$FILEFORGE_ROOT/logs/worker.log" "$FILEFORGE_ROOT/logs/frontend.log"
else
  wait
fi
