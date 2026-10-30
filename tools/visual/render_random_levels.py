"""Render the random levels dumped by dump_random_levels.py, and the step-by-step reduction of one of them to
our kind of level, as tile images (NetHack's own 16x16 tiles) and as text images (the game's ASCII symbols).

Every map cell comes from the dump: terrain from the game's own levl[][].typ codes, traps / objects / monsters
from the game's own descriptions. Buried and embedded objects are not drawn (a player cannot see them either).
The last step is the real demo instance b_puzzle (tools/visual/levels/b_puzzle.lua), the level of the paper's
"Play first" puzzle, which ran in the real game.

Usage (Windows or WSL Python with Pillow): python render_random_levels.py <dump dir> <win/share dir> <out img dir>
       [gallery ids, comma separated, default 1,2,3] [stepper id, default 3]
Prints a JSON summary (what each step removed) used for the alt texts and captions.
"""
import json, os, re, sys
from PIL import Image, ImageDraw, ImageFont

import tiles as T

ddir, share, out = sys.argv[1:4]
GAL = (sys.argv[4] if len(sys.argv) > 4 else '1,2,3').split(',')
STEP_ID = sys.argv[5] if len(sys.argv) > 5 else '3'
os.makedirs(out, exist_ok=True)
TILES = T.load_all(share)
FONTDIR = 'C:/Windows/Fonts' if os.name == 'nt' else '/mnt/c/Windows/Fonts'
FONT = ImageFont.truetype(f'{FONTDIR}/consola.ttf', 18)
CW, CH = 11, 20          # text cell
TS = 16                  # tile cell
BLACK = Image.new('RGB', (16, 16), (0, 0, 0))   # solid rock drawn black, as in the tty

PAL = {'default': (190, 190, 190), 'black': (90, 90, 230), 'red': (215, 60, 60), 'green': (70, 190, 70),
       'brown': (190, 130, 40), 'blue': (80, 120, 240), 'magenta': (200, 80, 200), 'cyan': (50, 190, 200),
       'white': (245, 245, 245), 'yellow': (240, 220, 60)}
GRAY, DIM = (170, 170, 170), (110, 110, 110)

WALL_T = {1: 'v', 2: 'h', 3: 'tlcorn', 4: 'trcorn', 5: 'blcorn', 6: 'brcorn', 7: 'cross wall', 8: 'tuwall',
          9: 'tdwall', 10: 'tlwall', 11: 'trwall'}
WALL_CH = {1: '|', 2: '-', 3: '-', 4: '-', 5: '-', 6: '-', 7: '-', 8: '-', 9: '-', 10: '|', 11: '|'}


def wall_tile(k):
    return {'v': 'main walls vertical', 'h': 'main walls horizontal'}.get(k, 'main walls ' + k)


def typ_code(c):
    if c in '*!':
        return 0
    if c.isdigit():
        return int(c)
    if 'a' <= c <= 'z':
        return ord(c) - ord('a') + 10
    return ord(c) - ord('A') + 36


# ---------- tile lookup for objects and monsters ----------
OBJ_TILES, MON_TILES = {}, {}
for n in T.load(f'{share}/objects.txt'):
    OBJ_TILES.setdefault(n, n)
    if ' / ' in n:
        a, b = n.split(' / ', 1)
        OBJ_TILES.setdefault(b, n)
        OBJ_TILES.setdefault(a, n)
for n in T.load(f'{share}/monsters.txt'):
    MON_TILES.setdefault(n.split(',')[0], n)
GENERIC = {'potion': 'potion / generic potion', 'wand': 'wand / generic wand', 'ring': 'ring / generic ring',
           'gem': 'gem / generic gem', 'spellbook': 'spellbook / generic spellbook',
           'amulet': 'amulet / generic amulet'}


