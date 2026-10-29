#!/usr/bin/env bash
# Capture the demo scenes in the headless WSL NetHack build (see capture.py). Usage: wsl -d Ubuntu -- bash run_capture.sh
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
PREFIX="$HOME/nh-witness/install"
PY="$HOME/nh-witness/venv/bin/python"
OUT="$HERE/../../media/build"
mkdir -p "$OUT"
cd "$HERE"
$PY gen_levels.py >/dev/null 2>&1 || python3 gen_levels.py
$PY capture.py "$PREFIX/games/nethack" "$PREFIX/lib" "$HERE/levels" "$OUT/frames.json"
