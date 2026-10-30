"""Dump ordinary random NetHack 5.0.0 levels from the real headless tty build (for the paper's
"From a random NetHack level to ours" section).

Runs in WSL (venv ~/nh-witness/venv: pexpect, pyte). Each run is a fresh game in wizard mode (each new game draws a
fresh random seed; NetHack does not let us set it). Wizard mode is used only to LOOK at the level the normal level
generator made; nothing on the level is changed except that the hero drinks two detection potions:
  1. ^V level-teleport to dungeon level DLVL (default 3) -> a freshly generated ordinary level;
  2. ^F (wizard map): reveals the whole map and every trap;
  3. #terrain, wizard view "internal levl[][].typ codes": the exact terrain type of every cell;
  4. wish + quaff a blessed potion of object detection: every object (and gold) is shown; cursor over each one
     gives the game's own description (autodescribe);
  5. wish + quaff an uncursed potion of monster detection: same for monsters.
The map is not otherwise touched. Output: one JSON per level with the 21 map rows (screen columns 0..78 = map
x 1..79), the typ grid, and the traps / objects / monsters with the game's own descriptions.

Usage: python dump_random_levels.py <nethack binary> <hackdir> <out dir> [count=3] [dlvl=3]
"""
import json, os, re, sys, time
import pexpect, pyte

nh, hackdir, outdir = sys.argv[1:4]
COUNT = int(sys.argv[4]) if len(sys.argv) > 4 else 3
DLVL = int(sys.argv[5]) if len(sys.argv) > 5 else 3
ROWS, COLS = 24, 80
OPTS = ('role:valkyrie,race:human,gender:female,align:lawful,pettype:none,!autopickup,!timed_delay,'
        'number_pad:0,!legacy,!news,!splash_screen,!tutorial,!tips,boulder:0,color,autodescribe,!verbose,time')

screen = pyte.Screen(COLS, ROWS)
stream = pyte.ByteStream(screen)


def pump(p, settle=0.3, total=4.0):
    t_end, last = time.time() + total, time.time()
    while time.time() < t_end:
        try:
            stream.feed(p.read_nonblocking(65536, timeout=0.05))
            last = time.time()
        except pexpect.TIMEOUT:
            if time.time() - last > settle:
                return
        except pexpect.EOF:
            return


def text():
    return [screen.display[i] for i in range(ROWS)]


def alltext():
    return '\n'.join(text())


def more(p, n=10):
    msgs = []
    for _ in range(n):
        t = alltext()
        if '--More--' in t:
            msgs.append(text()[0].strip())
            p.send('\r'); pump(p)
        else:
            break
    return msgs


def map_cells():
    """screen rows 1..21 -> list of 21 lists of (char, fg, bold)"""
    out = []
    for y in range(1, 22):
        row = []
        for x in range(COLS - 1):
            c = screen.buffer[y][x]
            row.append((c.data, c.fg, bool(c.bold)))
        out.append(row)
    return out


def find_hero():
    for y in range(1, 22):
        x = screen.display[y].find('@')
        if x >= 0:
            return x, y - 1
    return None


def cursor_to(p, cur, tgt):
    """move the getpos cursor from cur to tgt (map coords: screen col, map row); return the top line"""
    dx, dy = tgt[0] - cur[0], tgt[1] - cur[1]
    keys = ''
    while abs(dx) >= 8:
        keys += 'L' if dx > 0 else 'H'; dx -= 8 if dx > 0 else -8
    while abs(dy) >= 8:
        keys += 'J' if dy > 0 else 'K'; dy -= 8 if dy > 0 else -8
    keys += ('l' if dx > 0 else 'h') * abs(dx) + ('j' if dy > 0 else 'k') * abs(dy)
    for k in keys:
        p.send(k)
    pump(p, 0.25)
    return text()[0].strip()


def describe(p, cells, hero):
    """we are in a getpos prompt starting on the hero: autodescribe each cell"""
    more(p)
    cur, out = hero, {}
    for c in cells:
        out[c] = cursor_to(p, cur, c)
        cur = c
    p.send('\x1b'); pump(p)
    more(p)
    return out


def wish(p, what):
    p.send('\x17'); pump(p)                    # ^W
    if 'wish' not in text()[0]:
        raise RuntimeError('no wish prompt:\n' + alltext())
    p.send(what + '\r'); pump(p, 0.5)
    t = text()[0]
    m = re.match(r'\s*([a-zA-Z]) - ', t)
    more(p)
    if not m:
        raise RuntimeError('wish failed: ' + t)
    return m.group(1)


def quaff(p, letter):
    p.send('q'); pump(p)
    if 'Drink from the fountain' in text()[0] or 'Drink from the sink' in text()[0]:
        p.send('n'); pump(p)
    p.send(letter); pump(p, 0.6)
    msgs = more(p)
    return msgs


SEEN_SYMS = set(")[%?/=!(*$0`&;:'")


def objects_and_mons(base, now, hero):
    """cells whose glyph differs from the plain map snapshot, plus monsters/objects the hero could already see
    (letters and object-class symbols on the snapshot itself)"""
    out = []
    for y in range(21):
        for x in range(COLS - 1):
            if (x, y) == hero:
                continue
            ch = now[y][x][0]
            if (ch != base[y][x][0] and ch != ' ') or ch.isalpha() or ch in SEEN_SYMS:
                out.append((x, y))
    return out


