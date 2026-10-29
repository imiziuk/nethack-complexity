#!/usr/bin/env python3
"""R_model.py -- gadget windows + model side of the real-game differential brute force (proofs/exptime/R-realgame.md).

A *window* is a gadget map (A_core chars: '#'/' ' stone, '.' floor, '0' boulder, 'A'-'Z' port, 'a'-'z' named floor,
'^' hole). In the real game the window sits inside solid stone (des.map + solidfill), so port cells are dead ends.

Model used for prediction:
  * windows without holes: A_core.Board.moves (imported read-only) on the window with port letters turned into '.',
    so the window's own stone frame bounds every push (no LeakError);
  * windows with holes (G_X): HoleModel below = A_core rules + hu-on-lower F1/F4 (= check_small.py / D_game.py):
    a boulder pushed onto an unplugged hole plugs it (boulder and hole vanish, cell becomes floor); a hero step
    onto an unplugged hole = LOSS (falls through); a hole is not bad rock for the diagonal corner rule.
    On hole-free windows HoleModel is checked to agree with A_core on every enumerated state (self-test).

State = (hero cell index, boulder bitmask, unplugged-hole bitmask). Keys: hjklyubn (vi keys, y up = -1).
"""
import os, sys
from collections import deque

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import A_core as K
import A_library as AL
import A2_scd as A2

KEYS = {'h': (-1, 0), 'j': (0, 1), 'k': (0, -1), 'l': (1, 0), 'y': (-1, -1), 'u': (1, -1), 'b': (-1, 1), 'n': (1, 1)}
KEYLIST = 'hjklyubn'