def mon_name(desc):
    d = desc.replace('peaceful ', '').replace('tame ', '')
    d = d.split(', mimicking')[0].split(' - ')[0].split(' called ')[0].strip()
    if d in MON_TILES:
        return d
    if desc.startswith('peaceful ') and d[:1].isupper():
        return 'shopkeeper' if 'priest' not in d else 'aligned cleric'
    return d


def mon_tile(desc):
    n = mon_name(desc)
    return TILES.get(MON_TILES.get(n, ''), None)


def obj_tile(desc, ch):
    d = re.sub(r'^(a|an|some|the|\d+)\s+', '', desc).strip()
    m = re.match(r'statue of (a |an )?(.*)', d)
    if m:
        t = mon_tile(m.group(2))
        return t.convert('L').convert('RGB') if t else TILES['statue']
    for word, g in GENERIC.items():
        if d.endswith(' ' + word) or d == word:
            return TILES.get(g) or TILES['stone']
    m = re.match(r'scroll labeled (.*)', d)
    if m and m.group(1) in OBJ_TILES:
        return TILES[OBJ_TILES[m.group(1)]]
    for cand in (d, d[:-1], d.replace('pieces', 'piece'), re.sub(r'(\w+)s\b', r'\1', d, count=1)):
        if cand in OBJ_TILES:
            return TILES[OBJ_TILES[cand]]
    fb = {'$': 'gold piece', '0': 'boulder', '?': 'scroll / generic scroll', '!': 'potion / generic potion',
          '/': 'wand / generic wand', '=': 'ring / generic ring', '*': 'gem / generic gem', '%': 'food ration',
          ')': 'dagger', '[': 'leather armor', '(': 'large box', '+': 'spellbook / generic spellbook',
          '"': 'amulet / generic amulet'}.get(ch)
    return TILES.get(OBJ_TILES.get(fb, fb)) if fb else None


def is_monster_desc(desc):
    return bool(desc) and not re.match(r'^(a|an|some|the|\d+)\s', desc)


# ---------- level model ----------
def load_level(path):
    d = json.load(open(path))
    H, Wd = 21, 79
    typ = [[typ_code(r[x]) if x < len(r) else 0 for x in range(Wd)] for r in d['typ']]
    rows = [r.ljust(Wd) for r in d['rows']]
    cells = {}
    for y in range(H):
        for x in range(Wd):
            t, ch = typ[y][x], rows[y][x]
            if t in WALL_T:
                cells[(x, y)] = ('wall', wall_tile(WALL_T[t]), WALL_CH[t], GRAY)
            elif t == 14:     # secret door: looks like wall
                cells[(x, y)] = ('wall', wall_tile('v' if ch == '|' else 'h'), '|' if ch == '|' else '-', GRAY)
            elif t == 23:
                horiz = typ[y][x - 1] in WALL_T or typ[y][x + 1] in WALL_T
                if ch == '+':
                    cells[(x, y)] = ('door', ('horizontal' if horiz else 'vertical') + ' closed door', '+', PAL['brown'])
                elif ch == '|':
                    cells[(x, y)] = ('door', 'horizontal open door', '|', PAL['brown'])
                elif ch == '-':
                    cells[(x, y)] = ('door', 'vertical open door', '-', PAL['brown'])
                else:
                    cells[(x, y)] = ('door', 'no door', '.', GRAY)
            elif t == 24:
                cells[(x, y)] = ('corr', 'corridor', '#', GRAY)
            elif t == 25:
                cells[(x, y)] = ('floor', 'floor of a room', '.', GRAY)
            elif t == 26:
                up = ch == '<'
                cells[(x, y)] = ('stairs', 'staircase up' if up else 'staircase down', '<' if up else '>', GRAY)
            elif t == 28:
                cells[(x, y)] = ('furn', 'fountain', '{', PAL['blue'])
            elif t == 29:
                cells[(x, y)] = ('furn', 'throne', '\\', PAL['yellow'])
            elif t == 30:
                cells[(x, y)] = ('furn', 'sink', '#', GRAY)
            elif t == 31:
                cells[(x, y)] = ('furn', 'grave', '|', GRAY)
            elif t == 32:
                cells[(x, y)] = ('furn', 'unaligned altar', '_', GRAY)
            elif t in (16, 17, 18):
                cells[(x, y)] = ('water', 'water', '}', PAL['blue'])
            elif t == 20:
                cells[(x, y)] = ('lava', 'molten lava', '}', PAL['red'])
            elif t == 13:
                cells[(x, y)] = ('tree', 'tree', '#', PAL['green'])
            elif t == 22:
                cells[(x, y)] = ('wall', 'iron bars', '#', PAL['cyan'])
    traps = {}
    for t in d['traps']:
        name = t['desc'].replace('trap door', 'trap door')
        name = re.sub(r'^(a |an )', '', name)
        m = re.search(r'\((.*)\)', name)
        if m:
            name = m.group(1)
        col = d['colors'][t['y']][t['x']]
        traps[(t['x'], t['y'])] = (name, PAL.get(col.rstrip('+'), GRAY))
    objs, mons = {}, {}
    for o in d['objects']:
        if 'buried' in o['desc'] or 'embedded' in o['desc'] or not o['desc']:
            continue
        if is_monster_desc(o['desc']):
            continue
        objs[(o['x'], o['y'])] = (o['desc'], o['ch'], PAL.get(o['fg'], GRAY))
    for m in d['monsters']:
        if is_monster_desc(m['desc']):
            mons[(m['x'], m['y'])] = (m['desc'], m['ch'], PAL.get(m['fg'], GRAY))
    hero = tuple(d['hero'])
    return dict(cells=cells, traps=traps, objs=objs, mons=mons, hero=hero, raw=d)


