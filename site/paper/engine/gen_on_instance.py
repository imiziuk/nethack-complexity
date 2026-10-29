#!/usr/bin/env python3
"""gen_on_instance.py -- L_ON* instance generator for the NP-hardness reduction (proofs/hu-on-lower.md §4).

Input : a small Planar Monotone Rectilinear 3-SAT instance as JSON
        {"n": 3, "clauses": [[1,2,3], [-1,-3], [2]], "order": optional, "assignment": optional}
        - variables 1..n on a horizontal line, clause = list of 1..3 distinct literals, all of one sign
          (positive clauses drawn above the line, negative below);
        - "order" (optional) = {"pos": [[var, clause_index], ...], "neg": [...]}: the left-to-right order of the
          clause legs along the variable line (the rectilinear drawing). If omitted, among all orders whose clause
          partition is non-crossing the one with the least nesting (sum of levels, then max level) is used
          (brute force: for small instances only).
Output: the NetHack Lua level script (des.* calls, phase2-spec whitelist) and, if the formula is satisfiable,
        the intended move string (vi-keys hjklyubn, 'E' = eat the cookie here: keys "e" then "y").

Usage : python gen_on_instance.py instance.json [-o out.lua] [--moves out.txt] [--ascii]

Layout (see hu-on-lower.md §4): a grid of 11x11 tiles. Every tile has a stone border ring, except the midpoint
"port" cells of the sides through which its corridor continues into the neighbouring tile.
"""
import argparse, itertools, json, sys
from collections import deque

T = 11                      # tile size
LEVEL_PITCH = 7             # tile rows per clause level
START_HUNGER = 900
EAT_AT = 860                # eat a fresh cookie when u.uhunger <= EAT_AT
EAT_TURNS = 2               # conservative model of one fortune-cookie meal (delay 1)
COOKIE = 40

PORT = {'N': (5, 0), 'E': (10, 5), 'S': (5, 10), 'W': (0, 5)}
VEC = {'N': (0, -1), 'S': (0, 1), 'E': (1, 0), 'W': (-1, 0)}
OPP = {'N': 'S', 'S': 'N', 'E': 'W', 'W': 'E'}
TF = {  # dihedral group D4 acting on tile-local coordinates 0..10
    'id': lambda x, y: (x, y), 'r90': lambda x, y: (y, 10 - x), 'r180': lambda x, y: (10 - x, 10 - y),
    'r270': lambda x, y: (10 - y, x), 'hm': lambda x, y: (10 - x, y), 'vm': lambda x, y: (x, 10 - y),
    'tr': lambda x, y: (y, x), 'atr': lambda x, y: (10 - y, 10 - x)}


def tf_dir(f, d):
    p = TF[f](*PORT[d])
    return next(k for k, v in PORT.items() if v == p)


# ---------------------------------------------------------------- tile patterns (positive-side orientation)
SBEND = [(0, 5), (1, 5), (2, 5), (2, 4), (2, 3), (3, 3), (4, 3), (5, 3), (6, 3), (7, 3), (8, 3), (8, 4), (8, 5),
         (9, 5), (10, 5)]


def pat_wire(ports):
    """Straight wires are S-bends (corners at (2,5),(2,3),(8,3),(8,5)): a boulder pushed in through a port is
    stuck at a corner within 2 cells (Lemma 2.2), so stray boulders never travel along wires."""
    if set(ports) == {'W', 'E'}:
        return {p: '.' for p in SBEND}, {}
    if set(ports) == {'N', 'S'}:
        return {TF['r90'](*p): '.' for p in SBEND}, {}
    cells = {(5, 5): '.'}
    for d in ports:
        dx, dy = VEC[d]
        for t in range(6):
            cells[(5 + dx * t, 5 + dy * t)] = '.'
    return cells, {}


def pat_X():
    """G_X (§3.5) rotated: K enters W, leaves E; P runs N-S through S=(5,5). The P line is straight on rows 3..7
    (S +- 2) and bends east outside that window (corners (5,1),(7,1),(7,3),(5,3) and mirror), so the 8-neighbourhood
    of every K cell is exactly the proved map."""
    c = {p: '.' for p in [(5, 0), (5, 1), (6, 1), (7, 1), (7, 2), (7, 3), (6, 3), (5, 3), (5, 4), (5, 5),
                          (5, 6), (5, 7), (6, 7), (7, 7), (7, 8), (7, 9), (6, 9), (5, 9), (5, 10)]}
    for p in [(0, 5), (1, 5), (1, 6), (1, 7), (1, 8), (2, 8), (3, 8), (3, 7), (3, 6), (3, 4),
              (7, 5), (8, 5), (9, 5), (10, 5)]:
        c[p] = '.'
    c[(3, 5)] = '0'   # delta on n2
    c[(4, 5)] = '0'   # tau on n1
    c[(6, 5)] = '^'   # s1 hole
    return c, dict(kin=(3, 6), n2=(3, 5), n1=(4, 5), S=(5, 5), pocket=(3, 4), s1=(6, 5))


