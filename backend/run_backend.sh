#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

# FileForge backend runner.
# Always cd into this script's own directory first: uvicorn is invoked
# as `uvicorn server:app`, and server.py's imports (engine, batch,
# ff_queue, ...) are absolute, resolved relative to this directory
# being on sys.path — not relative package imports.
cd "$(dirname "$0")"

pip install -r requirements.txt --quiet

echo "[fileforge-backend] starting on 127.0.0.1:8091 (log-level: ${FILEFORGE_LOG_LEVEL:-info})"
uvicorn server:app --host 127.0.0.1 --port 8091 --log-level "${FILEFORGE_LOG_LEVEL:-info}"
