#!/usr/bin/env bash
# R_neigh.sh -- C-vs-model neighbourhood check (proofs/exptime/R-neighbourhood.md) inside WSL.
#   R_neigh.sh setup                  private HACKDIR copies ~/nh-witness/rneigh/h0..h11 (never shared with other runs)
#   R_neigh.sh run <phase> [wear|nowear]   run build/rgame/jobs_<phase>.json in the real game (RPROC games, default 8)
set -e
cd /mnt/c/Users/ivanm/Downloads/IRA/Research/nethack-complexity/tools/exptime
if [ "$1" = setup ]; then
  rm -rf ~/nh-witness/rneigh
  for i in 0 1 2 3 4 5 6 7 8 9 10 11; do
    d=~/nh-witness/rneigh/h$i
    mkdir -p "$d"
    cp -a ~/nh-witness/install/lib/. "$d/"
    rm -f "$d"/save/* "$d"/*.lua "$d"/*wizard*
  done
  ls ~/nh-witness/rneigh
  exit 0
fi
exec ~/nh-witness/venv/bin/python -u R_neigh.py "$@"
