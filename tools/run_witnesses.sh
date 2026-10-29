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
  rsync -a --delete --exclude .git "$SRC/" "$WORK/nh/"
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
NH="$(ls "$PREFIX"/games/nethack "$PREFIX"/nethack 2>/dev/null | head -1)"

python3 - "$NH" "$HACKDIR" "$HERE/tools/witness" "$HERE/build/witness-results.txt" <<'PY'
import sys, os, glob, shutil, pexpect
nh, hackdir, wdir, out = sys.argv[1:5]
res = []
for f in sorted(glob.glob(os.path.join(wdir, '*.lua'))):
    name = os.path.basename(f)
    tmp = os.path.join(hackdir, name)
    src = open(f).read().replace('\r\n', '\n')
    open(tmp, 'w').write(src + '\nnh.pline("WITNESS DONE");\n')   # marker: reached the end without error()
    env = dict(os.environ, NETHACKOPTIONS='pettype:none,!autopickup,!timed_delay,number_pad:0,!legacy,!news',
               TERM='xterm', HOME=os.environ['HOME'])
    p = pexpect.spawn(nh, ['-D', '-u', 'witness', '-p', 'valkyrie', '-r', 'human', '-g', 'female', '-a', 'neutral'],
                      env=env, cwd=hackdir, encoding='latin-1', timeout=20, dimensions=(30, 100))
    log = []
    try:
        p.expect(['welcome', 'Welcome', pexpect.TIMEOUT]); log.append(p.before)
        p.send('\x1b'); p.send('#wizloadlua\r'); p.expect(['lua', 'file', pexpect.TIMEOUT])
        p.send(name + '\r')
        idx = p.expect(['WITNESS DONE', 'FAIL', 'HARNESS', 'rror', pexpect.TIMEOUT, pexpect.EOF])
        log.append(p.before + str(p.after))
        verdict = 'PASS' if idx == 0 else 'FAIL'
    except Exception as e:
        verdict, log = 'ERROR', log + [repr(e)]
    finally:
        p.terminate(force=True); os.remove(tmp)
    res.append(f'{verdict}  {name}\n' + ''.join(map(str, log))[-2000:] + '\n' + '-' * 60)
    print(verdict, name)
open(out, 'w').write('\n'.join(res))
PY
echo "results: $HERE/build/witness-results.txt"
