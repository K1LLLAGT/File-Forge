#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

cd "$(dirname "$0")"
pip install -r requirements.txt --quiet

echo "[fileforge-worker] starting ff_queue worker loop"
python3 -c "from ff_queue import worker_loop; worker_loop()"
