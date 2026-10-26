#!/usr/bin/env bash
# macOS / Linux launcher. Run: bash START.sh
set -e
cd "$(dirname "$0")/backend"
command -v python3 >/dev/null || { echo "Python 3.10+ is required"; exit 1; }
[ -d .venv ] || { echo "[1/4] Creating virtual environment..."; python3 -m venv .venv; }
source .venv/bin/activate
if [ ! -f .venv/deps_installed ]; then
  echo "[2/4] Installing packages (first run only)..."
  pip install -r requirements.txt && touch .venv/deps_installed
fi
if [ ! -f data/krishimandi.db ]; then
  echo "[3/4] Loading demo data and training forecasts (first run only)..."
  python -m etl.pipeline --synthetic && python -m ml.run_forecasts
fi
echo "[4/4] Starting at http://localhost:8000  (Ctrl+C to stop)"
(sleep 3; (xdg-open http://localhost:8000 || open http://localhost:8000) >/dev/null 2>&1) &
python -m uvicorn app.main:app --port 8000
