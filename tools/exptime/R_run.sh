#!/usr/bin/env bash
# R_run.sh -- run R_run.py inside WSL with the witness venv (pexpect, pyte). Usage: R_run.sh <phase> [gadgets...]
cd /mnt/c/Users/ivanm/Downloads/IRA/Research/nethack-complexity/tools/exptime
exec ~/nh-witness/venv/bin/python -u R_run.py "$@"
