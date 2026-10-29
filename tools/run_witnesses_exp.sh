#!/usr/bin/env bash
# Teleport-coin witnesses W9-W11 (proofs/exptime-feasibility.md sec. 7/9) on the headless WSL build of run_witnesses.sh.
# Usage (from Windows): wsl -d Ubuntu -- bash /mnt/c/Users/ivanm/Downloads/IRA/Research/nethack-complexity/tools/run_witnesses_exp.sh
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
PREFIX="$HOME/nh-witness/install"
NH="$PREFIX/games/nethack"; [ -x "$NH" ] || NH="$PREFIX/nethack"
PY="$HOME/nh-witness/venv/bin/python"
OUT="$HERE/build/witness-exp-results.txt"
mkdir -p "$HERE/build"
echo "teleport-coin witnesses, $(date -u +%Y-%m-%dT%H:%MZ), NetHack 5.0.0 headless tty, one fresh game (system seed) per run" > "$OUT"
for spec in exp_coin.lua:30 exp_coin_noboots.lua:15 exp_coin_zone3.lua:10 exp_coin_noexclude.lua:10; do
  "$PY" "$HERE/tools/witness_driver_exp.py" "$NH" "$PREFIX/lib" "$HERE/tools/witness_exp/${spec%%:*}" "${spec##*:}" "$OUT"
done
echo "results: $OUT"
