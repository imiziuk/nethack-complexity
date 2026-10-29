"""Variant witness driver for the teleport-coin witnesses (tools/witness_exp/exp_*.lua, W9-W11).

Runs ONE script N times, each in a fresh game (fresh system-random seed), and records the RES/SEQ/OTHER lines the
script plines plus counts of fumbling/escape/teleport messages seen on the tty. Differences from witness_driver.py:
  - answers the wizard-mode-only teleport getpos ("Where do you want to be teleported?" + "(For instructions ...)")
    with '.', i.e. the hero's own cell T; T is a trap cell, so teleok() fails, "Sorry..." follows and the game falls
    through to safe_teleds() exactly as for a non-wizard hero (teleport.c scrolltele);
  - matches "Dlvl:" only until #wizloadlua has been sent (status redraws would otherwise eat the loop budget).
Usage: python witness_driver_exp.py <nethack> <hackdir> <script.lua> <runs> <out.txt>   (appends to out.txt)
"""
import glob, os, re, sys, time
import pexpect

nh, hackdir, script, runs, out = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5]
ANSI = re.compile(r'\x1b\[[0-9;?]*[A-Za-z]|\x1b[()][0-9A-Za-z]|\x1b[=>]')
OPTS = ('role:valkyrie,race:human,gender:female,align:neutral,pettype:none,!autopickup,'
        '!timed_delay,number_pad:0,!legacy,!news,!splash_screen,!tutorial,paranoid_confirmation:pray')
KEYS = {
    'escape': r'escape\s*a\s*teleportation\s*trap',
    'tele_q': r'Where\s*do\s*you\s*want\s*to\s*be\s*teleported',
    'sorry': r'Sorry\.\.\.',
    'trip': r'trip\s*over',
    'slip': r'slip\s*and\s*nearly\s*fall',
    'flounder': r'You\s*flounder',
    'stumble': r'You\s*stumble',
    'noise': r'lot\s*of\s*noise',
    'disoriented': r'disoriented',
    'wrenching': r'wrenching',
    'shudder': r'shudder',
    'mysterious': r'mysterious\s*force',
    'materialize': r'materialize',
    'burdened': r'Burdened',
    'stressed': r'Stressed',
}


def clean(t):
    return ANSI.sub('', t or '')


def run_one(name, src):
    tmp = os.path.join(hackdir, name)
    open(tmp, 'w').write(src + '\nnh.pline("WITNESS DONE");\n')
    for f in glob.glob(os.path.join(hackdir, 'save', '*')) + glob.glob(os.path.join(hackdir, '*wizard*')):
        if os.path.isfile(f) and not f.endswith('.lua'):
            os.remove(f)
    env = dict(os.environ, NETHACKOPTIONS=OPTS, TERM='xterm')
    p = pexpect.spawn(nh, ['-D', '-u', 'witness'], env=env, cwd=hackdir, encoding='latin-1',
                      timeout=1.2, dimensions=(30, 120))
    log, verdict, sent = [], 'ERROR', False
    try:
        for _ in range(3000):
            pats = [r'WITNESS DONE', r'(FAIL|HARNESS)[^\n]*', r'[Ll]ua error[^\n]*|rror:[^\n]*',
                    r'--More--', r'\[ynq?a?\]|\[yn\]', r'Hit return', r'[Ll]oad which lua file\?',
                    r'For instructions type', pexpect.TIMEOUT, pexpect.EOF]
            if not sent:
                pats.append(r'Dlvl:')
            i = p.expect(pats)
            log.append(clean(p.before) + clean(p.after if isinstance(p.after, str) else ''))
            if i == 0:
                verdict = 'DONE'
                try:  # let the final screen flush
                    p.expect([pexpect.TIMEOUT], timeout=0.3)
                    log.append(clean(p.before))
                except Exception:
                    pass
                break
            if i in (1, 2):
                verdict = 'FAIL'; break
            if i in (3, 5):
                p.send('\r')
            elif i == 4:
                p.send('y')
            elif i == 6:
                p.send(name + '\r')
            elif i == 7:
                p.send('.')
            elif i == 8:
                p.send('\x1b' if sent else '\r')
            elif i == 9:
                break
            elif i == 10 and not sent:
                p.send('\x1b#wizloadlua\r'); sent = True
    finally:
        p.terminate(force=True)
        os.remove(tmp)
    return verdict, ''.join(log)


src = open(script).read().replace('\r\n', '\n')
name = os.path.basename(script)
lines = []
tot = {k: 0 for k in KEYS}
for r in range(1, runs + 1):
    t0 = time.time()
    v, log = run_one(name, src)
    res = re.findall(r'RES:[^\s]*', log)
    seq = re.findall(r'SEQ:[ABTCXO]*', log)
    oth = re.findall(r'OTHER:[^\s]*', log)
    err = re.findall(r'(?:HARNESS|[Ll]ua error|rror:)[^\n]*', log)
    kc = {k: len(re.findall(pat, log)) for k, pat in KEYS.items()}
    for k in kc:
        tot[k] += kc[k]
    kcs = ' '.join(f'{k}={c}' for k, c in kc.items() if c)
    line = (f'{name} run={r} verdict={v} {res[-1] if res else "RES:none"} {seq[-1] if seq else "SEQ:none"} '
            f'{" ".join(oth)} {" ".join(err[:1])} msgs[{kcs}] t={time.time() - t0:.1f}s')
    print(line, flush=True)
    lines.append(line)
    if r == 1:
        lines.append('  first-run screen tail: ' + re.sub(r'\s+', ' ', log[-1200:]))
lines.append(f'{name} TOTAL msgs ' + ' '.join(f'{k}={c}' for k, c in tot.items()))
with open(out, 'a') as f:
    f.write('\n'.join(lines) + '\n' + '-' * 60 + '\n')
