#!/usr/bin/env bash
# Build the distributable zip for boss.
#
# Steps:
#   1. Build the React frontend (`frontend/dist/`).
#   2. Stage a clean copy of the project into a temp dir.
#   3. Zip it as `dist/Provectus Analytics.zip` (overwrites any existing file).
#
# Usage:
#   tools/build_dist.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

DIST_DIR="$REPO_ROOT/dist"
STAGE_DIR="$(mktemp -d)"
APP_NAME="Provectus Analytics"
APP_STAGE="$STAGE_DIR/$APP_NAME"
ZIP_OUT="$DIST_DIR/$APP_NAME.zip"

cleanup() { rm -rf "$STAGE_DIR"; }
trap cleanup EXIT

echo "==> Building frontend"
( cd frontend && npm install --silent && npm run build )

[ -d "frontend/dist" ] || { echo "frontend/dist missing — build failed"; exit 1; }

echo "==> Staging into $APP_STAGE"
mkdir -p "$APP_STAGE"

# Files to ship at app root
for path in \
    Provectus.command \
    pyproject.toml \
    setup.cfg \
    requirements.txt \
    "Read Me First.pdf" \
    synthetic_fsp_clients.csv \
    synthetic_fsp_reservations.csv \
    synthetic_fsp_invoices.csv \
    synthetic_alumni_survey.csv \
    ; do
    if [ -e "$path" ]; then
        cp -R "$path" "$APP_STAGE/"
    fi
done

# Python package source (no Dash app/legacy code is excluded here — Phase 11
# removes those files. After 11.2 lands, src/ will only contain api/ + core.)
mkdir -p "$APP_STAGE/src"
rsync -a \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    src/provectus_analytics "$APP_STAGE/src/"

# Built frontend assets
mkdir -p "$APP_STAGE/frontend"
rsync -a --delete frontend/dist "$APP_STAGE/frontend/"

# Optional assets directory (sticker logo etc.)
if [ -d assets ]; then
    rsync -a --exclude '__pycache__' assets "$APP_STAGE/"
fi

echo "==> Writing $ZIP_OUT"
mkdir -p "$DIST_DIR"
rm -f "$ZIP_OUT"
( cd "$STAGE_DIR" && zip -qr "$ZIP_OUT" "$APP_NAME" )

echo "==> Done: $(ls -lh "$ZIP_OUT" | awk '{print $5, $9}')"