class Window:
    def __init__(self, name, rows, ports_extra=None):
        self.name = name
        self.rows = [r for r in rows]
        self.H = len(rows)
        self.W = max(len(r) for r in rows)
        g = [r.ljust(self.W) for r in rows]
        self.ports = {}
        holes = []
        mrows = []
        for y in range(self.H):
            m = ''
            for x in range(self.W):
                ch = g[y][x]
                if ch.isupper():
                    self.ports[ch] = (x, y)
                    ch = '.'
                if ch == '^':
                    holes.append((x, y))
                    ch = '.'
                m += ch
            mrows.append(m)
        self.board = K.Board(mrows)          # A_core board, ports as plain floor
        self.cells = self.board.cells
        self.idx = self.board.idx
        self.n = len(self.cells)
        self.b0 = self.board.b0
        self.h0 = sum(1 << self.idx[c] for c in holes)
        self.has_holes = bool(holes)
        self.port_idx = {p: self.idx[c] for p, c in self.ports.items()}

    # ---------- prediction ----------
    def predict_acore(self, h, B, key):
        dx, dy = KEYS[key]
        x, y = self.cells[h]
        t = self.idx.get((x + dx, y + dy))
        if t is None:
            return ('stay', h, B, 0)
        for t2, B2 in self.board.moves(h, B):
            if t2 == t:
                return ('move', t2, B2, 0)
        return ('stay', h, B, 0)

    def predict_hole(self, h, B, Hm, key):
        dx, dy = KEYS[key]
        x, y = self.cells[h]
        t = self.idx.get((x + dx, y + dy))
        if t is None:
            return ('stay', h, B, Hm)
        tb = 1 << t
        if dx == 0 or dy == 0:
            if B & tb:
                b = self.idx.get((x + 2 * dx, y + 2 * dy))
                if b is None or B >> b & 1:
                    return ('stay', h, B, Hm)
                if Hm >> b & 1:                       # plug the hole
                    return ('move', t, B & ~tb, Hm & ~(1 << b))
                return ('move', t, (B & ~tb) | (1 << b), Hm)
            if Hm & tb:
                return ('loss', t, B, Hm)
            return ('move', t, B, Hm)
        # diagonal
        if B & tb:
            return ('stay', h, B, Hm)
        ok = False
        for c in ((x + dx, y), (x, y + dy)):
            i = self.idx.get(c)
            if i is not None and not (B >> i & 1):
                ok = True
        if not ok:
            return ('stay', h, B, Hm)
        if Hm & tb:
            return ('loss', t, B, Hm)
        return ('move', t, B, Hm)

    def predict(self, h, B, Hm, key):
        if self.has_holes:
            return self.predict_hole(h, B, Hm, key)
        return self.predict_acore(h, B, key)

    # ---------- enumeration ----------
    def reachable(self, inits, limit=5_000_000):
        """all (h, B, H) reachable from hero on any port with boulders/holes = init (list of (B, H))."""
        seen = set()
        dq = deque()
        for B0, H0 in inits:
            for p, i in self.port_idx.items():
                s = (i, B0, H0)
                if s not in seen:
                    seen.add(s)
                    dq.append(s)
        while dq:
            h, B, Hm = dq.popleft()
            for k in KEYLIST:
                kind, h2, B2, H2 = self.predict(h, B, Hm, k)
                if kind != 'move':
                    continue
                s = (h2, B2, H2)
                if s not in seen:
                    seen.add(s)
                    dq.append(s)
                    if len(seen) > limit:
                        raise RuntimeError('too many states')
        return seen

    # ---------- traversals (A_core semantics: start on a port, stop at the first port reached) ----------
    def traversal_walks(self, B, Hm, p):
        """{(q, B', H'): shortest key string} for traversals from port p in local state (B, H)."""
        start = (self.port_idx[p], B, Hm)
        par = {start: None}
        dq = deque([start])
        out = {}
        portset = set(self.port_idx.values())
        pname = {i: n for n, i in self.port_idx.items()}
        while dq:
            s = dq.popleft()
            h, Bc, Hc = s
            for k in KEYLIST:
                kind, h2, B2, H2 = self.predict(h, Bc, Hc, k)
                if kind != 'move':
                    continue
                s2 = (h2, B2, H2)
                if s2 in par:
                    continue
                par[s2] = (s, k)
                if h2 in portset:
                    key = (pname[h2], B2, H2)
                    if key not in out:
                        w = []
                        c = s2
                        while par[c] is not None:
                            c, kk = par[c]
                            w.append(kk)
                        out[key] = ''.join(reversed(w))
                else:
                    dq.append(s2)
        return out

    def local_states(self, inits):
        """gadget states (B, H) reachable by traversals from the inits."""
        seen = set(inits)
        dq = deque(inits)
        while dq:
            B, Hm = dq.popleft()
            for p in self.port_idx:
                for (q, B2, H2) in self.traversal_walks(B, Hm, p):
                    if (B2, H2) not in seen:
                        seen.add((B2, H2))
                        dq.append((B2, H2))
        return seen

    def path_states(self, h, B, Hm, keys):
        """list of states along a key string (start included)."""
        out = [(h, B, Hm)]
        for k in keys:
            kind, h, B, Hm = self.predict(h, B, Hm, k)
            out.append((h, B, Hm))
        return out

    # ---------- helpers ----------
    def bset(self, B):
        return sorted(self.cells[i] for i in range(self.n) if B >> i & 1)

    def mask(self, cells):
        return sum(1 << self.idx[c] for c in cells)

    def show(self, h, B, Hm=0):
        g = [list(r.ljust(self.W)) for r in self.rows]
        for i, (x, y) in enumerate(self.cells):
            if g[y][x] in '0^':
                g[y][x] = '.'
            if Hm >> i & 1:
                g[y][x] = '^'
            if B >> i & 1:
                g[y][x] = '0'
        if h is not None:
            x, y = self.cells[h]
            g[y][x] = '@'
        return '\n'.join(''.join(r) for r in g)


# ---------------------------------------------------------------- the gadgets
def tile_rows(pat, ports):
    cells, lab = pat()
    rows = []
    pc = {(5, 0): 'N', (10, 5): 'E', (5, 10): 'S', (0, 5): 'W'}
    for y in range(11):
        r = ''
        for x in range(11):
            ch = cells.get((x, y), '#')
            if (x, y) in pc and ch == '.' and pc[(x, y)] in ports:
                ch = pc[(x, y)]
            r += ch
        rows.append(r)
    return rows, lab