def bbox(L, margin=1):
    xs = [x for (x, y) in L['cells']]
    ys = [y for (x, y) in L['cells']]
    return max(0, min(xs) - margin), max(0, min(ys) - margin), min(78, max(xs) + margin), min(20, max(ys) + margin)


def draw(L, box, path_base, marks=(), extra=None, labels=None, scale=1):
    """extra: {(x,y): (kind, tile, ch, col)} drawn over terrain (pockets etc.)"""
    x0, y0, x1, y1 = box
    w, h = x1 - x0 + 1, y1 - y0 + 1
    ts = TS * scale
    ti = Image.new('RGB', (w * ts, h * ts), (0, 0, 0))
    tx = Image.new('RGB', (w * CW * scale, h * CH * scale), (0, 0, 0))
    dt, dx = ImageDraw.Draw(ti), ImageDraw.Draw(tx)
    font = FONT if scale == 1 else ImageFont.truetype(f'{FONTDIR}/consola.ttf', 18 * scale)
    cells = dict(L['cells'])
    if extra:
        cells.update(extra)
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            px, py = (x - x0) * ts, (y - y0) * ts
            qx, qy = (x - x0) * CW * scale, (y - y0) * CH * scale
            c = cells.get((x, y))
            base = TILES[c[1]] if c else BLACK
            ti.paste(base.resize((ts, ts), Image.NEAREST), (px, py))
            ch, col = (c[2], c[3]) if c else (' ', GRAY)
            if (x, y) in L['traps']:
                n, tc = L['traps'][(x, y)]
                t = TILES.get(n)
                if t:
                    ti.paste(t.resize((ts, ts), Image.NEAREST), (px, py))
                ch, col = '^', tc
            ov = None
            if (x, y) in L['objs']:
                desc, och, ocol = L['objs'][(x, y)]
                ov = obj_tile(desc, och)
                ch, col = och, ocol
            if (x, y) in L['mons']:
                desc, mch, mcol = L['mons'][(x, y)]
                ov = mon_tile(desc) or ov
                ch, col = mch, mcol
            if L['hero'] and (x, y) == L['hero']:
                ov = TILES['valkyrie,female']
                ch, col = '@', PAL['white']
            if ov is not None:
                ti.paste(ov.resize((ts, ts), Image.NEAREST), (px, py))
            if ch != ' ':
                dx.text((qx + CW * scale / 2, qy + CH * scale / 2), ch, font=font, fill=col, anchor='mm')
    gold = (242, 207, 74)
    for (x, y), lab in (labels or {}).items():
        for img, d, cw, chh in ((ti, dt, ts, ts), (tx, dx, CW * scale, CH * scale)):
            px, py = (x - x0) * cw, (y - y0) * chh
            d.rectangle([px, py, px + cw - 1, py + chh - 1], outline=gold, width=2)
    for (x, y) in marks:
        for d, cw, chh in ((dt, ts, ts), (dx, CW * scale, CH * scale)):
            px, py = (x - x0) * cw, (y - y0) * chh
            d.rectangle([px - 2, py - 2, px + cw + 1, py + chh + 1], outline=(255, 70, 70), width=2)
    ti.save(path_base + '-tiles.webp', lossless=True, quality=100, method=6)
    tx.save(path_base + '-text.webp', lossless=True, quality=100, method=6)
    return ti.size, tx.size


