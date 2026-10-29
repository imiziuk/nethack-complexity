#!/usr/bin/env bash
# Render frames.json into media/ (PNG screenshots, MP4, GIF). Usage: wsl -d Ubuntu -- bash run_render.sh
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"
"$HOME/nh-witness/venv/bin/python" render.py "$HERE/../../media/build/frames.json" "$HOME/nh-witness/nh/win/share" "$HERE/../../media"
