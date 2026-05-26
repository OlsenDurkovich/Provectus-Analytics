#!/bin/bash
# Provectus Analytics — double-click launcher (macOS)
# First run: creates a Python virtual environment and installs dependencies.
# Subsequent runs: just launches the app + opens it in your default browser.
#
# To stop the app: close this Terminal window, or press Ctrl+C.

set -e
cd "$(dirname "$0")"

# ---- Check for Python 3 -----------------------------------------------------
if ! command -v python3 >/dev/null 2>&1; then
    echo ""
    echo "  ERROR: Python 3 is not installed on this Mac."
    echo "  Install it from https://www.python.org/downloads/macos/"
    echo "  Then double-click Provectus.command again."
    echo ""
    read -p "Press Enter to close..."
    exit 1
fi

# ---- First-run setup --------------------------------------------------------
if [ ! -d ".venv" ]; then
    echo ""
    echo "  First-time setup — installing dependencies (1-2 minutes)..."
    echo ""
    python3 -m venv .venv
    source .venv/bin/activate
    pip install --upgrade pip --quiet
    pip install -e "." --quiet
    echo ""
    echo "  Done. Launching Provectus Analytics..."
    echo ""
else
    source .venv/bin/activate
fi

PORT=8050

# ---- Open the browser shortly after the server starts -----------------------
( sleep 2 && open "http://127.0.0.1:${PORT}" ) &

# ---- Launch FastAPI via uvicorn ---------------------------------------------
echo "  Provectus Analytics is running at http://127.0.0.1:${PORT}"
echo "  To stop: close this window or press Ctrl+C."
echo ""
exec python3 -m uvicorn provectus_analytics.api.main:app \
    --host 127.0.0.1 --port "${PORT}"
