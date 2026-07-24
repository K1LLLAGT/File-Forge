#!/usr/bin/env bash
# Launch the selected FileForge service. SERVICE=cloud-api | license
set -euo pipefail

PORT="${PORT:-8080}"
SERVICE="${SERVICE:-cloud-api}"

case "$SERVICE" in
  cloud-api)
    cd /app/cloud-api
    exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
    ;;
  license)
    cd /app/license-server
    exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
    ;;
  *)
    echo "unknown SERVICE='$SERVICE' (expected cloud-api or license)" >&2
    exit 64
    ;;
esac
