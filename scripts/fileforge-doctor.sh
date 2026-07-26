#!/data/data/com.termux/files/usr/bin/bash
#
# fileforge-doctor.sh — environment + runtime health check for the
# FileForge web app (backend/app/components/cli — not the separate
# CLI/apps product, which has its own `fileforge doctor` command).
#
# Safe to run any time: read-only, never starts/stops/kills anything.
# Exits 0 if nothing failed, 1 if any check failed (so it's usable in
# scripts: `./scripts/fileforge-doctor.sh || echo "not healthy"`).

set -uo pipefail

FILEFORGE_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

PASS=0
WARN=0
FAIL=0

pass() { echo "  [ OK ] $1"; PASS=$((PASS + 1)); }
warn() { echo "  [WARN] $1"; WARN=$((WARN + 1)); }
fail() { echo "  [FAIL] $1"; FAIL=$((FAIL + 1)); }
section() { echo ""; echo "== $1 =="; }

section "Required binaries"
for bin in ffmpeg convert pandoc redis-server redis-cli node npm python3 curl; do
  if command -v "$bin" >/dev/null 2>&1; then
    pass "$bin found"
  else
    fail "$bin NOT found — run ./scripts/install_conversion_tools.sh"
  fi
done

section "LibreOffice (proot-distro Ubuntu, used for doc -> pdf/html)"
if command -v proot-distro >/dev/null 2>&1; then
  pass "proot-distro installed"
  if timeout 10 proot-distro login ubuntu -- true >/dev/null 2>&1; then
    pass "ubuntu proot container present"
    if timeout 15 proot-distro login ubuntu -- command -v libreoffice >/dev/null 2>&1; then
      pass "libreoffice present inside ubuntu proot"
    else
      warn "libreoffice missing inside ubuntu proot — doc conversions to pdf/html will fail"
    fi
  else
    warn "ubuntu proot container not reachable — run ./scripts/install_conversion_tools.sh"
  fi
else
  warn "proot-distro not installed — document conversions (docx/pptx/xlsx) will fail"
fi

section "Redis"
if redis-cli ping >/dev/null 2>&1; then
  pass "redis-server responding to PING"
  DEPTH="$(redis-cli llen fileforge:jobs 2>/dev/null || echo '?')"
  echo "         queue depth: $DEPTH"
else
  fail "redis-server not responding — start it with: redis-server --daemonize yes"
fi

section "Backend (FastAPI, :8091)"
if curl -sf --max-time 3 http://127.0.0.1:8091/health >/dev/null 2>&1; then
  pass "backend responding at http://127.0.0.1:8091/health"
else
  fail "backend not responding on :8091 — is fileforge-launcher.sh running?"
fi
if pgrep -af "uvicorn server:app" >/dev/null 2>&1; then
  pass "uvicorn process running"
else
  warn "no uvicorn process found"
fi

section "Worker (ff_queue)"
if pgrep -af "ff_queue" >/dev/null 2>&1; then
  pass "worker process running"
else
  warn "no worker process found — queued conversions won't be processed"
fi

section "Frontend (Next.js, :8090)"
if curl -sf --max-time 3 http://127.0.0.1:8090/ >/dev/null 2>&1; then
  pass "frontend responding at http://127.0.0.1:8090/"
else
  fail "frontend not responding on :8090"
fi
if pgrep -af "next-server|next dev" >/dev/null 2>&1; then
  pass "next dev process running"
else
  warn "no next dev process found"
fi

section "Project setup"
if [ -d "$FILEFORGE_ROOT/node_modules" ]; then
  pass "node_modules installed"
else
  fail "node_modules missing — run: npm install"
fi

if command -v git >/dev/null 2>&1 && git -C "$FILEFORGE_ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  DIRTY="$(git -C "$FILEFORGE_ROOT" status --porcelain | wc -l)"
  if [ "$DIRTY" -eq 0 ]; then
    pass "git working tree clean"
  else
    warn "$DIRTY uncommitted change(s) in the repo"
  fi
fi

section "Disk usage (backend output dirs are never auto-cleaned)"
for d in output compressed thumbs; do
  DIR="$FILEFORGE_ROOT/backend/$d"
  if [ -d "$DIR" ]; then
    COUNT="$(find "$DIR" -type f ! -name '.gitkeep' | wc -l)"
    SIZE="$(du -sh "$DIR" 2>/dev/null | cut -f1)"
    if [ "$COUNT" -gt 200 ]; then
      warn "backend/$d has $COUNT files ($SIZE) — every job's input+output stays forever; consider clearing old ones"
    else
      echo "         backend/$d: $COUNT files ($SIZE)"
    fi
  fi
done

echo ""
echo "== Summary: $PASS passed, $WARN warnings, $FAIL failed =="
if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
exit 0