def pat_Cl():
    """G_C (§3.2) mirrored for a positive clause: K back segment enters W -> Q=(5,5) -> (5,4) -> C=(5,3) -> out N;
    P T-lane enters S -> T=(5,7) -> N=(5,6) holds W -> U-turn out E."""
    c = {}
    for p in [(0, 5), (1, 5), (2, 5), (3, 5), (4, 5), (5, 5), (5, 4), (5, 3), (6, 3), (7, 3), (7, 2), (7, 1),
              (6, 1), (5, 1), (5, 0), (5, 7), (5, 8), (5, 9), (5, 10), (6, 6), (7, 6), (8, 6), (8, 5), (9, 5),
              (10, 5)]:
        c[p] = '.'
    c[(5, 6)] = '0'
    return c, dict(Q=(5, 5), N=(5, 6), T=(5, 7), C=(5, 3))


def pat_door():
    """G_D (§3.3) reflected: K enters N -> e=(5,4) -> X=(5,5) holds Kd (pocket (5,6) below) -> q=(6,5) -> out E."""
    c = {(5, y): '.' for y in range(5)}
    for p in [(5, 6), (6, 5), (7, 5), (8, 5), (9, 5), (10, 5)]:
        c[p] = '.'
    c[(5, 5)] = '0'
    return c, dict(e=(5, 4), X=(5, 5), pocket=(5, 6))


BASE = {'X': (pat_X, {'W', 'E'}, {'N', 'S'}), 'Cl': (pat_Cl, None, None), 'door': (pat_door, None, None)}


# ---------------------------------------------------------------- instance analysis
def parse(inst):
    n = inst['n']
    cl = [list(c) for c in inst['clauses']]
    for c in cl:
        assert 1 <= len(c) <= 3 and len(set(abs(l) for l in c)) == len(c), c
        assert all(l > 0 for l in c) or all(l < 0 for l in c), ('not monotone', c)
        assert all(1 <= abs(l) <= n for l in c)
    return n, cl


def compress(n, cl, order=None):
    """Preprocessing: delete variables that occur in no clause and renumber the rest in order (does not change
    satisfiability or planarity; the drawing restricted to the used variables is still a PMR drawing)."""
    used = sorted({abs(l) for c in cl for l in c})
    ren = {v: k + 1 for k, v in enumerate(used)}
    cl2 = [[ren[abs(l)] * (1 if l > 0 else -1) for l in c] for c in cl]
    order2 = None
    if order:
        order2 = {s: [[ren[v], i] for v, i in o] for s, o in order.items()}
    else:      # canonical clause order (so equal formulas give equal levels)
        cl2 = sorted(sorted(c) for c in cl2)
    return len(used), cl2, order2, used


def noncrossing(seq):
    """seq = list of clause ids (leg order). True iff the partition into clauses is non-crossing."""
    pos = {}
    for i, c in enumerate(seq):
        pos.setdefault(c, []).append(i)
    ids = list(pos)
    for a in ids:
        for b in ids:
            if a == b:
                continue
            pa = pos[a]
            gaps = set()
            for p in pos[b]:
                g = sum(1 for q in pa if q < p)
                gaps.add(0 if g == len(pa) else g)
            if len(gaps) > 1:
                return False
    return True


def leg_order(n, cl, side, given=None):
    ids = [i for i, c in enumerate(cl) if (c[0] > 0) == (side == 'pos')]
    per_var = {v: [i for i in ids if any(abs(l) == v for l in cl[i])] for v in range(1, n + 1)}
    if given is not None:
        seq = [tuple(x) for x in given]
        assert sorted(seq) == sorted((v, i) for v in per_var for i in per_var[v]), 'order does not match legs'
        assert [v for v, _ in seq] == sorted(v for v, _ in seq), 'legs not sorted by variable'
        assert noncrossing([i for _, i in seq]), 'given order is not planar'
        return seq
    choices = [list(itertools.permutations(per_var[v])) for v in range(1, n + 1)]
    best = None
    for combo in itertools.product(*choices):
        seq = [(v + 1, i) for v, perm in enumerate(combo) for i in perm]
        if noncrossing([i for _, i in seq]):
            lev = forest(seq)[3]
            score = (sum(lev.values()), max(lev.values(), default=0))   # least nesting first
            if best is None or score < best[0]:
                best = (score, seq)
    return best[1] if best else None


