#!/usr/bin/env python3
"""L_lua.py -- review 6 F5: emit the instance script S (spec Rev. 1-4 whitelist) for a WINDOW of a generated level and
lint it against the whitelist.

The full level is not emitted: the machinery boards on the check path are not placed (M-machinery.md, L-generator.md
§7.1), so the goal g (end of the check path) has no cell yet, and the main layer alone of the smallest instance is
~40k x 7k cells. The window is the tile row (macro row 0) from the start junction tile to the coin tile, cut out of
the concretely generated main layer; corridors leaving the window end at its border (dead ends). Everything the
spec asks of the instance proper is emitted and linted: level flags, level_init, explicit map, boulders with explicit
curse state, the coin's teleport trap(s) `seen = true`, the sentinel pit, the sealed branch pocket P with its
`levregion`, exactly one 1-cell `teleport_region` on s with the coin zone Z as `exclude`, the inventory and the
debug flags.

Usage: python L_lua.py [SEED K]   (default: seed 3, instance 0 = inst3_0 of `L_gen.py --run 20 3`)
Writes build/lgen/lua/inst<seed>_<k>_window.lua and prints the lint result.
"""
import os, random, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import L_gen as L

PREFIX_FLAGS = ('noflip', 'sokoban', 'hardfloor', 'solidify')
ALLOWED = {'des.level_init', 'des.level_flags', 'des.map', 'des.object', 'des.trap', 'des.levregion',
           'des.teleport_region', 'des.non_diggable', 'des.non_passwall', 'u.clear_inventory', 'u.giveobj',
           'obj.new', 'nh.debug_flags', 'des.region'}


def window(seed, k):
    rng = random.Random(seed)
    for _ in range(k + 1):
        inst = L.random_instance(rng)
    N = L.netlist(inst); L.contract(N)
    Bs = L.Bus(N); Bs.order(); Bs.rows()
    Lv = L.Level(Bs); Lv.blocks()
    coin = [tn for tn, T in Bs.tiles.items() if T['kind'] == 'coin']
    assert coin, 'instance has no coin (n_Y = 0); pick another'
    st = Bs.start_tile
    cols = [Lv.tile_at[st], Lv.tile_at[coin[0]]]
    c0 = min(cols)
    c1 = max(Lv.tile_at[tn] + len(Bs.tiles[tn]['ports']) - 1 for tn in (st, coin[0]))
    P = L.P
    floor = {}
    for (c, r), key in Lv.g.items():
        if r != 0 or not (c0 <= c <= c1) or key[0] != 'tile' or key[2] != 0:
            continue
        b = Lv.tb[key[1]]
        ox = (c - c0) * P
        for (x, y), ch in b.floor.items():
            floor[(ox + x, y)] = ch
    sb, cb = Lv.tb[st], Lv.tb[coin[0]]
    s = ((Lv.tile_at[st] - c0) * P + sb.jn_cell[0], sb.jn_cell[1])
    off = (Lv.tile_at[coin[0]] - c0) * P
    cz = {k2: (off + v[0], off * 0 + v[1]) for k2, v in cb.coin.items()}
    W = (c1 - c0 + 1) * P
    return dict(floor=floor, s=s, coin=cz, W=W, H=P, inst=inst, cols=(c0, c1))