def one_level(idx):
    # wizard mode always plays as "wizard": clear a stale wizard save/lock so every run is a FRESH game
    for d in (hackdir, os.path.join(hackdir, 'save')):
        for f in os.listdir(d) if os.path.isdir(d) else []:
            if 'wizard' in f and os.path.isfile(os.path.join(d, f)):
                os.remove(os.path.join(d, f))
    env = dict(os.environ, NETHACKOPTIONS=OPTS, TERM='xterm', LINES=str(ROWS), COLUMNS=str(COLS))
    p = pexpect.spawn(nh, ['-D', '-u', 'randlev%d' % idx], env=env, cwd=hackdir, timeout=6, dimensions=(ROWS, COLS))
    log = []
    try:
        for _ in range(30):
            pump(p, 0.5)
            t = alltext()
            if '--More--' in t or 'Hit return' in t:
                p.send('\r')
            elif 'Dlvl:' in t:
                break
            elif 'Destroy old game' in t:
                p.send('y')
            elif '[ynq]' in t or '[yn]' in t:
                p.send('y')
        more(p)
        # 1. level teleport to a fresh ordinary level
        p.send('\x16'); pump(p)
        if 'level' not in text()[0]:
            raise RuntimeError('no level-teleport prompt:\n' + alltext())
        p.send(str(DLVL) + '\r'); pump(p, 0.8)
        log += more(p)
        status = [l for l in text() if 'Dlvl:' in l]
        # 2. wizard map
        p.send('\x06'); pump(p, 0.5)
        log += more(p)
        p.send('\x12'); pump(p)                # ^R redraw
        base = map_cells()
        hero = find_hero()
        # 3. exact terrain types
        p.send('#terrain\r'); pump(p, 0.5)
        menu = alltext()
        m = re.search(r'([a-z]) - internal levl', menu)
        if not m:
            raise RuntimeError('no typ option in #terrain menu:\n' + menu)
        p.send(m.group(1)); pump(p, 0.5)
        if 'internal levl' in alltext():       # some menus need a confirm
            p.send('\r'); pump(p, 0.5)
        typ_rows, pages = [], 0
        while pages < 6:
            pages += 1
            for line in text():
                s = line.rstrip()
                if len(s) >= 78 and re.fullmatch(r'[0-9a-zA-Z*!]+', s):
                    typ_rows.append(s)
            t = alltext()
            if '--More--' in t or '(end)' in t or re.search(r'\(\d+ of \d+\)', t):
                p.send('\r'); pump(p, 0.5)
                if '(end)' in t:
                    break
            else:
                break
        p.send('\x1b'); pump(p); more(p)
        p.send('\x12'); pump(p)
        if len(typ_rows) != 21:
            log.append('WARNING typ rows: %d' % len(typ_rows))
        # traps: '^' on the wizard map; describe via farlook
        traps = [(x, y) for y in range(21) for x in range(COLS - 1) if base[y][x][0] == '^']
        trap_desc = {}
        if traps:
            p.send(';'); pump(p)
            trap_desc = describe(p, traps, hero)
        # 4. objects
        letter = wish(p, 'blessed potion of object detection')
        p.send('\x12'); pump(p)
        base2 = map_cells()                    # potion now in pack, hero unmoved
        p.send('q'); pump(p)
        if 'Drink from' in text()[0]:
            p.send('n'); pump(p)
        p.send(letter); pump(p, 0.8)
        log += [text()[0].strip()]
        # browse_map getpos with autodescribe is now active (or a --More--)
        if '--More--' in alltext():
            more(p)
        objscr = map_cells()
        objs = objects_and_mons(base2, objscr, hero)
        obj_desc = describe(p, objs, hero) if objs else {}
        if not objs:
            p.send('\x1b'); pump(p)
        p.send('\x12'); pump(p)
        # 5. monsters
        letter = wish(p, 'uncursed potion of monster detection')
        p.send('\x12'); pump(p)
        base3 = map_cells()
        p.send('q'); pump(p)
        if 'Drink from' in text()[0]:
            p.send('n'); pump(p)
        p.send(letter); pump(p, 0.8)
        log += [text()[0].strip()]
        if '--More--' in alltext():
            more(p)
        monscr = map_cells()
        mons = [c for c in objects_and_mons(base3, monscr, hero)]
        mon_desc = describe(p, mons, hero) if mons else {}
        if not mons:
            p.send('\x1b'); pump(p)
        res = {
            'source': 'NetHack 5.0.0 (16ff591) headless tty, fresh game, wizard mode used only to view: '
                      '^V to Dlvl %d, ^F, #terrain typ codes, object + monster detection' % DLVL,
            'status': status,
            'hero': hero,
            'rows': [''.join(c[0] for c in r) for r in base],
            'colors': [[c[1] + ('+' if c[2] else '') for c in r] for r in base],
            'typ': typ_rows,
            'traps': [{'x': x, 'y': y, 'desc': trap_desc.get((x, y), '')} for (x, y) in traps],
            'objects': [{'x': x, 'y': y, 'ch': objscr[y][x][0], 'fg': objscr[y][x][1], 'desc': obj_desc.get((x, y), '')}
                        for (x, y) in objs],
            'monsters': [{'x': x, 'y': y, 'ch': monscr[y][x][0], 'fg': monscr[y][x][1], 'desc': mon_desc.get((x, y), '')}
                         for (x, y) in mons],
            'log': log,
        }
        return res
    finally:
        p.kill(9)          # SIGKILL: no hangup save is written
        p.close(force=True)


def main():
    os.makedirs(outdir, exist_ok=True)
    for i in range(1, COUNT + 1):
        try:
            r = one_level(i)
        except Exception as e:  # keep going; report
            print('level', i, 'failed:', e)
            continue
        path = os.path.join(outdir, 'random%d.json' % i)
        json.dump(r, open(path, 'w'), indent=1)
        print(path, r['status'], 'typ rows', len(r['typ']), 'traps', len(r['traps']), 'objects', len(r['objects']),
              'monsters', len(r['monsters']))


main()