def forest(seq):
    """Nesting forest of a non-crossing leg order. Returns (legs_of, children_in_gap, roots, level)."""
    legs_of = {}
    for p, (v, i) in enumerate(seq):
        legs_of.setdefault(i, []).append((p, v))
    span = {i: (l[0][0], l[-1][0]) for i, l in legs_of.items()}
    parent, gap = {}, {}
    for y in legs_of:
        best = None
        for x in legs_of:
            if x == y:
                continue
            px = [p for p, _ in legs_of[x]]
            g = sum(1 for q in px if q < span[y][0])
            if 0 < g < len(px) and span[x][0] < span[y][0]:
                if best is None or span[x][1] - span[x][0] < span[best][1] - span[best][0]:
                    best, bg = x, g
        if best is not None:
            parent[y], gap[y] = best, bg
    kids = {x: {k: [] for k in range(1, len(legs_of[x]))} for x in legs_of}
    roots = []
    for y in sorted(legs_of, key=lambda i: span[i][0]):
        (kids[parent[y]][gap[y]] if y in parent else roots).append(y)
    level = {}

    def lev(x):
        if x not in level:
            level[x] = 1 + max([lev(c) for g in kids[x].values() for c in g], default=0)
        return level[x]
    for x in legs_of:
        lev(x)
    return legs_of, kids, roots, level


def preorder(roots, kids):
    out = []

    def go(x):
        out.append(x)
        for k in sorted(kids[x]):
            for c in kids[x][k]:
                go(c)
    for r in roots:
        go(r)
    return out


def tokens(x, legs_of, kids):
    t = [('a', x), ('hL', x)]
    for k in range(len(legs_of[x])):
        t.append(('leg', x, k, legs_of[x][k][1]))
        for c in kids[x].get(k + 1, []):
            t += tokens(c, legs_of, kids)
    t.append(('hR', x))
    return t


