"""Play the demo scenes in the real headless NetHack 5.0.0 tty and record every screen.

Runs in WSL (venv ~/nh-witness/venv: pexpect, pyte). One game, wizard mode only to load each level with
#wizloadlua (the level scripts in levels/ build the board; they press no keys). All moves are typed into the tty
exactly like a player would type them; after each key the terminal output is fed to a pyte VT100 screen and the
whole 24x80 screen is stored. render.py later turns the map part into NetHack tile images.

Usage: python capture.py <nethack binary> <hackdir> <levels dir> <out frames.json>
"""
import glob, json, os, sys, time
import pexpect, pyte

from scenes import SCENES

nh, hackdir, ldir, out = sys.argv[1:5]
ROWS, COLS = 24, 80
OPTS = ('role:valkyrie,race:human,gender:female,align:lawful,pettype:none,!autopickup,!timed_delay,'
        'number_pad:0,!legacy,!news,!splash_screen,!tutorial,symset:DECgraphics,boulder:0,'
        '!verbose,time,showexp')

screen = pyte.Screen(COLS, ROWS)
stream = pyte.ByteStream(screen)


def pump(p, settle=0.35, total=4.0):
    """read until the terminal is quiet for `settle` seconds"""
    t_end = time.time() + total
    last = time.time()
    while time.time() < t_end:
        try:
            data = p.read_nonblocking(65536, timeout=0.05)
            stream.feed(data)
            last = time.time()
        except pexpect.TIMEOUT:
            if time.time() - last > settle:
                return
        except pexpect.EOF:
            return


def text():
    return [screen.display[i] for i in range(ROWS)]


def find_hero():
    for y in range(1, 22):
        x = screen.display[y].find('@')
        if x >= 0:
            return x, y
    return None


def snap(frames, **kw):
    f = dict(rows=text(), cursor=[screen.cursor.x, screen.cursor.y])
    f.update(kw)
    frames.append(f)


def clear_more(p, frames, scene, label):
    """--More-- prompts: keep a frame showing the message, then acknowledge"""
    for _ in range(8):
        if '--More--' in ''.join(text()):
            snap(frames, scene=scene, label=label, more=True)
            p.send('\r'); pump(p)
        else:
            return


def load_level(p, name):
    src = open(os.path.join(ldir, name + '.lua')).read().replace('\r\n', '\n')
    tmp = os.path.join(hackdir, 'vis_' + name + '.lua')
    open(tmp, 'w').write(src)
    p.send('\x1b'); pump(p, 0.2)
    p.send('#wizloadlua\r'); pump(p)
    if 'lua file' not in ''.join(text()):
        raise RuntimeError('no lua prompt:\n' + '\n'.join(text()))
    p.send('vis_' + name + '.lua\r'); pump(p, 0.6)
    for _ in range(5):
        if '--More--' in ''.join(text()):
            p.send('\r'); pump(p)
    p.send('\x12'); pump(p)     # ^R redraw
    os.remove(tmp)


def main():
    for f in glob.glob(os.path.join(hackdir, 'save', '*')) + glob.glob(os.path.join(hackdir, '*visual*')):
        if os.path.isfile(f):
            os.remove(f)
    env = dict(os.environ, NETHACKOPTIONS=OPTS, TERM='xterm', LINES=str(ROWS), COLUMNS=str(COLS))
    p = pexpect.spawn(nh, ['-D', '-u', 'visual'], env=env, cwd=hackdir, timeout=6, dimensions=(ROWS, COLS))
    frames, log = [], []
    try:
        for _ in range(30):          # get through the intro to the map
            pump(p, 0.5)
            t = ''.join(text())
            if '--More--' in t or 'Hit return' in t:
                p.send('\r')
            elif 'Dlvl:' in t:
                break
            elif '[ynq]' in t or '[yn]' in t:
                p.send('y')
        for sc in SCENES:
            for attempt in range(6):
                load_level(p, sc['level'])
                hero = find_hero()
                # the expected start: first '@' of the board text, or the START label, at screen (x-1, y+1)
                if hero == tuple(sc['expect_screen']):
                    break
                log.append(f"{sc['id']}: hero at {hero}, expected {sc['expect_screen']}, retry")
            else:
                raise RuntimeError(f"{sc['id']}: hero never on the start cell")
            snap(frames, scene=sc['id'], label='start', key=None)
            for step in sc['keys']:
                k, label = step
                p.send(k); pump(p)
                snap(frames, scene=sc['id'], label=label, key=k)
                clear_more(p, frames, sc['id'], label)
                if '--More--' in ''.join(text()):
                    raise RuntimeError('stuck on More')
            snap(frames, scene=sc['id'], label='end', key=None)
            log.append(f"{sc['id']}: ok, hero ends at {find_hero()}")
    finally:
        log.append('final screen:\n' + '\n'.join(text()))
        p.terminate(force=True)
        json.dump({'frames': frames, 'log': log, 'options': OPTS}, open(out, 'w'), indent=0)
        print('\n'.join(log))


main()