def find_pocket(L, box, avoid=()):
    """centre of a 5x5 all-stone window inside the box (so a 3x3 walled pocket touches nothing)"""
    x0, y0, x1, y1 = box
    best = None
    for y in range(y0 + 2, y1 - 1):
        for x in range(x0 + 2, x1 - 1):
            if all((x + i, y + j) not in L['cells'] for i in range(-2, 3) for j in range(-2, 3)) and \
                    all(abs(x - a) > 4 or abs(y - b) > 4 for a, b in avoid):
                score = abs(y - (y0 + y1) / 2) * 0 + (x - x0)    # leftmost
                if best is None or score < best[0]:
                    best = (score, (x, y))
    return best[1] if best else None


def pocket(cx, cy, centre):
    e = {}
    for (i, j, k, chh) in ((-1, -1, 'tlcorn', '-'), (0, -1, 'h', '-'), (1, -1, 'trcorn', '-'), (-1, 0, 'v', '|'),
                           (1, 0, 'v', '|'), (-1, 1, 'blcorn', '-'), (0, 1, 'h', '-'), (1, 1, 'brcorn', '-')):
        e[(cx + i, cy + j)] = ('wall', wall_tile(k), chh, GRAY)
    e[(cx, cy)] = centre
    return e


summary = {'gallery': {}, 'steps': []}

# ---------- gallery ----------
for gid in GAL:
    L = load_level(os.path.join(ddir, f'random{gid}.json'))
    box = bbox(L)
    s = draw(L, box, os.path.join(out, f'rand{gid}'))
    kinds = {}
    for c in L['cells'].values():
        kinds[c[1]] = kinds.get(c[1], 0) + 1
    summary['gallery'][gid] = dict(size=s, box=box, traps=[v[0] for v in L['traps'].values()],
                                   monsters=[v[0] for v in L['mons'].values()],
                                   objects=[v[0] for v in L['objs'].values()],
                                   furniture={k: v for k, v in kinds.items() if k in (
                                       'fountain', 'sink', 'throne', 'unaligned altar', 'grave', 'staircase up',
                                       'staircase down')},
                                   hidden=len([o for o in L['raw']['objects'] if 'buried' in o['desc'] or 'embedded' in o['desc']]))

# ---------- stepper ----------
L = load_level(os.path.join(ddir, f'random{STEP_ID}.json'))
box = bbox(L)
steps = []


def step(name, marks):
    i = len(steps)
    draw(L, box, os.path.join(out, f'step{i}'), marks=marks, extra=EXTRA)
    steps.append(dict(name=name, removed=len(marks)))