# ---------------------------------------------------------------- layout
class Layout:
    def __init__(self, inst):
        self.inst = inst
        n0, cl0 = parse(inst)
        self.n, self.cl, order, self.var_names = compress(n0, cl0, inst.get('order'))
        order = order or {}
        self.side = {}
        for s in ('pos', 'neg'):
            seq = leg_order(self.n, self.cl, s, order.get(s))
            if seq is None:
                raise ValueError('not PMR: no planar leg order on side ' + s)
            legs_of, kids, roots, level = forest(seq)
            self.side[s] = dict(seq=seq, legs_of=legs_of, kids=kids, roots=roots, level=level,
                                pre=preorder(roots, kids),
                                toks=[t for r in roots for t in tokens(r, legs_of, kids)])
        self.columns()
        self.rows()
        self.occ, self.spec, self.junc, self.labels = {}, {}, set(), {}
        self.build_P()
        self.build_K()
        self.resolve()

    # ---- columns: the token sweep (§4.2)
    def columns(self):
        self.col, self.u = {}, {}
        ptr = {'pos': 0, 'neg': 0}
        x = 1
        self.fork, self.join = {}, {}

        def place(s, t, xx):
            if t[0] == 'leg':
                self.u[(t[1], t[2])] = xx + 1          # door xx, T-lane xx+1, return lane xx+2
                return xx + 3
            self.col[(t[0], t[1])] = xx
            return xx + 1
        for i in range(1, self.n + 1):
            xs = {}
            for s in ('pos', 'neg'):
                toks, p, xx = self.side[s]['toks'], ptr[s], x
                while p < len(toks) and toks[p][0] != 'leg':
                    xx = place(s, toks[p], xx)
                    p += 1
                ptr[s], xs[s] = p, xx
            self.fork[i] = max(xs.values())
            x = self.fork[i] + 1
            for s in ('pos', 'neg'):
                toks, p, xx = self.side[s]['toks'], ptr[s], x
                last = max([j for j in range(p, len(toks)) if toks[j][0] == 'leg' and toks[j][3] == i], default=None)
                if last is not None:
                    assert toks[p][0] == 'leg' and toks[p][3] == i
                    while p <= last:
                        xx = place(s, toks[p], xx)
                        p += 1
                ptr[s], xs[s] = p, xx
            self.join[i] = max(xs.values())
            x = self.join[i] + 1
        ends = {}
        for s in ('pos', 'neg'):
            toks, p, xx = self.side[s]['toks'], ptr[s], x
            while p < len(toks):
                assert toks[p][0] != 'leg'
                xx = place(s, toks[p], xx)
                p += 1
            ends[s] = xx
        self.goal_col = ends['pos']
        self.xc = max(ends['pos'] + 1, ends['neg'], x)
        self.xE = self.xc + 1
        self.Wt = self.xE + 1

    def rows(self):
        self.Dtop = {s: (LEVEL_PITCH * max(d['level'].values()) + 3 if d['level'] else 0)
                     for s, d in self.side.items()}
        self.RM = max(self.Dtop['pos'], 2)
        self.Ht = self.RM + max(self.Dtop['neg'], 1) + 1

    def r(self, s, depth):
        return self.RM - depth if s == 'pos' else self.RM + depth

    def geo(self, s, x):
        """depth of Q rows v[k], forward row f, dive row d of clause x on side s."""
        L, ell = len(self.side[s]['legs_of'][x]), self.side[s]['level'][x]
        v = [1 + LEVEL_PITCH * ell - 2 * k for k in range(L)]
        return v, 1 + LEVEL_PITCH * ell + 1, v[-1] - 1

    # ---- routing primitives
    def route(self, pts, cls):
        tiles = [pts[0]]
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            assert x0 == x1 or y0 == y1, (pts, 'not axis-aligned')
            dx, dy = (x1 > x0) - (x1 < x0), (y1 > y0) - (y1 < y0)
            x, y = x0, y0
            while (x, y) != (x1, y1):
                x, y = x + dx, y + dy
                tiles.append((x, y))
        for i, t in enumerate(tiles):
            def dirto(a, b):
                return next(k for k, v in VEC.items() if v == (b[0] - a[0], b[1] - a[1]))
            din = dirto(t, tiles[i - 1]) if i > 0 else None
            dout = dirto(t, tiles[i + 1]) if i + 1 < len(tiles) else None
            assert 0 <= t[0] < self.Wt and 0 <= t[1] < self.Ht, ('tile off map', t)
            self.occ.setdefault(t, []).append((cls, din, dout))
        return tiles

    def special(self, t, kind, side):
        assert t not in self.spec, ('special overlap', t)
        self.spec[t] = (kind, side)

    # ---- P: main line, forks/joins, branches with spikes
    def build_P(self):
        RM = self.RM
        self.labels[(0, RM)] = 's0'
        self.special((0, self.r('pos', 2)), 'sentinel', 'pos')
        prev = 0
        for i in range(1, self.n + 1):
            self.route([(prev, RM), (self.fork[i], RM)], 'P')
            self.junc |= {(self.fork[i], RM), (self.join[i], RM)}
            for s in ('pos', 'neg'):
                pts = [(self.fork[i], RM), (self.fork[i], self.r(s, 1))]
                legs = sorted([(self.u[(x, k)], x, k) for x, l in self.side[s]['legs_of'].items()
                               for k, (_, v) in enumerate(l) if v == i])
                for u, x, k in legs:
                    v = self.geo(s, x)[0][k]
                    pts += [(u, self.r(s, 1)), (u, self.r(s, v)), (u + 1, self.r(s, v)), (u + 1, self.r(s, 1))]
                    self.special((u, self.r(s, v)), 'Cl', s)
                    self.special((u - 1, self.r(s, v)), 'door', s)
                pts += [(self.join[i], self.r(s, 1)), (self.join[i], RM)]
                self.route(dedupe(pts), 'P')
            prev = self.join[i]
        self.route([(prev, RM), (self.xE, RM)], 'P')
        self.junc.add((self.xE, RM))

    # ---- K: clause gadgets and the chain of arcs
    def clause_K(self, s, x):
        v, f, _ = self.geo(s, x)
        hL, hR = self.col[('hL', x)], self.col[('hR', x)]
        u = [self.u[(x, k)] for k in range(len(v))]
        r = lambda d: self.r(s, d)
        L = len(v)
        if L > 1:
            self.route([(hL, r(f)), (hL, r(v[-1] + 1))], 'K')
        for k in range(L):
            self.junc.add((hL, r(v[k] + 1)))
            self.route([(hL, r(v[k] + 1)), (u[k] - 1, r(v[k] + 1)), (u[k] - 1, r(v[k]))], 'K')
            self.route([(u[k] - 1, r(v[k])), (u[k], r(v[k]))], 'K')
            self.route([(u[k], r(v[k])), (u[k], r(f))], 'K')
            self.junc.add((u[k], r(f)))
        self.route([(u[0], r(f)), (hR, r(f))], 'K')
        self.junc |= {(hL, r(f)), (hR, r(f))}

    def chosen_path(self, s, x, k):
        v, f, _ = self.geo(s, x)
        hL, hR = self.col[('hL', x)], self.col[('hR', x)]
        u = self.u[(x, k)]
        r = lambda d: self.r(s, d)
        return dedupe([(hL, r(f)), (hL, r(v[k] + 1)), (u - 1, r(v[k] + 1)), (u - 1, r(v[k])), (u, r(v[k])),
                       (u, r(f)), (hR, r(f))])

    def arrival(self, s, x, top_col):
        """from (top_col, depth Dtop) to the left hub of the first root x."""
        D, (_, f, _) = self.Dtop[s], self.geo(s, x)
        a, hL = self.col[('a', x)], self.col[('hL', x)]
        return [(top_col, self.r(s, D)), (a, self.r(s, D)), (a, self.r(s, f)), (hL, self.r(s, f))]

    def arc(self, prev, nxt):
        """K polyline from the right hub of prev (or the main-line end) to the left hub of nxt (or the goal)."""
        RM, xc, xE = self.RM, self.xc, self.xE
        hasneg, haspos = bool(self.side['neg']['pre']), bool(self.side['pos']['pre'])
        if prev is None:
            pts = [(xE, RM)]
            if hasneg:
                return pts + self.arrival('neg', nxt[1], xE)
            pts += [(xE, RM + 1), (xc, RM + 1)]
            return pts + (self.arrival('pos', nxt[1], xc) if nxt else [(xc, RM - 1)])
        ps, px = prev
        _, fz, _ = self.geo(ps, px)
        start = (self.col[('hR', px)], self.r(ps, fz))
        if nxt is not None and nxt[0] == ps:
            s, x = nxt
            a, hL = self.col[('a', x)], self.col[('hL', x)]
            _, fx, _ = self.geo(s, x)
            kids = self.side[s]['kids'][px]
            first_child = next((c for k in sorted(kids) for c in kids[k]), None)
            if first_child == x:                                   # dive (i)
                _, _, dP = self.geo(s, px)
                return dedupe([start, (start[0], self.r(s, dP)), (a, self.r(s, dP)), (a, self.r(s, fx)),
                               (hL, self.r(s, fx))])
            return dedupe([start, (a, start[1]), (a, self.r(s, fx)), (hL, self.r(s, fx))])   # step right (ii)
        if ps == 'neg':
            pts = [start, (xc, start[1])]
            return dedupe(pts + (self.arrival('pos', nxt[1], xc) if nxt else [(xc, RM - 1)]))
        return [start, (self.goal_col, start[1])]

    def build_K(self):
        chain = [('neg', x) for x in self.side['neg']['pre']] + [('pos', x) for x in self.side['pos']['pre']]
        self.chain = chain
        self.arcs = []
        prev = None
        for c in chain + [None]:
            pts = self.arc(prev, c)
            self.route(pts, 'K')
            self.arcs.append(pts)
            if c is not None:
                self.clause_K(*c)
            prev = c
        self.goal_tile = self.arcs[-1][-1]
        self.labels[self.goal_tile] = 'g'

    # ---- tiles -> cells
    def resolve(self):
        self.tile = {}
        for t in set(self.occ) | set(self.spec):
            ent = self.occ.get(t, [])
            ports = {d for _, a, b in ent for d in (a, b) if d}
            if t in self.spec:
                kind, s = self.spec[t]
                want = {'Cl': {'W', 'N', 'S', 'E'}, 'door': {'N', 'E'}, 'sentinel': set()}[kind]
                if s == 'neg':
                    want = {tf_dir('vm', d) for d in want}
                assert ports == want, ('special tile ports', t, kind, ports, want)
                if kind == 'Cl':     # K uses W and out, P uses in and E
                    kp = {d for c, a, b in ent if c == 'K' for d in (a, b) if d}
                    assert kp == {'W', 'N' if s == 'pos' else 'S'}, (t, ent)
                self.tile[t] = (kind, 'id' if s == 'pos' else 'vm', ports)
                continue
            if t in self.junc or len(ent) == 1:
                if t not in self.junc:
                    assert len(ent) == 1
                self.tile[t] = ('wire', None, ports)
                continue
            cls = sorted(c for c, _, _ in ent)
            assert cls == ['K', 'P'], ('illegal overlap', t, ent)
            k = next(e for e in ent if e[0] == 'K')
            p = next(e for e in ent if e[0] == 'P')
            assert k[1] and k[2] and k[1] == OPP[k[2]], ('K not straight through crossover', t, ent)
            assert p[1] and p[2] and p[1] == OPP[p[2]] and p[1] not in (k[1], k[2]), ('P not straight', t, ent)
            f = next(f for f in ('id', 'vm', 'hm', 'r180', 'r90', 'r270', 'tr', 'atr')
                     if tf_dir(f, 'W') == k[1] and tf_dir(f, 'E') == k[2])
            self.tile[t] = ('X', f, ports)
        self.cells()

    def cells(self):
        W, H = self.Wt * T, self.Ht * T
        self.W, self.H = W, H
        g = [[' '] * W for _ in range(H)]
        self.boulders, self.holes, self.lab = set(), set(), {}
        self.tile_of = {}
        for (tc, tr), (kind, f, ports) in self.tile.items():
            ox, oy = tc * T, tr * T
            if kind == 'wire':
                cells, labs = pat_wire(ports)
                f = 'id'
            elif kind == 'sentinel':   # pit + sealed branch-stair pocket 'b' (phase2-spec Rev. 3 item 8)
                cells, labs = {(5, 5): 'p', (2, 2): 'b'}, {}
            else:
                cells, labs = {'X': pat_X, 'Cl': pat_Cl, 'door': pat_door}[kind]()
            for (x, y), ch in cells.items():
                X, Y = TF[f](x, y)
                X, Y = ox + X, oy + Y
                g[Y][X] = '.' if ch in '.0' else ch
                if ch == '0':
                    self.boulders.add((X, Y))
                if ch == '^':
                    self.holes.add((X, Y))
                self.tile_of[(X, Y)] = (tc, tr)
            for name, (x, y) in labs.items():
                X, Y = TF[f](x, y)
                self.lab[((tc, tr), name)] = (ox + X, oy + Y)
            if self.labels.get((tc, tr)) == 's0':
                self.start = (ox + 5, oy + 5)
            if self.labels.get((tc, tr)) == 'g':
                self.goal = (ox + 5, oy + 5)
            if kind == 'sentinel':
                self.pit = (ox + 5, oy + 5)
                self.branch = (ox + 2, oy + 2)
        self.grid = g
        bx, by = self.branch
        assert all(g[by + dy][bx + dx] == ' ' for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy),             'branch pocket not sealed'
        self.check_separation()

    def check_separation(self):
        """Lemma 4.1 (checked here mechanically): floor cells of different tiles are 8-adjacent only as matching
        port pairs (orthogonal, on the shared side's midpoint)."""
        for (x, y), t in self.tile_of.items():
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    q = (x + dx, y + dy)
                    if q in self.tile_of and self.tile_of[q] != t:
                        assert dx == 0 or dy == 0, ('diagonal contact across tiles', (x, y), q)
                        assert (x % T, y % T) in PORT.values(), ('non-port contact', (x, y), q)

    # ---- statistics
    def stats(self):
        floor = sum(row.count('.') + row.count('^') + row.count('p') + row.count('b') for row in self.grid)
        kinds = {}
        for k, _, _ in self.tile.values():
            kinds[k] = kinds.get(k, 0) + 1
        return dict(width=self.W, height=self.H, tiles_w=self.Wt, tiles_h=self.Ht, floor_cells=floor,
                    boulders=len(self.boulders), holes=len(self.holes), crossovers=kinds.get('X', 0),
                    closing_sites=kinds.get('Cl', 0), doors=kinds.get('door', 0),
                    cookies=floor - len(self.holes) - 2)

    def ascii(self):
        g = [row[:] for row in self.grid]
        for (x, y) in self.boulders:
            g[y][x] = '0'
        g[self.start[1]][self.start[0]] = '@'
        g[self.goal[1]][self.goal[0]] = 'G'
        return '\n'.join(''.join(r).rstrip() for r in g)


