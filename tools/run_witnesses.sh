#!/usr/bin/env bash
# Run the witness scripts in tools/witness/ against a headless NetHack 5.0.0 build (WSL Ubuntu).
# ONLY run when Ivan is away from the laptop (CLAUDE.md rule). Not run yet.
#
# Usage (from Windows):  wsl -d Ubuntu -- bash /mnt/c/Users/ivanm/Downloads/IRA/Research/nethack-complexity/tools/run_witnesses.sh
# Needs once: sudo apt install build-essential bison flex libncurses-dev python3-pexpect   (Ivan runs sudo)
# Output: build/witness-results.txt (one PASS/FAIL line per script + captured screen text).
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$HERE/src"
WORK="$HOME/nh-witness"            # build outside /mnt/c (faster, no CRLF trouble)
PREFIX="$WORK/install"
mkdir -p "$WORK" "$HERE/build"

if [ ! -x "$PREFIX/games/nethack" ] && [ ! -x "$PREFIX/nethack" ]; then
  # fresh LF clone of the same tag (the Windows checkout has CRLF line endings, which break setup.sh)
  rm -rf "$WORK/nh"
  git clone -q --depth 1 --branch NetHack-5.0.0_Released https://github.com/NetHack/NetHack.git "$WORK/nh"
  test "$(git -C "$WORK/nh" rev-parse HEAD)" = 16ff59115315917b93185d026aeefea06db9b0f4
  cd "$WORK/nh/sys/unix" && sh setup.sh hints/linux.500
  cd "$WORK/nh"
  make fetch-lua
  # README: tests need a build WITHOUT dlb; install into a private prefix, wizard mode for our user
  make WANT_WIN_TTY=1 WANT_WIN_CURSES=0 PREFIX="$PREFIX" HACKDIR="$PREFIX/lib" \
       CFLAGS_DLB= -j"$(nproc)" all
  make WANT_WIN_TTY=1 WANT_WIN_CURSES=0 PREFIX="$PREFIX" HACKDIR="$PREFIX/lib" install
  sed -i "s/^WIZARDS=.*/WIZARDS=$USER/" "$PREFIX/lib/sysconf" || true
fi
HACKDIR="$PREFIX/lib"
NH="$PREFIX/games/nethack"; [ -x "$NH" ] || NH="$PREFIX/nethack"
grep -q "^WIZARDS=.*$USER" "$HACKDIR/sysconf" || sed -i "s/^WIZARDS=.*/WIZARDS=$USER/" "$HACKDIR/sysconf"

python3 "$HERE/tools/witness_driver.py" "$NH" "$HACKDIR" "$HERE/tools/witness" "$HERE/build/witness-results.txt"
echo "results: $HERE/build/witness-results.txt"
