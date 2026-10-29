"""R_game.py -- one headless wizard-mode NetHack 5.0.0 tty session (WSL build ~/nh-witness/install), reused for many
#wizloadlua scripts. Used by R_oracle.py (EXPTIME real-game differential brute force, proofs/exptime/R-realgame.md).

Game.run(src)   load a Lua script, page through every --More-- / text window, return the cleaned tty text that the
                script produced (scripts end with nh.text(... "BATCH END")).
Game.keys(k)    type raw keys into the tty (screen mode), wait until the screen is quiet; returns the message lines
                seen (including every --More-- page, each answered with RETURN).
Game.screen()   the pyte screen (list of strings).
"""
import os, re, time, glob
import pexpect, pyte

ROOT = os.path.expanduser('~/nh-witness/realgame')    # private HACKDIR copies h0..h7, hp (R_setup.sh)
OPTS = ('role:valkyrie,race:human,gender:female,align:neutral,pettype:none,!autopickup,'
        '!timed_delay,number_pad:0,!legacy,!news,!splash_screen,!tutorial,paranoid_confirmation:pray')
ANSI = re.compile(r'\x1b\[[0-9;?]*[A-Za-z]|\x1b[()][0-9A-Za-z]|\x1b[=>]')
ROWS, COLS = 60, 200


class LuaError(Exception):
    pass


class Game:
    def __init__(self, tag='0'):
        self.tag = tag
        self.name = 'R_q.lua'
        self.hack = os.path.join(ROOT, 'h' + tag)
        self.nh = os.path.join(self.hack, 'nethack')
        self.p = None
        self.restarts = 0

    def _feed(self, s):
        if s:
            self.stream.feed(s)

    def start(self):
        self.close()
        for f in glob.glob(os.path.join(self.hack, '*wizard*')) + glob.glob(os.path.join(self.hack, 'save', '*')) + \
                glob.glob(os.path.join(self.hack, '[0-9]*')):
            if os.path.isfile(f):
                os.remove(f)
        self.scr = pyte.Screen(COLS, ROWS)
        self.stream = pyte.Stream(self.scr)
        env = dict(os.environ, NETHACKOPTIONS=OPTS, TERM='xterm', HACKDIR=self.hack)
        self.p = pexpect.spawn(self.nh, ['-D', '-u', 'wizard'], env=env, cwd=self.hack, encoding='latin-1',
                               timeout=5, dimensions=(ROWS, COLS))
        for _ in range(60):
            i = self.p.expect([r'Dlvl:', r'--More--', r'\[ynq?a?\]|\[yn\]', r'Hit return', pexpect.TIMEOUT,
                               pexpect.EOF])
            self._feed(self.p.before); self._feed(self.p.after if isinstance(self.p.after, str) else '')
            if i == 0:
                break
            if i in (1, 3):
                self.p.send('\r')
            elif i == 2:
                self.p.send('n')   # never restore or keep anything
            elif i == 4:
                self.p.send('\r')
            else:
                raise RuntimeError('game exited during startup')
        self.quiet()
        self.p.send('\x1b')
        self.quiet()
        self.restarts += 1

    def quiet(self, t=0.05):
        """read until no output for t seconds"""
        while True:
            try:
                s = self.p.read_nonblocking(65536, timeout=t)
                self._feed(s)
            except pexpect.TIMEOUT:
                return
            except pexpect.EOF:
                raise

    def close(self):
        if self.p is not None:
            try:
                self.p.terminate(force=True)
            except Exception:
                pass
            self.p = None
        try:
            os.remove(os.path.join(self.hack, self.name))
        except OSError:
            pass

    def run(self, src, end='BATCH END', timeout=600):
        with open(os.path.join(self.hack, self.name), 'w', newline='\n') as f:
            f.write(src)
        self.p.send('#wizloadlua\r')
        log = []
        t0 = time.time()
        while True:
            i = self.p.expect([end, r'--More--', r'\(end\)', r'\(\d+ of \d+\)', r'[Ll]oad which lua file\?',
                               r'[Ll]ua error[^\n]*|LUAERR[^\n]*', r'\[ynq?a?\]|\[yn\]', pexpect.TIMEOUT,
                               pexpect.EOF], timeout=timeout)
            b = self.p.before or ''
            a = self.p.after if isinstance(self.p.after, str) else ''
            self._feed(b); self._feed(a)
            log.append(b + a)
            if i == 0:
                # answer only real prompts after the end marker (never a blind key: it would be a game command)
                for _ in range(20):
                    j = self.p.expect([r'--More--', r'\(end\)', r'\(\d+ of \d+\)', pexpect.TIMEOUT],
                                      timeout=0.15)
                    self._feed(self.p.before); self._feed(self.p.after if isinstance(self.p.after, str) else '')
                    log.append((self.p.before or '') + (self.p.after if isinstance(self.p.after, str) else ''))
                    if j == 3:
                        break
                    self.p.send('\r')
                self.quiet()
                break
            if i == 3:
                m = re.search(r'\((\d+) of (\d+)\)', a)
                # tty menu: '>' = next page; RETURN would close the whole menu
                self.p.send('>' if m and int(m.group(1)) < int(m.group(2)) else '\r')
            elif i in (1, 2):
                self.p.send('\r')
            elif i == 4:
                self.p.send(self.name + '\r')
            elif i == 5:
                txt = ANSI.sub(' ', ''.join(log))[-2000:]
                self.quiet(0.3)
                raise LuaError(txt)
            elif i == 6:
                self.p.send('y')
            elif i == 7:
                raise RuntimeError('timeout in run: ' + ANSI.sub(' ', ''.join(log))[-1500:])
            else:
                raise RuntimeError('EOF in run')
        return ANSI.sub('\n', ''.join(log)), time.time() - t0

    def keys(self, k, settle=0.08):
        """type k; answer --More-- with RETURN; return the list of top-line messages seen."""
        msgs = []
        self.p.send(k)
        for _ in range(30):
            try:
                i = self.p.expect([r'--More--', pexpect.TIMEOUT], timeout=settle)
            except pexpect.EOF:
                raise
            self._feed(self.p.before); self._feed(self.p.after if isinstance(self.p.after, str) else '')
            line = self.scr.display[0].rstrip()
            if i == 0:
                msgs.append(line.replace('--More--', '').strip())
                self.p.send('\r')
            else:
                if line.strip():
                    msgs.append(line.strip())
                break
        return msgs

    def screen(self):
        return list(self.scr.display)