def pp_joined():
    """precursor / 1-toggle window: proto-precursor with A, B, C joined by a corridor above (node T on it)."""
    pp = A2.PROTO_PRECURSOR
    W = len(pp[0])
    top = ['#' * W, '#' * W]
    t0 = list('#' * W)
    t1 = list('#' * W)
    for x in range(2, 8):
        t0[x] = '.'
    t0[5] = 'T'
    for x in (2, 4, 7):
        t1[x] = '.'
    rows = ['#' * W, ''.join(t0), ''.join(t1)]
    for r in pp:
        rows.append(r.replace('A', '.').replace('B', '.').replace('C', '.'))
    return rows


def scd_rows(prec_init='o'):
    """flat physical Fig. 37 SCD: precursor (top left), 1-toggle (top right, vertically mirrored),
    diodes d1 (I -> X) and d2 (Y -> J) below; hidden check locations D, G are dead-end pockets."""
    Wd, Hd = 23, 14
    g = [['#'] * Wd for _ in range(Hd)]

    def blit(rows, ox, oy, flip=False, pm=None):
        rr = rows[::-1] if flip else rows
        for y, r in enumerate(rr):
            for x, ch in enumerate(r):
                if ch == '#':
                    continue
                if ch.isupper():
                    ch = (pm or {}).get(ch, '.')
                g[oy + y][ox + x] = ch

    pp = list(A2.PROTO_PRECURSOR)
    if prec_init == 'c':        # precursor blocks at track x=3,5 (state 2 = closed)
        pp[2] = '#..0.0...#'
    blit(pp, 1, 3)
    blit(A2.PROTO_PRECURSOR, 13, 3, flip=True, pm={'E': 'O'})
    dio = AL.SLOT1             # = protodiode with C and D joined (Fig. 35a + joining corridor)
    blit(dio, 1, 9, pm={'A': 'I'})
    blit(dio, 6, 9, pm={'B': 'J'})
    for x in range(3, 20):     # T corridor
        g[1][x] = '.'
    for x in (3, 5, 8, 19):
        g[2][x] = '.'
    for x in (15, 17, 20):     # toggle's A, B, C joined (internal node tT)
        g[8][x] = '.'
    for x in range(15, 21):
        g[9][x] = '.'
    g[8][4] = '.'              # precursor E -> X -> d1.B
    g[8][7] = '.'              # precursor F -> Y -> d2.A
    return [''.join(r) for r in g]


def gadgets():
    """name -> (Window, inits [(B, H)], intended walks [(label, start port, (B,H) init, keys-or-None, expect)])"""
    import gen_on_instance as GO
    G = {}
    G['diode'] = Window('diode', AL.PROTODIODE)
    G['G_D'] = Window('G_D', AL.GD_ROWS)
    G['SLOT1'] = Window('SLOT1', AL.SLOT1)
    G['UTURN2'] = Window('UTURN2', AL.UTURN2)
    G['proto_precursor'] = Window('proto_precursor', A2.PROTO_PRECURSOR)
    G['precursor'] = Window('precursor', pp_joined())          # = 1-toggle window (T is a port only for precursor)
    rows, _ = tile_rows(GO.pat_Cl, 'NEWS')
    G['G_C'] = Window('G_C', rows)
    rows, _ = tile_rows(GO.pat_X, 'NEWS')
    G['G_X'] = Window('G_X', rows)
    rows, _ = tile_rows(GO.pat_door, 'NEWS')
    G['G_D_tile'] = Window('G_D_tile', rows)
    G['SCD'] = Window('SCD', scd_rows('o'))
    return G


if __name__ == '__main__':
    import time
    for name, w in gadgets().items():
        t0 = time.time()
        print('==', name, f'{w.W}x{w.H}', 'ports', w.ports, 'holes' if w.has_holes else '')
        print(w.show(None, w.b0, w.h0))
        if name == 'SCD':
            continue
        R = w.reachable([(w.b0, w.h0)])
        print(f'  reachable (h,B,H): {len(R)}  ({time.time() - t0:.1f}s)')