EXTRA = {}
step('as generated', [])
m = list(L['mons']); L['mons'] = {}; step('monsters', m)
m = list(L['objs']); L['objs'] = {}; step('objects', m)
m = [k for k, c in L['cells'].items() if c[0] == 'furn']
for k in m:
    L['cells'][k] = ('floor', 'floor of a room', '.', GRAY)
step('furniture', m)
m = [k for k, v in L['traps'].items() if v[0] not in ('pit', 'hole', 'trap door')]
for k in m:
    del L['traps'][k]
step('traps', m)
m = [k for k, c in L['cells'].items() if c[0] == 'stairs']
for k in m:
    L['cells'][k] = ('floor', 'floor of a room', '.', GRAY)
sp = find_pocket(L, box)
EXTRA.update(pocket(sp[0], sp[1], ('stairs', 'branch staircase up', '<', GRAY)))
step('stairs', m)
step('hero', [L['hero']])
step('hunger', [])
pp = find_pocket({**L, 'cells': {**L['cells'], **EXTRA}}, box, avoid=[sp])
EXTRA.update(pocket(pp[0], pp[1], ('trap', 'pit', '^', GRAY)))
step('sokoban', [pp])
summary['steps'] = steps
summary['step_box'] = box
summary['pockets'] = {'stairs': sp, 'pit': pp}

# ---------- final: the real instance b_puzzle ----------
lua = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'levels', 'b_puzzle.lua')).read()
mp = re.search(r'map = \[\[\n(.*?)\]\]', lua, re.S).group(1).split('\n')
mp = [r for r in mp if r != '']
Wd, H = max(len(r) for r in mp), len(mp)
mp = [r.ljust(Wd) for r in mp]
floor = {(x, y) for y in range(H) for x in range(Wd) if mp[y][x] == '.'}


def solid(x, y):
    return (x, y) not in floor


def wkey(x, y):
    def near(a, b):
        return any((a + i, b + j) in floor for i in (-1, 0, 1) for j in (-1, 0, 1) if i or j)
    if not near(x, y):
        return None
    def w(a, b):
        return 0 <= a < Wd and 0 <= b < H and solid(a, b) and near(a, b)
    N, S, E, Wd_ = w(x, y - 1), w(x, y + 1), w(x + 1, y), w(x - 1, y)
    n = N + S + E + Wd_
    if n == 4: return 'cross wall'
    if n == 3: return 'tdwall' if not N else 'tuwall' if not S else 'tlwall' if not E else 'trwall'
    if N and S: return 'v'
    if E and Wd_: return 'h'
    if S and E: return 'tlcorn'
    if S and Wd_: return 'trcorn'
    if N and E: return 'blcorn'
    if N and Wd_: return 'brcorn'
    return 'v' if (N or S) else 'h'


F = dict(cells={}, traps={}, objs={}, mons={}, hero=(1, 2))
for y in range(H):
    for x in range(Wd):
        if (x, y) in floor:
            F['cells'][(x, y)] = ('floor', 'floor of a room', '.', GRAY)
        else:
            k = wkey(x, y)
            if k:
                F['cells'][(x, y)] = ('wall', wall_tile(k), '|' if k in ('v', 'tlwall', 'trwall') else '-', GRAY)
for b in re.findall(r'des\.object\("boulder", (\d+), (\d+)\)', lua):
    F['objs'][(int(b[0]), int(b[1]))] = ('a boulder', '0', GRAY)
for t in re.findall(r'des\.trap\("pit", (\d+), (\d+)\)', lua):
    F['traps'][(int(t[0]), int(t[1]))] = ('pit', GRAY)
F['cells'][(11, 1)] = ('stairs', 'branch staircase up', '<', GRAY)   # levregion branch: the sealed pocket
sz = draw(F, (0, 0, Wd - 1, H - 1), os.path.join(out, f'step{len(steps)}'), labels={(6, 2): 'g'}, scale=3)
steps.append(dict(name='instance b_puzzle', size=sz))
print(json.dumps(summary, indent=1, default=str))