def emit(win):
    """returns (lua text, meta). Map placed at absolute (1, 0): absolute = map-relative + (1, 0) (column 0 unused)."""
    fl, W, H = win['floor'], win['W'], win['H']
    Wm, Hm = W + 6, H                           # 6 extra columns on the right: sentinel pit + sealed pocket P
    pit = (W + 1, 2)
    pocket = (W + 4, 2)
    rows = []
    for y in range(Hm):
        r = []
        for x in range(Wm):
            r.append('.' if (x, y) in fl or (x, y) in (pit, pocket) else '-')
        rows.append(''.join(r))
    A = lambda c: (c[0] + 1, c[1])
    cz = win['coin']
    Z = (A(cz['A'])[0], A(cz['T'])[1], A(cz['B'])[0], A(cz['T'])[1])
    s = A(win['s'])
    out = ['-- L_OFF^{W+C} instance script S (window of a generated level; L_lua.py). Harness H wraps it:',
           '-- des.reset_level(); S; des.finalize_level()  (spec Rev. 1 item 1). No loops, no functions.',
           'nh.debug_flags({ mongen = false, hunger = false });',
           'des.level_init({ style = "solidfill", fg = " ", lit = true });',
           'des.level_flags(' + ', '.join(f'"{f}"' for f in PREFIX_FLAGS) + ');',
           'des.map({ x = 1, y = 0, map = [[',
           *rows,
           ']] });']
    for (x, y), ch in sorted(fl.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        if ch == '0':
            ax, ay = A((x, y))
            out.append(f'des.object({{ id = "boulder", x = {ax}, y = {ay}, buc = "uncursed" }});')
    for (x, y), ch in sorted(fl.items()):
        if ch == 'T':
            ax, ay = A((x, y))
            out.append(f'des.trap({{ type = "teleport", coord = {{ {ax}, {ay} }}, seen = true }});')
    ax, ay = A(pit)
    out.append(f'des.trap("pit", {ax}, {ay});                 -- sentinel')
    px, py = A(pocket)
    out.append(f'des.levregion({{ region = {{ {px}, {py}, {px}, {py} }}, region_islev = true, type = "branch" }});')
    out.append(f'des.teleport_region({{ region = {{ {s[0]}, {s[1]}, {s[0]}, {s[1]} }}, region_islev = true, '
               f'exclude = {{ {Z[0]}, {Z[1]}, {Z[2]}, {Z[3]} }}, exclude_islev = true, dir = "both" }});')
    out += ['u.clear_inventory();', 'u.giveobj(obj.new("cursed loadstone"));',
            'u.giveobj(obj.new("cursed +0 fumble boots"));']
    return '\n'.join(out) + '\n', dict(s=s, Z=Z, pocket=A(pocket), pit=A(pit), W=Wm, H=Hm)


def lint(text):
    """independent re-parse of the script against spec Rev. 1-4 (no use of the generator's data)."""
    errs = []
    m = re.search(r'des\.map\(\{ x = (\d+), y = (\d+), map = \[\[\n(.*?)\n\]\] \}\);', text, re.S)
    mx, my = int(m.group(1)), int(m.group(2))
    rows = m.group(3).split('\n')
    if len({len(r) for r in rows}) != 1:
        errs.append('map not rectangular')
    if mx < 1:
        errs.append('map column 0 used')
    fl = {(x + mx, y + my) for y, r in enumerate(rows) for x, ch in enumerate(r) if ch == '.'}
    body = text[:m.start()] + text[m.end():]
    code = '\n'.join(l.split('--')[0] for l in body.split('\n'))
    for kw in ('for ', 'while ', 'function', 'repeat', 'goto', 'local '):
        if kw in code:
            errs.append(f'control flow / local: {kw.strip()}')
    calls = re.findall(r'([a-z]+\.[a-z_]+)\(', code)
    bad = sorted(set(calls) - ALLOWED)
    if bad:
        errs.append(f'calls outside the whitelist: {bad}')
    fl_line = re.search(r'des\.level_flags\(([^)]*)\)', code).group(1)
    flags = re.findall(r'"(\w+)"', fl_line)
    if 'noteleport' in flags:
        errs.append('noteleport forbidden (Rev. 4 10a)')
    for f in PREFIX_FLAGS:
        if f not in flags:
            errs.append(f'missing level flag {f}')
    if not re.search(r'nh\.debug_flags\(\{ mongen = false, hunger = false \}\)', code):
        errs.append('mandatory debug flags missing')
    for need in ('u.clear_inventory()', 'obj.new("cursed loadstone")', 'obj.new("cursed +0 fumble boots")'):
        if need not in code:
            errs.append(f'missing {need}')
    if len(re.findall(r'u\.giveobj', code)) != 2:
        errs.append('inventory must be exactly {cursed loadstone, cursed fumble boots}')
    tr = re.findall(r'des\.teleport_region\(\{ region = \{ (\d+), (\d+), (\d+), (\d+) \}, region_islev = true, '
                    r'exclude = \{ (\d+), (\d+), (\d+), (\d+) \}, exclude_islev = true, dir = "both" \}\)', code)
    if len(tr) != 1 or code.count('des.teleport_region') != 1:
        errs.append('exactly one teleport_region with exclude required (Rev. 4 10c)')
        return errs, {}
    sx1, sy1, sx2, sy2, zx1, zy1, zx2, zy2 = map(int, tr[0])
    inZ = lambda c: zx1 <= c[0] <= zx2 and zy1 <= c[1] <= zy2
    s = (sx1, sy1)
    if (sx1, sy1) != (sx2, sy2):
        errs.append('teleport_region is not one cell')
    if zx1 < 1:
        errs.append('zx1 < 1')
    if inZ(s):
        errs.append('s in Z')
    if s not in fl:
        errs.append('s is not floor')
    lr = re.findall(r'des\.levregion\(\{ region = \{ (\d+), (\d+), (\d+), (\d+) \}, region_islev = true, '
                    r'type = "branch" \}\)', code)
    if len(lr) != 1:
        errs.append('exactly one branch levregion required (Rev. 3 item 8)')
    else:
        p = tuple(map(int, lr[0][:2]))
        if inZ(p):
            errs.append('P in Z')
        if p not in fl or any((p[0] + dx, p[1] + dy) in fl for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy):
            errs.append('pocket P not a sealed 1-cell floor pocket')
    tele = [tuple(map(int, t)) for t in re.findall(r'des\.trap\(\{ type = "teleport", coord = \{ (\d+), (\d+) \}, '
                                                    r'seen = true \}\)', code)]
    if code.count('type = "teleport"') != len(tele):
        errs.append('teleport trap without seen = true / with other keys')
    if 'teledest' in code or 'launchfrom' in code:
        errs.append('teledest / launchfrom forbidden')
    for t in tele:
        if not inZ(t):
            errs.append(f'teleport trap {t} outside Z')
        if t not in fl:
            errs.append(f'teleport trap {t} not on floor')
    other = re.findall(r'des\.trap\("(\w+)"', code)
    if any(t not in ('pit', 'hole', 'trapdoor') for t in other):
        errs.append(f'trap types outside the whitelist: {other}')
    objs = re.findall(r'des\.object\(([^;]*)\);', code)
    nb = 0
    for o in objs:
        mm = re.fullmatch(r'\{ id = "boulder", x = (\d+), y = (\d+), buc = "(uncursed|cursed|blessed)" \}\)?', o.strip())
        if not mm:
            errs.append(f'object without explicit otyp / coordinates / curse state: {o[:60]}')
            continue
        c = (int(mm.group(1)), int(mm.group(2)))
        nb += 1
        if c not in fl or c == s or inZ(c):
            errs.append(f'boulder {c} not on a free floor cell outside Z and s')
    if s in tele:
        errs.append('trap on s')
    return errs, dict(boulders=nb, teleport_traps=len(tele), s=s, Z=(zx1, zy1, zx2, zy2), floor=len(fl),
                      map_wh=(len(rows[0]), len(rows)))


if __name__ == '__main__':
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    k = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    win = window(seed, k)
    text, meta = emit(win)
    os.makedirs(os.path.join(L.OUT, 'lua'), exist_ok=True)
    path = os.path.join(L.OUT, 'lua', f'inst{seed}_{k}_window.lua')
    open(path, 'w').write(text)
    errs, info = lint(text)
    print(f'instance {seed}_{k}: window macro columns {win["cols"]} of row 0 (start tile .. coin tile), '
          f'{len(text) / 1e6:.1f} MB -> {os.path.relpath(path, L.ROOT)}')
    print('lint:', info)
    # negative controls: the linter must reject broken variants
    bad = {'noteleport': text.replace('"noflip"', '"noteleport", "noflip"'),
           'second teleport_region': text + 'des.teleport_region({ region = { 1, 1, 1, 1 } });\n',
           'trap unseen': text.replace('seen = true', 'seen = false', 1),
           'boulder BUC implicit': text.replace(', buc = "uncursed"', '', 1),
           'loop': text + 'for i = 1, 2 do end\n',
           'no pocket': re.sub(r'des\.levregion\([^\n]*\n', '', text)}
    caught = {n: bool(lint(t)[0]) for n, t in bad.items()}
    print('negative controls caught:', caught)
    ok = not errs and all(caught.values())
    print('LINT', 'OK' if ok else f'FAILED {errs[:10]}')
    sys.exit(0 if ok else 1)