def dedupe(pts):
    out = []
    for p in pts:
        if not out or out[-1] != p:
            out.append(p)
    # drop collinear middle points
    res = []
    for p in out:
        if len(res) >= 2 and (res[-2][0] == res[-1][0] == p[0] or res[-2][1] == res[-1][1] == p[1]):
            res[-1] = p
        else:
            res.append(p)
    return res


# ---------------------------------------------------------------- exact movement model (hu-on-lower §2)
KEYS = {(-1, 0): 'h', (1, 0): 'l', (0, -1): 'k', (0, 1): 'j', (-1, -1): 'y', (1, -1): 'u', (-1, 1): 'b', (1, 1): 'n'}


class Sim:
    """Cell-level simulation of the rules F1-F4 (Sokoban, heavy hero). Used for the intended play."""

    def __init__(self, lay):
        self.L = lay
        self.b = set(lay.boulders)
        self.h = set(lay.holes)
        self.pos = lay.start
        self.cookies = {(x, y) for y, row in enumerate(lay.grid) for x, ch in enumerate(row) if ch == '.'}
        self.hunger, self.minh, self.moves, self.out = START_HUNGER, START_HUNGER, 0, []
        self.visits = {self.pos: 1}
        self.dry, self.maxdry = 0, 0     # consecutive moves without passing a cookie cell

    def floor(self, c):
        x, y = c
        return 0 <= x < self.L.W and 0 <= y < self.L.H and self.L.grid[y][x] in '.^'

    def bad(self, c):
        return not self.floor(c) or c in self.b

    def can_step(self, a, d):
        t = (a[0] + d[0], a[1] + d[1])
        if not self.floor(t) or t in self.b or t in self.h:
            return False
        if d[0] and d[1] and self.bad((a[0] + d[0], a[1])) and self.bad((a[0], a[1] + d[1])):
            return False
        return True

    def arrive(self, key):
        self.moves += 1
        self.hunger -= 1
        self.out.append(key)
        self.visits[self.pos] = self.visits.get(self.pos, 0) + 1
        self.dry = 0 if self.pos in self.cookies else self.dry + 1
        self.maxdry = max(self.maxdry, self.dry)
        if self.pos in self.cookies and self.hunger <= EAT_AT:
            self.cookies.discard(self.pos)
            self.hunger += COOKIE - EAT_TURNS
            self.moves += 1
            self.out.append('E')
        self.minh = min(self.minh, self.hunger)

    def push(self, d):
        b = (self.pos[0] + d[0], self.pos[1] + d[1])
        t = (b[0] + d[0], b[1] + d[1])
        assert b in self.b, ('no boulder to push', self.pos, d)
        assert self.floor(t) and t not in self.b, ('push blocked', self.pos, d)
        self.b.discard(b)
        if t in self.h:
            self.h.discard(t)
        else:
            self.b.add(t)
        self.pos = b
        self.arrive(KEYS[d])

    def walk(self, goal):
        prev = {self.pos: None}
        q = deque([self.pos])
        while q:
            a = q.popleft()
            if a == goal:
                break
            for d in KEYS:
                t = (a[0] + d[0], a[1] + d[1])
                if t not in prev and self.can_step(a, d):
                    prev[t] = (a, d)
                    q.append(t)
        assert goal in prev, ('walk: unreachable', self.pos, goal)
        path = []
        c = goal
        while prev[c]:
            a, d = prev[c]
            path.append(d)
            c = a
        for d in reversed(path):
            self.pos = (self.pos[0] + d[0], self.pos[1] + d[1])
            self.arrive(KEYS[d])


