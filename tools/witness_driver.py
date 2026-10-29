"""Drive a wizard-mode NetHack (tty) through #wizloadlua for each witness script. Used by run_witnesses.sh."""
import glob, os, re, sys
import pexpect

nh, hackdir, wdir, out = sys.argv[1:5]
ANSI = re.compile(r'\x1b\[[0-9;?]*[A-Za-z]|\x1b[()][0-9A-Za-z]|\x1b[=>]')
OPTS = ('role:valkyrie,race:human,gender:female,align:neutral,pettype:none,!autopickup,'
        '!timed_delay,number_pad:0,!legacy,!news,!splash_screen,!tutorial')


def clean(t):
    return ANSI.sub('', t or '')


def run_one(path):
    name = os.path.basename(path)
    tmp = os.path.join(hackdir, name)
    src = open(path).read().replace('\r\n', '\n')
    open(tmp, 'w').write(src + '\nnh.pline("WITNESS DONE");\n')
    for f in glob.glob(os.path.join(hackdir, 'save', '*')) + glob.glob(os.path.join(hackdir, '*wizard*')):
        if os.path.isfile(f) and not f.endswith('.lua'):
            os.remove(f)          # no leftover save / lock from a previous run
    env = dict(os.environ, NETHACKOPTIONS=OPTS, TERM='xterm')
    p = pexpect.spawn(nh, ['-D', '-u', 'witness'], env=env, cwd=hackdir, encoding='latin-1',
                      timeout=6, dimensions=(30, 120))
    log, verdict, sent = [], 'ERROR', False
    try:
        for _ in range(120):
            i = p.expect([r'WITNESS DONE', r'(FAIL|HARNESS)[^\n]*', r'[Ll]ua error[^\n]*|rror:[^\n]*',
                          r'--More--', r'\[ynq?a?\]|\[yn\]', r'Hit return', r'[Ll]oad which lua file\?',
                          r'Dlvl:', pexpect.TIMEOUT, pexpect.EOF])
            log.append(clean(p.before) + clean(p.after if isinstance(p.after, str) else ''))
            if i == 0:
                verdict = 'PASS'; break
            if i in (1, 2):
                verdict = 'FAIL'; break
            if i == 3 or i == 5:
                p.send('\r')
            elif i == 4:
                p.send('y')
            elif i == 6:
                p.send(name + '\r')
            elif i == 7 and not sent:
                p.send('\x1b#wizloadlua\r'); sent = True
            elif i == 8:
                p.send('\x1b' if sent else '\r')
            elif i == 9:
                break
    finally:
        p.terminate(force=True)
        os.remove(tmp)
    return verdict, ''.join(log)[-3000:]


res = []
for f in sorted(glob.glob(os.path.join(wdir, '*.lua'))):
    v, log = run_one(f)
    print(v, os.path.basename(f), flush=True)
    res.append(f'{v}  {os.path.basename(f)}\n{log}\n' + '-' * 60)
open(out, 'w').write('\n'.join(res))
