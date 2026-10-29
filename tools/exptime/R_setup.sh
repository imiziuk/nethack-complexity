#!/usr/bin/env bash
# R_setup.sh -- private HACKDIR copies for the real-game oracle (one per parallel worker), so our wizard-mode
# games never share lock/save files with other witness runs that use ~/nh-witness/install/lib.
set -e
rm -rf ~/nh-witness/realgame
for i in 0 1 2 3 4 5 6 7 p; do
  d=~/nh-witness/realgame/h$i
  mkdir -p "$d"
  cp -a ~/nh-witness/install/lib/. "$d/"
  rm -f "$d"/save/* "$d"/*.lua
done
ls ~/nh-witness/realgame