def satisfying(n, cl):
    for bits in itertools.product([False, True], repeat=n):
        if all(any(bits[abs(l) - 1] == (l > 0) for l in c) for c in cl):
            return list(bits)
    return None


def intended_play(lay, alpha):
    """§5.1: P phase (take T_i iff alpha_i), then the K chain choosing a true literal per clause."""
    S = Sim(lay)
    sub = lambda a, b: (a[0] - b[0], a[1] - b[1])
    for i in range(1, lay.n + 1):
        s = 'neg' if alpha[i - 1] else 'pos'   # walk T_i (spikes of negative clauses) iff x_i true
        legs = sorted([(lay.u[(x, k)], x, k) for x, l in lay.side[s]['legs_of'].items()
                       for k, (_, v) in enumerate(l) if v == i])
        for u, x, k in legs:
            t = (u, lay.r(s, lay.geo(s, x)[0][k]))
            T_, N_ = lay.lab[(t, 'T')], lay.lab[(t, 'N')]
            S.walk(T_)
            S.push(sub(N_, T_))
        S.walk((lay.join[i] * T + 5, lay.RM * T + 5))
    route = []
    for j, c in enumerate(lay.chain):
        route += lay.arcs[j]
        s, x = c
        lits = lay.cl[x]
        legs = lay.side[s]['legs_of'][x]
        k = next(k for k, (_, v) in enumerate(legs) if alpha[v - 1] == (s == 'pos'))
        route += lay.chosen_path(s, x, k)
    route += lay.arcs[-1]
    tiles = []
    for a, b in zip(route, route[1:]):
        dx, dy = (b[0] > a[0]) - (b[0] < a[0]), (b[1] > a[1]) - (b[1] < a[1])
        p = a
        while p != b:
            if not tiles or tiles[-1] != p:
                tiles.append(p)
            p = (p[0] + dx, p[1] + dy)
    tiles.append(route[-1])
    for t in tiles:
        kind = lay.tile.get(t, (None,))[0]
        if kind == 'X':
            kin, n2, n1 = lay.lab[(t, 'kin')], lay.lab[(t, 'n2')], lay.lab[(t, 'n1')]
            S.walk(kin)
            S.push(sub(n2, kin))
            S.push(sub(n1, n2))
            S.push(sub(n1, n2))
        elif kind == 'door':
            e, X = lay.lab[(t, 'e')], lay.lab[(t, 'X')]
            S.walk(e)
            S.push(sub(X, e))
    S.walk(lay.goal)
    return S


# ---------------------------------------------------------------- Lua
def lua(lay, ox=1, oy=0):
    out = ['-- L_ON* instance generated by tools/gen_on_instance.py (hu-on-lower.md section 4).',
           '-- Needs the generalized family: COLNO >= %d, ROWNO >= %d (stock 80x21 is too small).'
           % (lay.W + ox + 1, lay.H + oy + 1),
           '-- Hero template: human Valkyrie, pettype:none (phase2-spec Rev. 2). Run order (Rev. 1):',
           '-- after newgame(): des.reset_level(); <this script>; des.finalize_level().',
           'nh.debug_flags({ mongen = false });',
           'u.clear_inventory();',
           'des.level_flags("noflip", "sokoban", "noteleport");',
           'des.level_init({ style = "solidfill", fg = " ", lit = true });',
           'des.map({ x = %d, y = %d, map = [[' % (ox, oy)]
    rows = [''.join('.' if ch in '.^pb' else ' ' for ch in row) for row in lay.grid]
    out.append('\n'.join(rows) + ']] });')
    out.append('des.non_diggable();')
    out.append('des.non_passwall();')
    for (x, y) in sorted(lay.boulders):
        out.append('des.object("boulder", %d, %d);' % (x, y))
    for (x, y) in sorted(lay.holes):
        out.append('des.trap("hole", %d, %d);' % (x, y))
    out.append('des.trap("pit", %d, %d);   -- sentinel (keeps Sokoban rules on)' % lay.pit)
    for y, row in enumerate(lay.grid):
        for x, ch in enumerate(row):
            if ch == '.':
                out.append('des.object({ id = "fortune cookie", x = %d, y = %d, buc = "uncursed", quantity = 1 });'
                           % (x, y))
    bx, by = lay.branch   # Rev. 3: sealed 1-cell pocket (8 stone neighbours) receives the DL1 branch stair
    out.append('des.levregion({ region = { %d, %d, %d, %d }, region_islev = true, type = "branch" });'
               % (bx + ox, by + oy, bx + ox, by + oy))
    sx, sy = lay.start
    out.append('des.teleport_region({ region = { %d, %d, %d, %d }, region_islev = true, dir = "both" });'
               % (sx + ox, sy + oy, sx + ox, sy + oy))
    out.append('u.giveobj(obj.new("cursed loadstone"));')
    out.append('-- target g = map cell (%d, %d), absolute (%d, %d)' % (lay.goal[0], lay.goal[1],
                                                                       lay.goal[0] + ox, lay.goal[1] + oy))
    return '\n'.join(out) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('instance')
    ap.add_argument('-o', '--out')
    ap.add_argument('--moves')
    ap.add_argument('--ascii', action='store_true')
    a = ap.parse_args()
    inst = json.load(open(a.instance))
    lay = Layout(inst)
    text = lua(lay)
    if a.out:
        open(a.out, 'w', encoding='ascii', newline='\n').write(text)
    st = lay.stats()
    alpha = ([inst['assignment'][v - 1] for v in lay.var_names] if inst.get('assignment')
             else satisfying(lay.n, lay.cl))
    if alpha:
        S = intended_play(lay, alpha)
        assert S.pos == lay.goal
        st.update(solution_moves=S.moves, min_hunger=S.minh, max_visits=max(S.visits.values()),
                  max_moves_without_cookie=S.maxdry)
        if a.moves:
            open(a.moves, 'w', encoding='ascii', newline='\n').write(''.join(S.out) + '\n')
    else:
        st.update(solution_moves=None)
    if a.ascii:
        print(lay.ascii())
    print(json.dumps(st), file=sys.stderr)


if __name__ == '__main__':
    main()
