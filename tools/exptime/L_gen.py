#!/usr/bin/env python3
"""L_gen.py -- layout generator for the EXPTIME reduction G6 <=_p L_OFF^{W+C} (review 5 repair 2).

Pipeline (proofs/exptime/L-generator.md):
  1. instance   : a G6 instance (F, X, Y, alpha0, first mover) -- review5_t1's random distribution, or a JSON file;
  2. arena      : B-reduction §3 game G_F with Lemma TS (plain SCDs only), built by review5_t1.build itself (read-only
                  import; its Arena class is swapped for a recorder so the same code produces the edge list);
  3. netlist    : every arena edge realized with B's base pieces: plain u->v = diode; O-tunnel u->v = diode, button O
                  of the door's SCD on a private node, diode; S-tunnel u->v = diode, I ... J of the SCD, diode;
                  the coin = one tile with ports E (entry, = T's only neighbour), A, B. Nodes of degree >= 3 become
                  junction tiles, degree-2 nodes direct route edges;
  4. layout     : B §6.2 bus layout on a macro grid: one bottom row of tiles (v2 SCD tile, v2 diode tile, junction,
                  coin, start), every route edge its own track row above, nested spans lower; where a column crosses a
                  track the macro cell is a copy of the v2 crossover map (build/xover/crossover.txt) under the grid
                  symmetry that matches both directions;
  5. check path : B2 §3 order t -> level 1 (one Thm 5.3 G' per SCD incl. the crossovers' SCDs) -> level 2 (one G'
                  per raw component) -> g, routed as a planar curve on the concrete cells (see L-generator.md §4);
  6. checks     : static (locality/planarity, Z1 exact, Z2 lint, check-location coverage) and semantic (attractors).
Usage: python L_gen.py [--seed N] [--trials K] [--out build/lgen]
"""
import itertools, json, os, random, sys, time
from collections import deque, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
import review5_t1 as R5

OUT = os.path.join(ROOT, 'build', 'lgen')


# ============================================================ 1. instances
def random_instance(rng):
    """same distribution as review5_t1.main (|X|, |Y| <= 2, <= 3 clauses, both first movers)."""
    nx_, ny_ = rng.choice([(1, 1), (1, 2), (2, 1), (2, 2), (0, 1), (1, 0)])
    X = [f'x{i}' for i in range(nx_)]
    Y = [f'y{i}' for i in range(ny_)]
    V = X + Y
    m = rng.randint(1, 3)
    F = []
    for _ in range(m):
        w = rng.randint(1, min(3, len(V)))
        F.append([(v, rng.randint(0, 1)) for v in rng.sample(V, w)])
    a0 = {v: rng.randint(0, 1) for v in V}
    first = rng.choice(['I', 'II'])
    if first == 'II' and all(any(a0[v] == s for v, s in C) for C in F):
        first = 'I'
    return dict(F=F, X=X, Y=Y, a0=a0, first=first)


def g6_winner(inst):
    return R5.g6(inst['F'], inst['X'], inst['Y'], inst['a0'], inst['first'])


# ============================================================ 2. arena (review5_t1.build, recorded)
class _Rec(R5.Arena):
    def solve(self, start, goal, init_open, cap=0):
        return self, start, goal, init_open


def arena(inst, mode='ts'):
    saved = R5.Arena
    R5.Arena = _Rec
    try:
        A, start, goal, init_open = R5.build(inst['F'], inst['X'], inst['Y'], inst['a0'], mode, inst['first'])
    finally:
        R5.Arena = saved
    return A, start, goal, set(init_open)


# ============================================================ 3. netlist
class Net:
    """gadgets: name -> dict(kind, ports {port: node}, init); kinds:
       'scd'  ports O (button, bidirectional), I (in), J (out); init 'o' | 'c'
       'dio'  ports A (in), B (out)
       'coin' ports E (in: arriving at T), A, B (out: nature's choice)
    nodes are strings; start node, goal node (= the arena's g, reached from c_m by a diode), t node (= c_m)."""
    PORT_DIR = {'scd': {'O': 'bi', 'I': 'in', 'J': 'out'}, 'dio': {'A': 'in', 'B': 'out'},
                'coin': {'E': 'in', 'A': 'out', 'B': 'out'}}

    def __init__(self):
        self.g = {}
        self.k = 0

    def node(self, tag):
        self.k += 1
        return f'{tag}~{self.k}'

    def add(self, kind, ports, init=None, name=None):
        name = name or f'{kind}{len(self.g)}'
        self.g[name] = dict(kind=kind, ports=dict(ports), init=init)
        return name

    def dio(self, u, v):
        return self.add('dio', {'A': u, 'B': v})


def netlist(inst):
    A, start, goal, init_open = arena(inst)
    N = Net()
    scd_of = {}
    tun = defaultdict(dict)                       # door -> {'O': x, 'I': x1, 'J': x2}
    for u, lst in A.edges.items():
        for kind, v, d in lst:
            if kind == 'plain':
                N.dio(u, v)
            elif kind == 'O':
                x = N.node('btn')
                N.dio(u, x)
                N.dio(x, v)
                assert 'O' not in tun[d], ('two O users on one SCD', d)
                tun[d]['O'] = x
            else:
                x1, x2 = N.node('si'), N.node('sj')
                N.dio(u, x1)
                N.dio(x2, v)
                assert 'I' not in tun[d], ('two S users on one SCD', d)
                tun[d]['I'], tun[d]['J'] = x1, x2
    for d in range(A.ndoor):
        ports = {p: tun[d].get(p) or N.node(f'free{p}') for p in 'OIJ'}
        scd_of[d] = N.add('scd', ports, 'o' if d in init_open else 'c', name=f'scd{d}')
    if A.coin:
        T, (Aa, Bb) = A.coin
        N.add('coin', {'E': T, 'A': Aa, 'B': Bb}, name='coin')
    N.start, N.goal = start, goal
    # t = c_m: the unique node with a diode into g
    t = [G['ports']['A'] for G in N.g.values() if G['kind'] == 'dio' and G['ports']['B'] == goal]
    assert len(t) == 1
    N.t = t[0]
    N.scd_of = scd_of
    return N


def solve_net(N, goal=None, xovers=None, cap=4_000_000):
    """exact attractor on the netlist with ideal gadgets: diode A->B, SCD button O (open, stay), I->J iff open
    (closes), coin E -> nature picks A or B. xovers: optional list of (name, System-like dict) -- ideal crossover
    nodes are given as extra 'xo' gadgets in N.g (ports A1, B1, A2, B2: A1->B1, A2->B2, stateless).
    Returns (hero wins from start, #positions)."""
    goal = goal or N.goal
    names = sorted(N.g)
    scds = [n for n in names if N.g[n]['kind'] == 'scd']
    bit = {n: i for i, n in enumerate(scds)}
    at = defaultdict(list)
    for n in names:
        for p, v in N.g[n]['ports'].items():
            at[v].append((n, p))
    b0 = sum(1 << bit[n] for n in scds if N.g[n]['init'] == 'o')
    coin = N.g.get('coin')
    idx, key, succ = {}, [], []
    dq = deque()

    def add(s):
        i = idx.get(s)
        if i is None:
            i = idx[s] = len(key)
            key.append(s)
            succ.append(None)
            dq.append(i)
        return i
    add((N.start, b0))
    isnat = []
    while dq:
        i = dq.popleft()
        u, b = key[i]
        out, nat = [], False
        if u != goal:
            for n, p in at[u]:
                G = N.g[n]
                k = G['kind']
                if k == 'dio' and p == 'A':
                    out.append(add((G['ports']['B'], b)))
                elif k == 'scd':
                    if p == 'O':
                        out.append(add((u, b | 1 << bit[n])))
                    elif p == 'I' and b >> bit[n] & 1:
                        out.append(add((G['ports']['J'], b & ~(1 << bit[n]))))
                elif k == 'xo' and p in ('A1', 'A2'):
                    out.append(add((G['ports']['B' + p[1]], b)))
                elif k == 'xnet':                    # crossover realized as its own SCD network (see layout_net)
                    pass
            if coin and u == coin['ports']['E']:
                # arriving at T: nature moves; T has no other move (Z2: T's only neighbour is E, a bounce = null)
                out = [add((coin['ports']['A'], b)), add((coin['ports']['B'], b))]
                nat = True
        succ[i] = sorted(set(out) - {i}) if not nat else sorted(set(out))
        isnat.append(nat)
        if len(key) > cap:
            raise RuntimeError('cap')
    while len(isnat) < len(key):
        isnat.append(False)
    n = len(key)
    pred = [[] for _ in range(n)]
    for i, s in enumerate(succ):
        for j in s:
            pred[j].append(i)
    win = [False] * n
    cnt = [len(s) for s in succ]
    q = deque(i for i in range(n) if key[i][0] == goal)
    for i in q:
        win[i] = True
    while q:
        j = q.popleft()
        for i in pred[j]:
            if win[i]:
                continue
            if isnat[i]:
                cnt[i] -= 1
                if cnt[i] == 0:
                    win[i] = True
                    q.append(i)
            else:
                win[i] = True
                q.append(i)
    return win[0], n


def stats(N):
    c = defaultdict(int)
    for G in N.g.values():
        c[G['kind']] += 1
    deg = defaultdict(int)
    for G in N.g.values():
        for v in G['ports'].values():
            deg[v] += 1
    c['nodes'] = len(deg)
    c['junctions(deg>=3)'] = sum(1 for d in deg.values() if d >= 3)
    return dict(c)


def contract(N):
    """merge diode chains: a node with exactly two attachments dio1.B, dio2.A (not start/goal/t) -> one diode."""
    while True:
        att = defaultdict(list)
        for n, G in N.g.items():
            for p, v in G['ports'].items():
                att[v].append((n, p))
        done = True
        for v, lst in att.items():
            if len(lst) != 2 or v in (N.start, N.goal, N.t):
                continue
            (n1, p1), (n2, p2) = lst
            if N.g[n1]['kind'] == N.g[n2]['kind'] == 'dio' and {p1, p2} == {'A', 'B'} and n1 != n2:
                a, b = (n1, n2) if p1 == 'B' else (n2, n1)          # a.B = v = b.A
                N.g[a]['ports']['B'] = N.g[b]['ports']['B']
                del N.g[b]
                done = False
                break
        if done:
            return N


# ============================================================ 4. bus layout (macro level)
import numpy as np

# top-port order of each tile kind (left to right). 'scdc' = SCD compound: v2 SCD tile + a local junction on its
# button O (the O-tunnel's private node: in-diode, button, out-diode), so the bidirectional button link never leaves
# the tile. Ports of scdc: Oin, Oout (towards the two diodes at the button node), I, J.
TILE_PORTS = {'scd': ['O', 'I', 'J'], 'dio': ['A', 'B'], 'coin': ['E', 'A', 'B']}
PDIR = {'scdc': {'Oin': 'in', 'Oout': 'out', 'I': 'in', 'J': 'out'}, 'scd': {'O': 'bi', 'I': 'in', 'J': 'out'},
        'dio': {'A': 'in', 'B': 'out'}, 'coin': {'E': 'in', 'A': 'out', 'B': 'out'}}
FLIP = {'in': 'out', 'out': 'in', 'bi': 'bi'}


class Bus:
    """tiles: name -> dict(kind, ports [(port, node, dir)]) left to right (dir as seen from the tile: 'in' = traffic
    enters the tile there). edges: dict(a=(tile, port), b=(tile, port), dir 'ab' (traffic a -> b) | 'bi', node).
    Junction tiles 'jn' (one per node of degree >= 3, and for start and t), ports p0.. ."""

    def __init__(self, N):
        self.N = N
        att = defaultdict(list)
        for n, G in N.g.items():
            for p, v in G['ports'].items():
                att[v].append((n, p))
        tiles = {}
        ends = defaultdict(list)                 # node -> [(tile, port, dir)]
        for n, G in N.g.items():
            k = G['kind']
            if k == 'dio' and G['ports']['B'] == N.goal:
                continue                         # c_m -> g: replaced by the check path (t = c_m, chain ends in g)
            if k == 'scd':
                x = G['ports']['O']
                others = [a for a in att[x] if a != (n, 'O')]
                ins = [a for a in others if N.g[a[0]]['kind'] == 'dio' and a[1] == 'B']
                outs = [a for a in others if N.g[a[0]]['kind'] == 'dio' and a[1] == 'A']
                if len(others) == 2 and len(ins) == 1 and len(outs) == 1 and x not in (N.start, N.goal, N.t):
                    # compound: the diode ports at x connect straight to the tile's Oin / Oout
                    tiles[n] = dict(kind='scdc', init=G['init'], btn=x,
                                    ports=[('Oin', ('cmp', n, 'Oin'), 'in'), ('Oout', ('cmp', n, 'Oout'), 'out'),
                                           ('I', G['ports']['I'], 'in'), ('J', G['ports']['J'], 'out')])
                    ends[('cmp', n, 'Oin')].append((ins[0][0], ins[0][1], 'out'))
                    ends[('cmp', n, 'Oout')].append((outs[0][0], outs[0][1], 'in'))
                    continue
            tiles[n] = dict(kind=k, init=G.get('init'),
                            ports=[(p, G['ports'][p], PDIR[k][p]) for p in TILE_PORTS[k]])
        btn = {T['btn'] for T in tiles.values() if T['kind'] == 'scdc'}
        moved = {(a[0], a[1]) for v in ends for a in ends[v]}
        for tn, T in tiles.items():
            for p, v, d in T['ports']:
                if v in btn or (tn, p) in moved:
                    continue
                ends[v].append((tn, p, d))
        self.dead, edges = [], []
        for v, es in ends.items():
            if len(es) == 1 and v not in (N.start, N.t):
                self.dead.append((v, es[0]))     # dangling port (an SCD tunnel without user): dead-end stub
                continue
            if len(es) >= 3 or v in (N.start, N.t):
                jn = f'jn[{v}]'
                tiles[jn] = dict(kind='jn', node=v, ports=[])
                for k, (tn, p, d) in enumerate(es):
                    q = f'p{k}'
                    tiles[jn]['ports'].append((q, v, FLIP[d]))
                    edges.append(self._edge((tn, p, d), (jn, q, FLIP[d]), v))
            else:
                edges.append(self._edge(es[0], es[1], v))
        self.tiles, self.edges = tiles, edges
        self.start_tile = f'jn[{N.start}]'
        self.t_tile = f'jn[{N.t}]'

    @staticmethod
    def _edge(e1, e2, v):
        (t1, p1, d1), (t2, p2, d2) = e1, e2
        if d1 == 'bi' or d2 == 'bi':
            return dict(a=(t1, p1), b=(t2, p2), dir='bi', node=v)
        if d1 == 'out' and d2 == 'in':
            return dict(a=(t1, p1), b=(t2, p2), dir='ab', node=v)
        if d1 == 'in' and d2 == 'out':
            return dict(a=(t2, p2), b=(t1, p1), dir='ab', node=v)
        raise AssertionError(('edge with incompatible directions', e1, e2, v))

    # ---------------- order of the bottom row
    def columns(self, order):
        col, x = {}, 0
        for tn in order:
            for p, *_ in self.tiles[tn]['ports']:
                col[(tn, p)] = x
                x += 1
        return col

    def crossings(self, order):
        col = self.columns(order)
        L = np.array([min(col[e['a']], col[e['b']]) for e in self.edges])
        Rr = np.array([max(col[e['a']], col[e['b']]) for e in self.edges])
        A = (L[:, None] < L[None, :]) & (L[None, :] < Rr[:, None]) & (Rr[:, None] < Rr[None, :])
        return int(A.sum())

    def order(self, iters=80, seed=0):
        rng = random.Random(seed)
        nb = defaultdict(list)
        for e in self.edges:
            nb[e['a'][0]].append(e['b'][0])
            nb[e['b'][0]].append(e['a'][0])
        seen, order = set(), []
        for root in [self.start_tile] + sorted(self.tiles):
            if root in seen:
                continue
            st = [root]
            while st:                                    # DFS keeps chains (write paths) together
                u = st.pop()
                if u in seen:
                    continue
                seen.add(u)
                order.append(u)
                st.extend(w for w in reversed(nb[u]) if w not in seen)
        best = (self.crossings(order), list(order))
        cur = list(order)
        for it in range(iters):
            pos = {t: i for i, t in enumerate(cur)}
            bary = {t: (sum(pos[w] for w in nb[t]) / len(nb[t]) if nb[t] else pos[t]) + rng.random() * 0.5
                    for t in cur}
            cur = sorted(cur, key=lambda t: 0.5 * pos[t] + 0.5 * bary[t])
            c = self.crossings(cur)
            if c < best[0]:
                best = (c, list(cur))
        cur = best[1]
        improved = True
        while improved:
            improved = False
            for i in range(len(cur) - 1):
                cand = cur[:i] + [cur[i + 1], cur[i]] + cur[i + 2:]
                c = self.crossings(cand)
                if c < best[0]:
                    best, cur, improved = (c, cand), cand, True
        self.order_ = best[1]
        return best[0]

    # ---------------- rows (tracks) and crossings
    def rows(self):
        col = self.col = self.columns(self.order_)
        span = [(min(col[e['a']], col[e['b']]), max(col[e['a']], col[e['b']])) for e in self.edges]
        idx = sorted(range(len(self.edges)), key=lambda i: span[i][1] - span[i][0])
        row = {}
        for i in idx:
            l, r = span[i]
            lo = 1 + max([row[j] for j in row if l < span[j][0] and span[j][1] < r] or [0])
            busy = {row[j] for j in row if not (span[j][1] < l or r < span[j][0])}
            k = lo
            while k in busy:
                k += 1
            row[i] = k
        for i in row:
            for j in row:
                if span[i][0] < span[j][0] and span[j][1] < span[i][1]:
                    assert row[j] < row[i]
        self.span, self.row = span, row
        X = []
        for i, e in enumerate(self.edges):           # e's track (row[i]) crosses f's column at x
            l, r = span[i]
            for j, f in enumerate(self.edges):
                if i != j:
                    for end in ('a', 'b'):
                        x = col[f[end]]
                        if l < x < r and row[i] < row[j]:
                            X.append(dict(track=i, col=x, colEdge=j, end=end, row=row[i]))
        for c in X:
            assert self.edges[c['track']]['dir'] != 'bi' and self.edges[c['colEdge']]['dir'] != 'bi', 'bidir crossed'
        self.X = X
        return len(X), max(row.values()) if row else 0


# ============================================================ 5. concrete blocks (P x P cells; tiles k*P x P)
import X_build as XB

P, MID = 587, 293                     # macro pitch (fits the 556 x 560 r6b crossover under every flip, margin >= 4; r6a: 597, 298 for 569 x 550; r5: 469, 234)
JN_GEOM = os.environ.get('LGEN_JN', 'bar')     # junction comb: 'bar' (r6b, uniform in the degree) or 'fan' (r5/r6a)
LANES = (2, P - 3)                    # chain lane rows inside every block (top, bottom)
XDIR = os.path.join(ROOT, 'build', 'xover')
SIDE_CELL = {'T': (MID, 0), 'B': (MID, P - 1), 'L': (0, MID), 'R': (P - 1, MID)}


class Block:
    """concrete block: floor {(x, y): ch} ('.', '0', 'T'), owner {(x, y): tuple}, arms {side: True};
    placed tiles (for the check path): list of dicts in block coordinates (cells, comps, legs, checks, kind)."""

    def __init__(self, kind, W=P, H=P):
        self.kind, self.W, self.H = kind, W, H
        self.floor, self.owner, self.arms, self.tiles = {}, {}, {}, []

    def put(self, c, ch, own):
        assert 0 <= c[0] < self.W and 0 <= c[1] < self.H, ('outside block', c, self.kind)
        assert c not in self.floor or self.owner[c] == own, ('overlap', c, own, self.owner.get(c), self.kind)
        self.floor[c] = ch
        self.owner[c] = own

    def line(self, a, b, own):
        (x0, y0), (x1, y1) = a, b
        assert x0 == x1 or y0 == y1
        for x in range(min(x0, x1), max(x0, x1) + 1):
            for y in range(min(y0, y1), max(y0, y1) + 1):
                self.put((x, y), '.', own)


def corridor_block(kind):
    """'V', 'H', 'BL' (bottom + left arm), 'BR' (bottom + right arm), 'E' (empty)"""
    b = Block(kind)
    own = ('corr', kind)
    if kind == 'V':
        b.line((MID, 0), (MID, P - 1), own)
        b.arms = {'T': 1, 'B': 1}
    elif kind == 'H':
        b.line((0, MID), (P - 1, MID), own)
        b.arms = {'L': 1, 'R': 1}
    elif kind in ('BL', 'BR'):
        b.line((MID, MID), (MID, P - 1), own)
        b.line((MID, MID), ((0 if kind == 'BL' else P - 1), MID), own)
        b.arms = {'B': 1, ('L' if kind == 'BL' else 'R'): 1}
    return b


_XMAP = None


def xmap():
    global _XMAP
    if _XMAP is None:
        rows = open(os.path.join(XDIR, 'crossover.txt')).read().split('\n')
        j = json.load(open(os.path.join(XDIR, 'crossover.json')))
        _XMAP = (rows, j)
    return _XMAP


def x_block(fx, fy):
    """v2 crossover map flipped (fx: horizontal passage right->left; fy: vertical passage bottom->top), ports on
    the block midlines, straight stubs to the border. Passages: horizontal A1 -> B1, vertical A2 -> B2."""
    rows, j = xmap()
    W, H = j['W'], j['H']
    f = lambda x, y: (W - 1 - x if fx else x, H - 1 - y if fy else y)
    ext = {k: f(*v) for k, v in j['ext'].items()}
    ox, oy = MID - ext['A2'][0], MID - ext['A1'][1]
    assert ext['B2'][0] == ext['A2'][0] and ext['B1'][1] == ext['A1'][1]
    b = Block(('X', fx, fy))
    tcell = {}
    for tid, t in j['tiles'].items():
        for c in t['cells']:
            tcell[tuple(c)] = tid
    for y, r in enumerate(rows):
        for x, ch in enumerate(r):
            if ch in '.0':
                gx, gy = f(x, y)
                tid = tcell.get((x, y))
                b.put((gx + ox, gy + oy), ch, ('xtile', tid) if tid else ('xcorr',))
    for k, (x, y) in ext.items():
        c = (x + ox, y + oy)
        side = 'L' if x == 0 else 'R' if x == W - 1 else 'T' if y == 0 else 'B'
        d = {'L': (-1, 0), 'R': (1, 0), 'T': (0, -1), 'B': (0, 1)}[side]
        c = (c[0] + d[0], c[1] + d[1])
        b.line(c, (c[0] if side in 'TB' else (0 if side == 'L' else P - 1),
                   c[1] if side in 'LR' else (0 if side == 'T' else P - 1)), ('xstub', k))
        b.arms[side] = k
    b.xoff, b.xflip = (ox, oy), (fx, fy)
    b.passage = {('L', 'R') if not fx else ('R', 'L'): 'h', ('T', 'B') if not fy else ('B', 'T'): 'v'}
    # placed tiles of the crossover in block coordinates (for the check path)
    for tid, t in j['tiles'].items():
        g = lambda c: (f(*c)[0] + ox, f(*c)[1] + oy)
        b.tiles.append(dict(id=tid, kind=t['kind'], cells=[g(c) for c in t['cells']],
                            zones=[g(c) for pp in t['ports'].values() for c in pp['zone']],
                            comps=[dict(name=cm['name'], kind=cm['kind'], cells=[g(c) for c in cm['cells'].values()])
                                   for cm in t['comps']],
                            checks={k: [g(c) for c in v] for k, v in t['checks'].items()},
                            legs={k: dict(gside=g(L['gside']), Wb=g(L['Wb']), Wt=g(L['Wt']),
                                          mid=[g(c) for c in L['mid']], cells=[g(c) for c in L['cells']],
                                          stub=[g(c) for c in L.get('stub', [])])
                                  for k, L in t['legs'].items()}))
    return b


def place_local(T, s):
    """apply symmetry s to a v2 Tile; returns (W, H, cells {c: ch}, owner {c: own}, ports {p: c}, legs, checks,
    comps [(name, kind, [cells])])"""
    W, H = XB.sym_size(s, T.W, T.H)
    g = lambda c: XB.sym(s, c[0], c[1], T.W, T.H)
    cells = {g(c): ch for c, ch in T.cells.items()}
    owner = {g(c): o for c, o in T.owner.items()}
    ports = {p: g(c) for p, (c, d, z) in T.ports.items()}
    legs = {l: dict(gside=g(L['gside']), Wb=g(L['Wb']), Wt=g(L['Wt']), mid=[g(c) for c in L['mid']],
                    cells=[g(c) for c in L['cells']], stub=[g(c) for c in L.get('stub', [])])
            for l, L in T.legs.items()}
    checks = {k: [g(c) for c in v] for k, v in T.checks.items()}
    comps = [(n, k, [g(c) for c in cm.values()]) for n, k, cm in XB.local_comps(T)]
    return W, H, cells, owner, ports, legs, checks, comps


COIN = ["e###a###b",
        ".###.###.",
        ".###.###.",
        ".###.###.",
        ".###.###.",
        ".###.###.",
        ".###A#T#B",
        ".#####.##",
        ".#####.##",
        ".......##"]


def fan(b, vports, own_of):
    """vports: [(port, (x, y), target_x or None)] (x ascending): explicit nested L-shaped stubs (left-goers: the
    leftmost turns lowest; right-goers: the rightmost turns lowest), 1-wide, then up to the top border."""
    vports = [(p, (c[0], c[1] - 1), t) for p, c, t in vports]      # stubs start just above the port cell
    y0 = min(c[1] for _, c, _ in vports) - 3
    L = [(p, c, t) for p, c, t in vports if t is not None and t < c[0]]
    R = [(p, c, t) for p, c, t in vports if t is not None and t > c[0]]
    S = [(p, c, t) for p, c, t in vports if t is not None and t == c[0]]
    for j, (p, c, t) in enumerate(L):
        yt = y0 - 2 * j
        b.line(c, (c[0], yt), own_of(p))
        b.line((c[0], yt), (t, yt), own_of(p))
        b.line((t, yt), (t, 0), own_of(p))
    for j, (p, c, t) in enumerate(reversed(R)):
        yt = y0 - 2 * j
        b.line(c, (c[0], yt), own_of(p))
        b.line((c[0], yt), (t, yt), own_of(p))
        b.line((t, yt), (t, 0), own_of(p))
    for p, c, t in S:
        b.line(c, (t, 0), own_of(p))


def build_tile_block(Bs, tn):
    """concrete block of bottom-row tile tn of Bus Bs"""
    T = Bs.tiles[tn]
    k = T['kind']
    ports = [p for p, *_ in T['ports']]
    kc = len(ports)
    b = Block(('tile', tn, k), kc * P, P)
    used = {(e['a']) for e in Bs.edges} | {(e['b']) for e in Bs.edges}
    tgt = {p: (i * P + MID if (tn, p) in used else None) for i, p in enumerate(ports)}
    own_of = lambda p: ('stub', tn, p)
    base_y = P - 14                       # body bottom row
    if k in ('scdc', 'scd'):
        Tl = XB.scd_tile(0)
        W, H, cells, owner, lp, legs, checks, comps = place_local(Tl, 7)        # ports O, I, J on top
        bx, by = (kc * P) // 2 - W // 2, base_y - H + 1
        tr = lambda c: (c[0] + bx, c[1] + by)
        # boulders: scd_tile(0) is CLOSED (precursor track 3,5); an OPEN door has the precursor blocks on 4,6
        cl = {}
        for c, ch in cells.items():
            cl[c] = ch
        if T.get('init') == 'o':
            prec = [cm for cm in comps if cm[0] == 'prec'][0]
            # precursor local board coords -> placed: rebuild via the component's local map
            _, kind_, pcs = prec
            Tl0 = XB.scd_tile(0)
            ox, oy = [o for n_, k_, o in Tl0.comps if n_ == 'prec'][0]
            for (lx, ly) in [(3, 2), (5, 2)]:
                cl[XB.sym(7, ox + lx, oy + ly, Tl0.W, Tl0.H)] = '.'
            for (lx, ly) in [(4, 2), (6, 2)]:
                cl[XB.sym(7, ox + lx, oy + ly, Tl0.W, Tl0.H)] = '0'
        for c, ch in cl.items():
            b.put(tr(c), ch, ('tile', tn) + tuple(owner[c]))
        vports = []
        if k == 'scdc':
            o = tr(lp['O'])
            yj = o[1] - 3
            b.line((o[0], o[1] - 1), (o[0], yj), ('btn', tn))   # O's link up to the button junction
            b.line((o[0] - 6, yj), (o[0], yj), ('btn', tn))
            vports += [('Oin', (o[0] - 6, yj), tgt['Oin']), ('Oout', (o[0], yj), tgt['Oout'])]
        else:
            vports.append(('O', tr(lp['O']), tgt['O']))
        vports += [('I', tr(lp['I']), tgt['I']), ('J', tr(lp['J']), tgt['J'])]
        fan(b, sorted(vports, key=lambda v: v[1][0]), own_of)
        b.tiles.append(dict(id=tn, kind='scd', cells=[tr(c) for c in cells],
                            zones=[tr(c) for c, o in owner.items() if o[0] == 'tport'],
                            comps=[dict(name=n_, kind=k_, cells=[tr(c) for c in cs]) for n_, k_, cs in comps],
                            checks={kk: [tr(c) for c in v] for kk, v in checks.items()},
                            legs={l: dict(gside=tr(L['gside']), Wb=tr(L['Wb']), Wt=tr(L['Wt']),
                                          mid=[tr(c) for c in L['mid']], cells=[tr(c) for c in L['cells']],
                                          stub=[tr(c) for c in L.get('stub', [])])
                                  for l, L in legs.items()}))
    elif k == 'dio':
        Tl = XB.diode_tile()
        W, H, cells, owner, lp, legs, checks, comps = place_local(Tl, 0)
        bx, by = (kc * P) // 2 - W // 2, base_y - H + 1
        tr = lambda c: (c[0] + bx, c[1] + by)
        for c, ch in cells.items():
            b.put(tr(c), ch, ('tile', tn) + tuple(owner[c]))
        fan(b, sorted([(p, tr(lp[p]), tgt[p]) for p in ('A', 'B')], key=lambda v: v[1][0]), own_of)
        b.tiles.append(dict(id=tn, kind='dio', cells=[tr(c) for c in cells],
                            zones=[tr(c) for c, o in owner.items() if o[0] == 'tport'],
                            comps=[dict(name=n_, kind=k_, cells=[tr(c) for c in cs]) for n_, k_, cs in comps],
                            checks={kk: [tr(c) for c in v] for kk, v in checks.items()},
                            legs={l: dict(gside=tr(L['gside']), Wb=tr(L['Wb']), Wt=tr(L['Wt']),
                                          mid=[tr(c) for c in L['mid']], cells=[tr(c) for c in L['cells']],
                                          stub=[tr(c) for c in L.get('stub', [])])
                                  for l, L in legs.items()}))
    elif k == 'coin':
        W, H = len(COIN[0]), len(COIN)
        bx, by = (kc * P) // 2 - W // 2, base_y - H + 1
        tr = lambda c: (c[0] + bx, c[1] + by)
        lp = {}
        for y, r in enumerate(COIN):
            for x, ch in enumerate(r):
                if ch == '#':
                    continue
                own = {'T': ('coin', 'T'), 'A': ('coin', 'A'), 'B': ('coin', 'B')}.get(ch, ('coin', 'corr'))
                b.put(tr((x, y)), 'T' if ch == 'T' else '.', ('tile', tn) + own)
                if ch in 'eab':
                    lp[ch.upper()] = tr((x, y))
                if ch in 'TAB':
                    lp['Z' + ch] = tr((x, y))
        b.coin = dict(T=lp['ZT'], A=lp['ZA'], B=lp['ZB'], E=tr((6, 7)), XA=tr((4, 5)), XB=tr((8, 5)))
        fan(b, sorted([(p, lp[p], tgt[p]) for p in ('E', 'A', 'B')], key=lambda v: v[1][0]), own_of)
    elif k == 'jn' and JN_GEOM == 'bar':
        # r6b (F4): uniform comb for every degree n: one horizontal bar under all n port columns, one straight tooth
        # per port up to the top border; no nested fan, so no row of the block depends on n (the fan's j-th turn row
        # P - 20 - 2j would reach lane row 2 for n > ~560). LGEN_JN=fan restores the old fan comb.
        n = len(ports)
        by = base_y - 2
        xs = [i * P + MID for i in range(n)]
        b.line((xs[0], by + 2), (max(xs[-1], xs[0] + 2), by + 2), ('jn', tn))
        for i, p in enumerate(ports):
            if tgt[p] is not None:
                b.line((xs[i], 0), (xs[i], by + 1), own_of(p))
        b.jn_cell = (xs[0], by + 2)                              # start cell / t's chain attachment (below it)
    elif k == 'jn':
        n = len(ports)
        bx, by = (kc * P) // 2 - (n - 1), base_y - 2
        for i in range(n):
            b.line((bx + 2 * i, by), (bx + 2 * i, by + 2), ('jn', tn))
        b.line((bx, by + 2), (bx + 2 * (n - 1), by + 2), ('jn', tn))
        if n == 1:
            b.line((bx, by + 2), (bx + 2, by + 2), ('jn', tn))
        fan(b, [(ports[i], (bx + 2 * i, by), tgt[ports[i]]) for i in range(n)], own_of)
        b.jn_cell = (bx, by + 2)                                 # start cell / t's chain attachment (below it)
    else:
        raise ValueError(k)
    for i, p in enumerate(ports):
        if tgt[p] is not None:
            b.arms[('T', i)] = 1
    return b


def check_block(b):
    """local locality contract of one block: (1) floor on the border ring only at arm midpoints, arms straight for
    3 cells with wall beside; (2) floor 8-components: one per intended net (owner class), different owners never
    8-adjacent except at the intended joins (tile internals checked by X_build/X_verify contracts)."""
    W, H = b.W, b.H
    mids = set()
    for a in b.arms:
        if isinstance(a, tuple):
            mids.add((a[1] * P + MID, 0))
        else:
            mids.add(SIDE_CELL[a] if b.W == P else None)
    for (x, y) in b.floor:
        if x in (0, W - 1) or y in (0, H - 1):
            assert (x, y) in mids, ('floor on border ring off an arm', b.kind, (x, y))
    for (mx, my) in mids:
        d = (0, 1) if my == 0 else (0, -1) if my == H - 1 else (1, 0) if mx == 0 else (-1, 0)
        for k in range(3):
            c = (mx + d[0] * k, my + d[1] * k)
            assert c in b.floor, ('arm not straight', b.kind, c)
            side = [(c[0] + d[1], c[1] + d[0]), (c[0] - d[1], c[1] - d[0])]
            assert all(s not in b.floor for s in side), ('arm has a floor neighbour', b.kind, c)
    return True


# ============================================================ 6. the level: macro grid of blocks
OPP = {'L': 'R', 'R': 'L', 'T': 'B', 'B': 'T'}
THROUGH = {'V': {'B': 'T', 'T': 'B'}, 'H': {'L': 'R', 'R': 'L'}, 'BL': {'B': 'L', 'L': 'B'},
           'BR': {'B': 'R', 'R': 'B'}}
STEP = {'L': (-1, 0), 'R': (1, 0), 'T': (0, 1), 'B': (0, -1)}         # macro (col, row): row grows upward


class Level:
    """macro grid: cell (c, r), c = column (port index), r = 0 tile row, 1.. track rows. kinds: 'V', 'H', 'BL', 'BR',
    ('X', fx, fy), tile pieces ('tile', tn, i). Concrete coordinates: block (c, r) has its top-left cell at
    ((c + 1) * P, (R - r) * P) with R = top row; column -1 / C are margins (chain only)."""

    def __init__(self, Bs):
        self.Bs = Bs
        col, row = Bs.col, Bs.row
        self.C = len(col)
        self.R = max(row.values()) if row else 0
        g = {}

        def setc(c, r, k):
            old = g.get((c, r))
            if old is None:
                g[(c, r)] = k
                return
            pair = {old[0] if isinstance(old, tuple) else old, k[0] if isinstance(k, tuple) else k}
            raise AssertionError(('macro cell conflict', (c, r), old, k))
        hdir, vdir = {}, {}
        for i, e in enumerate(Bs.edges):
            xa, xb, r = col[e['a']], col[e['b']], row[i]
            for x, up in ((xa, True), (xb, False)):
                for rr in range(1, r):
                    vdir.setdefault((x, rr), []).append(('up' if up else 'down', i))
                setc(x, r, 'BR' if (xb > xa) == (x == xa) else 'BL')
            for x in range(min(xa, xb) + 1, max(xa, xb)):
                hdir.setdefault((x, r), []).append(('right' if xb > xa else 'left', i))
        for (x, r), v in vdir.items():
            assert len(v) == 1 and (x, r) not in g, ('vertical conflict', x, r)
            if (x, r) in hdir:
                (hd, i), = hdir[(x, r)]
                (vd, j), = v
                g[(x, r)] = ('X', hd == 'left', vd == 'up')       # fx: right->left; fy: bottom->top
                self.Xedges = getattr(self, 'Xedges', {})
                self.Xedges[(x, r)] = (i, j)
            else:
                g[(x, r)] = 'V'
        for (x, r), v in hdir.items():
            assert len(v) == 1, ('horizontal conflict', x, r)
            if (x, r) not in g:
                g[(x, r)] = 'H'
            else:
                assert g[(x, r)][0] == 'X', ('track over a corner', x, r, g[(x, r)])
        x0 = 0
        self.tile_at = {}
        for tn in Bs.order_:
            k = len(Bs.tiles[tn]['ports'])
            for i in range(k):
                g[(x0 + i, 0)] = ('tile', tn, i)
            self.tile_at[tn] = x0
            x0 += k
        self.g = g
        self.nX = sum(1 for k in g.values() if k[0] == 'X')

    # ---------------- block library + compositional checks
    def blocks(self):
        lib = {}
        for k in set(v for v in self.g.values() if v[0] != 'tile'):
            lib[k] = x_block(k[1], k[2]) if k[0] == 'X' else corridor_block(k)
        tb = {tn: build_tile_block(self.Bs, tn) for tn in self.Bs.tiles}
        self.lib, self.tb = lib, tb
        return lib, tb

    def check_static(self):
        """(1) every block type passes check_block; (2) arms match between neighbouring macro cells (a corridor leaves
        a block at a side midpoint iff the neighbour has the matching arm), so floor cells of different blocks are
        8-adjacent only along matched arms; (3) tile blocks: stub/body separation."""
        for k, b in self.lib.items():
            check_block(b)
        for tn, b in self.tb.items():
            check_block(b)
            check_tile_block(b)
        bad = 0
        for (c, r), k in self.g.items():
            arms = self.arms_of(c, r)
            for s in arms:
                dc, dr = STEP[s]
                nb = (c + dc, r + dr)
                assert OPP[s] in self.arms_of(*nb), ('unmatched arm', (c, r), s, k, self.g.get(nb))
        # cells with no block entry are empty; their neighbours must not point into them (checked above)
        return True

    def arms_of(self, c, r):
        k = self.g.get((c, r))
        if k is None:
            return set()
        if k[0] == 'tile':
            tn, i = k[1], k[2]
            return {'T'} if ('T', i) in self.tb[tn].arms else set()
        b = self.lib[k]
        return {s for s in b.arms}

    # ---------------- S2: reconstruct the network from the concrete wiring
    def trace(self):
        Bs = self.Bs
        Xuse = defaultdict(list)
        paths = []
        for i, e in enumerate(Bs.edges):
            c, r = Bs.col[e['a']], 1
            ent = 'B'
            seq = []
            while r > 0:
                k = self.g[(c, r)]
                if k[0] == 'X':
                    ex = OPP[ent]
                    seq.append(((c, r), ent, ex))
                    Xuse[(c, r)].append(i)
                else:
                    ex = THROUGH[k][ent]
                dc, dr = STEP[ex]
                c, r = c + dc, r + dr
                ent = OPP[ex]
            assert ent == 'T' and c == Bs.col[e['b']], ('edge does not arrive at its target port', i)
            paths.append(seq)
        for xy, lst in Xuse.items():
            assert len(lst) == 2, ('crossover not used by exactly two edges', xy, lst)
        return paths

    def network(self, paths, flip=False):
        """Net (solve_net format) from the traced wiring: tiles as gadgets, every crossover as an ideal directed
        crossover 'xo' whose passages follow the PLACED variant's flips (a mis-oriented copy blocks the edge)."""
        Bs, N0 = self.Bs, self.Bs.N
        Nn = Net()
        shared = {}
        for tn, T in Bs.tiles.items():
            if T['kind'] == 'jn':
                for p, *_ in T['ports']:
                    shared[(tn, p)] = f'J:{tn}'
            elif T['kind'] == 'scdc':
                shared[(tn, 'Oin')] = shared[(tn, 'Oout')] = f'btn:{tn}'
        end = {}
        for i, e in enumerate(Bs.edges):
            seq = paths[i]
            sa, sb = shared.get(e['a']), shared.get(e['b'])
            if not seq:
                assert not (sa and sb), ('edge between two shared nodes', e)
                end[e['a']] = end[e['b']] = sa or sb or f'e{i}'
                continue
            nodes = [sa or f'e{i}a'] + [f'e{i}.{k}' for k in range(len(seq) - 1)] + [sb or f'e{i}b']
            for k, (xy, ent, ex) in enumerate(seq):
                b = self.lib[self.g[xy]]
                G = Nn.g.setdefault(f'xo{xy}', dict(kind='xo', ports={}, init=None))
                kind = b.passage.get((ent, ex)) or b.passage.get((ex, ent))
                assert kind, ('crossing does not go straight through', xy)
                pa, pb = ('A1', 'B1') if kind == 'h' else ('A2', 'B2')
                if ((ent, ex) not in b.passage) != flip:        # mis-oriented copy: traffic would bounce
                    pa, pb = pb, pa
                assert pa not in G['ports'] and pb not in G['ports'], ('crossover passage used twice', xy)
                G['ports'][pa], G['ports'][pb] = nodes[k], nodes[k + 1]
            end[e['a']], end[e['b']] = nodes[0], nodes[-1]
        node = lambda tn, p: shared.get((tn, p)) or end.get((tn, p)) or f'dead:{tn}.{p}'
        for tn, T in Bs.tiles.items():
            k = T['kind']
            if k == 'jn':
                continue
            if k == 'scdc':
                Nn.add('scd', {'O': f'btn:{tn}', 'I': node(tn, 'I'), 'J': node(tn, 'J')}, T['init'], name=tn)
            else:
                Nn.add(k, {p: node(tn, p) for p, *_ in T['ports']}, T.get('init'), name=tn)
        Nn.start, Nn.goal = f'J:{Bs.start_tile}', f'J:{Bs.t_tile}'
        if Bs.start_tile not in Bs.tiles:
            raise AssertionError('start is not a junction tile')
        return Nn


def check_tile_block(b):
    """tile block contract: different owners (stub of port p, stub of port q, tile body, button junction, coin
    parts) are 8-adjacent only at the intended join cells: a stub touches only its own port cell of the body."""
    own = b.owner

    def cls(o):
        if o[0] == 'stub':
            return ('stub', o[2])
        if o[0] in ('btn', 'jn'):
            return (o[0],)
        return ('body',)
    joins = 0
    for (x, y), o in own.items():
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                n = (x + dx, y + dy)
                if (dx or dy) and n in own and cls(own[n]) != cls(o):
                    a, bb = sorted([cls(o), cls(own[n])])
                    ok = ((a[0] == 'body' and bb[0] == 'stub') or (a[0] == 'body' and bb[0] == 'btn') or
                          (a[0] == 'btn' and bb[0] == 'stub') or (a[0] == 'jn' and bb[0] == 'stub'))
                    assert ok, ('unintended adjacency in tile block', b.kind, (x, y), n, o, own[n])
                    joins += 1
    # each stub touches the rest in exactly one place (its port): count distinct contact cells per stub
    contact = defaultdict(set)
    for (x, y), o in own.items():
        if o[0] != 'stub':
            continue
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                n = (x + dx, y + dy)
                if n in own and own[n][0] != 'stub':
                    contact[o[2]].add(n)
    for p, cs in contact.items():
        assert 1 <= len(cs) <= 3, ('stub touches the body in more than one place', b.kind, p, sorted(cs))
    return True


# ============================================================ 7. the check path (B2 §3, Thm 5.3 + Lemma 5.6)
import heapq

PP_CHECKS = [('A', 'D'), ('C', 'G'), ('B', 'A'), ('B', 'C')]
PD_CHECKS = [('A', 'C'), ('D', 'B')]
SCD_CHECKS = [('O', 'O'), ('I', 'J')]
PP_L, PD_L = ['A', 'B', 'C', 'E', 'F'], ['A', 'B', 'C', 'D']
# floor roles
WALL, WIN, SLOT, MIDR, SCDINT, LOC, CORR, COINC, GXR = range(9)
JUMP = 30                         # Dijkstra cost of one crossing (CHX / SX), steps cost 1
WIRE_PEN = int(os.environ.get('LGEN_WIRE_PEN', '4'))    # cost per wire step (box -> location), review 6 F2


def gprimes(tiles, level):
    """the Thm 5.3 wrappers of one block, as dicts: level, tile, name, legs [(leg, Wt, Wb)], locs {loc: cell}, scd"""
    out = []
    for t in tiles:
        if level == 1 and t['kind'] == 'scd':
            out.append(dict(level=1, tile=t['id'], name='scd', scd=t['id'], ckind='scd',
                            tcells=[tuple(c) for c in t['cells']],
                            legs=[(f'tile.{p}', t['legs'][f'tile.{p}']['Wt'], t['legs'][f'tile.{p}']['Wb'])
                                  for p in 'OIJ'],
                            locs={p: t['checks'][f'scd.{p}'][0] for p in 'OIJ'}, checks=SCD_CHECKS,
                            center=_centroid(set(map(tuple, t['cells'])) - set(map(tuple, t['zones']))),
                            gcells=sorted(set(map(tuple, t['cells'])) - set(map(tuple, t['zones'])) -
                                          {tuple(c) for p in 'OIJ' for c in t['legs'][f'tile.{p}']['cells']})))
        if level == 2:
            for cm in t['comps']:
                n, k = cm['name'], cm['kind']
                L, C = (PP_L, PP_CHECKS) if k == 'pp' else (PD_L, PD_CHECKS)
                locn = sorted({x for c in C for x in c})
                out.append(dict(level=2, tile=t['id'], name=n, scd=t['id'] if t['kind'] == 'scd' else None, ckind=k,
                                tcells=[tuple(c) for c in t['cells']],
                                legs=[(f'{n}.{p}', t['legs'][f'{n}.{p}']['Wt'], t['legs'][f'{n}.{p}']['Wb'])
                                      for p in L],
                                # leg locations: the leg's g-side (crossover.json 'checks' of diode tiles are
                                # shifted by one cell: X_build.diode_tile reads cport before finish()); pockets
                                # D, G of a proto-precursor: 'checks' (correct for SCD tiles)
                                locs={p: (t['legs'][f'{n}.{p}']['gside'] if f'{n}.{p}' in t['legs']
                                          else t['checks'][f'{n}.{p}'][0]) for p in locn}, checks=C,
                                center=_centroid(cm['cells']), gcells=[tuple(c) for c in cm['cells']]))
    return out


def _centroid(cells):
    cells = list(cells)
    return (sum(c[0] for c in cells) / len(cells), sum(c[1] for c in cells) / len(cells))


def ring_order(G, rot=1, gap=0):
    """legs sorted by angle around the G' centre, starting after the widest angular gap (Thm 5.3: pass 1 sweeps
    the spokes in one rotational sense, pass 2 back in the other, so the head ends in the gap sector next to G)"""
    import math
    cx, cy = G['center']
    ang = {ln: math.atan2(wt[1] - cy, wt[0] - cx) for ln, wt, wb in G['legs']}
    order = sorted(G['legs'], key=lambda L: ang[L[0]])
    if len(order) > 1:
        gaps = sorted([((ang[order[(i + 1) % len(order)][0]] - ang[order[i][0]]) % (2 * math.pi), i)
                       for i in range(len(order))], reverse=True)
        g, i = gaps[min(gap, len(gaps) - 1)]
        order = order[i + 1:] + order[:i + 1]
    return order if rot == 1 else order[::-1]


class Router:
    """chain = planar curve through wall-cell centres; it crosses a floor cell f only by a straight jump w1 f w2
    (w1, w2 walls, every floor 8-neighbour of f on the two sides of the jump line, both sides non-empty), which
    cuts f's corridor in two (the gadget placed there after a blow-up: delimiter WCX on a leg slot, CHX = WCX on any
    other corridor, never a window / location / coin cell); it crosses itself only by jumping a straight piece of
    its own earlier trace (SX, earlier traversal first). Every move is recorded."""

    def __init__(self, b, coin=None):
        """doubled-resolution grid: original cell (x, y) -> centre (2x+1, 2y+1); the point between two 4-adjacent
        floor cells is a floor LINK; a corner point is floor (never crossable) if a diagonal hero move passes it.
        The chain lives on non-floor points, so two crossings near one corner never compete for one wall cell."""
        self.b = b
        W0, H0 = b.W, b.H
        self.W0 = W0
        W, H = self.W, self.H = 2 * W0 + 1, 2 * H0 + 1
        n = W * H
        R = self.R
        ro, leg, scd = {}, {}, {}
        for c in b.floor:
            ro[c] = CORR
        gsl = {}                                         # (gside, Wb) pairs -> leg
        for t in b.tiles:
            tid = t['id']
            zones = set(map(tuple, t['zones']))
            legcells = {tuple(c) for L in t['legs'].values() for c in [L['Wb'], L['Wt']] + L['mid']}
            # review-6 scaled SCD tile: g-side stub cells (port .. g-side) are the port's location region; the
            # stubbed g-side itself is the check location (LOC, never crossed)
            stubs = {tuple(c): (tid, ln) for ln, L in t['legs'].items() for c in L.get('stub', [])}
            sgs = {tuple(L['gside']) for L in t['legs'].values() if L.get('stub')}
            for c in map(tuple, t['cells']):
                if t['kind'] == 'scd' and c not in zones and c not in legcells:
                    ro[c] = SCDINT
                    scd[c] = tid
            for cm in t['comps']:
                for c in map(tuple, cm['cells']):
                    ro[c] = WIN
            for c, lg in stubs.items():
                ro[c] = GXR
                leg[c] = lg
            for c in sgs:
                ro[c] = LOC
            for ln, L in t['legs'].items():
                for c in (L['Wb'], L['Wt']):
                    ro[tuple(c)] = SLOT
                    leg[tuple(c)] = (tid, ln)
                for c in L['mid']:
                    ro[tuple(c)] = MIDR
                    leg[tuple(c)] = (tid, ln)
                    if t['kind'] == 'scd' and not ln.startswith('tile.'):
                        scd[tuple(c)] = tid
                gsl[frozenset((tuple(L['gside']), tuple(L['Wb'])))] = (tid, ln)
            if t['kind'] == 'scd':
                for p in 'OIJ':
                    ro[tuple(t['checks'][f'scd.{p}'][0])] = LOC
        if coin:
            for k in ('T', 'A', 'B'):
                ro[tuple(coin[k])] = COINC
        self.fl = bytearray(n)
        self.role = bytearray(n)
        self.scd, self.leg = {}, {}
        for c, r in ro.items():
            i = R(c)
            self.fl[i], self.role[i] = 1, r
            if c in leg:
                self.leg[i] = leg[c]
            if c in scd:
                self.scd[i] = scd[c]
        # links between 4-adjacent floor cells
        for c in ro:
            for d in ((1, 0), (0, 1)):
                c2 = (c[0] + d[0], c[1] + d[1])
                if c2 not in ro:
                    continue
                i = (2 * c[1] + 1 + d[1]) * W + (2 * c[0] + 1 + d[0])
                self.fl[i] = 1
                r1, r2 = ro[c], ro[c2]
                pair = {r1, r2}
                key = frozenset((c, c2))
                if key in gsl:
                    self.role[i] = GXR
                    self.leg[i] = gsl[key]
                elif r1 == GXR and r2 == GXR:          # link inside one g-side stub
                    assert leg[c] == leg[c2]
                    self.role[i] = GXR
                    self.leg[i] = leg[c]
                elif pair & {WIN, LOC, COINC}:
                    self.role[i] = WIN
                elif SLOT in pair:
                    o = c2 if r1 == SLOT else c
                    if ro[o] == MIDR or (ro[o] == SLOT and leg.get(o) == leg.get(c)):
                        self.role[i] = MIDR
                        self.leg[i] = leg[c if r1 == SLOT else c2]
                        sc = scd.get(o)
                        if sc:
                            self.scd[i] = sc
                    else:
                        self.role[i] = ro[o]
                        if o in scd:
                            self.scd[i] = scd[o]
                elif MIDR in pair:
                    o = c if r1 == MIDR else c2
                    self.role[i], self.leg[i] = MIDR, leg[o]
                    if o in scd:
                        self.scd[i] = scd[o]
                elif SCDINT in pair:
                    o = c if r1 == SCDINT else c2
                    self.role[i], self.scd[i] = SCDINT, scd[o]
                else:
                    self.role[i] = CORR
        # corner points: floor (never crossed) if a diagonal hero move or a 2x2 floor patch passes them
        for (x, y) in ro:
            for dx in (-1, 1):
                q = (x + dx, y + 1)
                if q in ro or sum(p in ro for p in ((x + dx, y), (x, y + 1))) >= 2:
                    i = (2 * y + 2) * W + (2 * x + 1 + dx)
                    self.fl[i] = 1
                    self.role[i] = WIN
        self.near = bytearray(n)         # Chebyshev <= 4 of Z u {E}: no chain point, no crossing (Z1 + H4)
        if coin:
            for c in (coin['T'], coin['A'], coin['B'], coin['E']):
                for X in range(2 * (c[0] - 4), 2 * (c[0] + 5) + 1):
                    for Y in range(2 * (c[1] - 4), 2 * (c[1] + 5) + 1):
                        if 0 <= X < W and 0 <= Y < H:
                            self.near[Y * W + X] = 1
        self.side = bytearray(n)         # points beside a leg slot (the ends of its delimiter jump): kept for it
        for c, r in ro.items():
            if r == SLOT:
                i = R(c)
                for d in ((1, 0), (0, 1)):
                    if self.jump_ok(i, d):
                        for sg in (-1, 1):
                            j = i + sg * (d[1] * W + d[0])
                            if not self.fl[j]:
                                self.side[j] = 1
        self.halo = {}                   # level-1 routing keeps off the delimiter points of component legs
        self.halo2 = {}                  # level-2 routing keeps off the delimiter points of SCD tile legs
        for c, r in ro.items():
            if r == SLOT:
                i = R(c)
                hh = self.halo2 if leg[c][1].startswith('tile.') else self.halo
                for dx in range(-3, 4):
                    for dy in range(-3, 4):
                        hh[i + dy * W + dx] = 40
        self.gx_from = {}
        self.res = bytearray(n)          # reserved (lane rows etc.)
        self.occ = bytearray(n)          # chain points and crossed floor points
        self.pn = {}                     # chain point -> (prev, next)
        self.jumped = set()
        self.gx_used = set()
        # review-6 repair: geometry of drawn wires, point -> (level, prev, next) along the wire (box .. tree); a
        # level-1 chain drawn AFTER a level-2 wire may cross it by an SX whose earlier line (in time) is the chain
        # ('XW'; the same gadget as WSX, only the drawing order differs). LGEN_XW=0: off.
        self.wgeo = {}
        self.xw = os.environ.get('LGEN_XW', '1') == '1'
        self.dead = {1: set(), 2: set()}     # legs of G's checked earlier in TIME (their g-side stubs are dead)
        self.box = None                      # search window in ORIGINAL coordinates (x0, y0, x1, y1)
        self.finished = set()
        self.events = []
        self.trace = []
        self.starts = []
        self.tcid = []                   # chain id (1 = level-1 chain, 2 = level-2 chain) of every trace entry
        self.cur = 1
        self.lastp = {}
        self.ev_ti = []                  # trace index of every event (parallel to self.events)
        self.gseg = []                   # one record per routed G' (time order per level): see _gprime
        self.tree0 = {}                  # (G key, location) -> its edge points (reserved wire roots), reserve_locations
        # review 6 repair (F1/F2): GX only on legs of FINISHED G's ('finished'); 'own' = the old rule (own stubs
        # crossable after the two delimiter passes) kept only as the positive control of L_e2e.py.
        # placement 'ani' = SO_i at b_i, SD_i at a_i, drawn on the chain (repair F2); 'hk' = the old reachability-only
        # hooks (not drawn), kept only for the positive control.
        self.rule = os.environ.get('LGEN_GX_RULE', 'finished')
        self.placement = os.environ.get('LGEN_PLACEMENT', 'ani')
        self.hookrec = {}
        self.pcid = {}                   # chain point -> chain id (valid while the point is occupied)

    def R(self, c):
        return (2 * c[1] + 1) * self.W + 2 * c[0] + 1

    # ---------------- moves
    def free(self, i, side_ok=False):
        return not self.fl[i] and not self.occ[i] and not self.res[i] and not self.near[i] and             (side_ok or not self.side[i])

    def can_cross(self, f, level, own, dead=()):
        r = self.role[f]
        if self.near[f] or f in self.jumped:
            return None
        if r == GXR:
            return 'GX' if self.leg[f] in dead else None
        if r in (WIN, LOC, COINC, SLOT):
            return None
        if r == MIDR:
            lg = self.leg[f]
            if lg in own:
                return None
            s = self.scd.get(f)
            if level == 1 and s is not None and s not in self.finished:
                return None
            return 'CHX'
        if r == SCDINT:
            if level == 1 and self.scd[f] not in self.finished:
                return None
            return 'CHX'
        return 'CHX'

    def jump_ok(self, f, d):
        """geometric condition for a straight jump over floor cell f in direction d (unit vector index)"""
        W = self.W
        x, y = f % W, f // W
        dx, dy = d
        a = b = False
        for ex in (-1, 0, 1):
            for ey in (-1, 0, 1):
                if not (ex or ey):
                    continue
                X, Y = x + ex, y + ey
                if 0 <= X < W and 0 <= Y < self.H and self.fl[Y * W + X]:
                    t = ex * (-dy) + ey * dx                       # component across the jump line
                    if t == 0:
                        return False                               # floor on the jump line itself
                    if t < 0:
                        a = True
                    else:
                        b = True
        return a and b

    def sx_ok(self, c, d):
        pn = self.pn.get(c)
        if pn is None or c in self.jumped:
            return False
        W = self.W
        p, q = pn
        if p is None or q is None:
            return False
        perp = {abs(p - c), abs(q - c)}
        return perp == ({W} if d[1] == 0 else {1})

    def xw_ok(self, c, d):
        lv, p, q = self.wgeo[c]
        if lv != 2 or p is None or q is None:
            return False
        return {abs(p - c), abs(q - c)} == ({self.W} if d[1] == 0 else {1}) and p + q == 2 * c

    def neigh(self, i, level, own, targets=(), dead=()):
        W, H = self.W, self.H
        x, y = i % W, i // W
        for k, lg in self.gx_from.get(i, ()):
            if lg in dead and (self.free(k) or (k in targets and self.free(k, True))) and (i, k) not in self.gx_used:
                yield k, JUMP, ('GX', (i, k))
        for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            X, Y = x + d[0], y + d[1]
            if not (0 <= X < W and 0 <= Y < H):
                continue
            j = Y * W + X
            if self.free(j) or (j in targets and self.free(j, True)):
                yield j, 1, None
                continue
            X2, Y2 = X + d[0], Y + d[1]
            if not (0 <= X2 < W and 0 <= Y2 < H):
                continue
            k = Y2 * W + X2
            if not self.free(k):
                continue
            if self.fl[j]:
                kind = self.can_cross(j, level, own, dead)
                if kind and self.jump_ok(j, d):
                    yield k, JUMP, (kind, j)
            elif self.occ[j] and self.sx_ok(j, d):
                yield k, JUMP, ('SX', j)
            elif level == 1 and self.xw and j in self.wgeo and j not in self.jumped and self.xw_ok(j, d):
                yield k, JUMP, ('XW', j)

    def dijkstra(self, src, targets, level, own, limit=None, dead=(), pen=None, box=None, tpen=None):
        """tpen: extra cost of ENDING at a target (paid once, at the end; not when passing through it)"""
        box = box or self.box
        if box:
            W = self.W
            x0, y0, x1, y1 = (2 * v for v in box)
            hx, hy = src % W, src // W
            x0, y0, x1, y1 = min(x0, hx - 6), min(y0, hy - 6), max(x1, hx + 6), max(y1, hy + 6)
        dist = {src: 0}
        prev = {}
        pq = [(0, src)]
        while pq:
            dd, i = heapq.heappop(pq)
            if i < 0:                                       # virtual sink entry of target -1 - i
                i = -1 - i
                path = []
                while i != src:
                    path.append((i, prev[i][1]))
                    i = prev[i][0]
                return path[::-1], dd
            if dd > dist[i]:
                continue
            if i in targets and tpen is not None:
                if i != src:
                    heapq.heappush(pq, (dd + tpen.get(i, 0), -1 - i))
                    if not self.free(i):                    # a side point may end a piece, not be passed
                        continue
            elif i in targets:
                path = []
                while i != src:
                    path.append((i, prev[i][1]))
                    i = prev[i][0]
                return path[::-1], dd
            if limit and dd > limit:
                break
            for j, w, jv in self.neigh(i, level, own, targets, dead):
                if box and not (x0 <= j % W <= x1 and y0 <= j // W <= y1):
                    continue
                nd = dd + w + (pen.get(j, 0) if pen else 0)
                if nd < dist.get(j, 1 << 60):
                    dist[j] = nd
                    prev[j] = (i, jv)
                    heapq.heappush(pq, (nd, j))
        return None, None

    # ---------------- committing chain pieces
    def add(self, i):
        assert not self.occ[i] and not self.fl[i], ('chain cell reused', i)
        self.occ[i] = 1
        self.pcid[i] = self.cur
        last = self.lastp.get(self.cur)
        self.pn[i] = (last, None)
        if last is not None and last in self.pn and self.pn[last][1] is None:
            self.pn[last] = (self.pn[last][0], i)
        self.trace.append(i)
        self.tcid.append(self.cur)
        self.lastp[self.cur] = i

    def jump(self, kind, f, info=None):
        assert f not in self.jumped, ('double crossing', f)
        self.jumped.add(f)
        if kind not in ('SX', 'XW'):
            self.occ[f] = 1
        self.events.append((kind, f, info if info is not None else self.role[f]))
        self.ev_ti.append(len(self.trace))
        last = self.lastp[self.cur]
        if last in self.pn and self.pn[last][1] is None:
            self.pn[last] = (self.pn[last][0], f)
        self.trace.append(f)
        self.tcid.append(self.cur)
        self.lastp[self.cur] = f

    def commit(self, path):
        for i, jv in path:
            if jv and jv[0] == 'GX' and isinstance(jv[1], tuple):
                a, c = jv[1]
                self.gx_used.add((a, c))
                self.gx_used.add((c, a))
                self.events.append(('GX', a, self.gx[(a, c)]))
                self.ev_ti.append(len(self.trace))
                lp = self.lastp[self.cur]
                self.pn[lp] = (self.pn[lp][0], None)
            elif jv:
                self.jump(jv[0], jv[1])
            self.add(i)

    def start(self, i, side_ok=False):
        assert self.free(i, side_ok), ('start cell not free', i)
        self.starts.append(len(self.trace))
        self.occ[i] = 1
        self.pcid[i] = self.cur
        self.pn[i] = (None, None)
        self.trace.append(i)
        self.tcid.append(self.cur)
        self.lastp[self.cur] = i
        return i

    # ---------------- one G'
    def snapshot(self):
        return (bytes(self.occ), dict(self.pn), set(self.jumped), set(self.gx_used), len(self.events),
                len(self.trace), set(self.finished), {k: set(v) for k, v in self.dead.items()}, len(self.starts),
                dict(self.lastp), self.cur, bytes(self.res), len(self.gseg), dict(self.wgeo))

    def restore(self, sn):
        occ, pn, jumped, gxu, ne, nt, fin, dead, ns, lastp, cur, res, ng, wgeo = sn
        self.wgeo = dict(wgeo)
        self.res[:] = res
        del self.gseg[ng:]
        del self.ev_ti[ne:]
        del self.starts[ns:]
        del self.tcid[nt:]
        self.lastp, self.cur = dict(lastp), cur
        self.dead = {k: set(v) for k, v in dead.items()}
        self.occ[:] = occ
        self.pn, self.jumped, self.gx_used, self.finished = dict(pn), set(jumped), set(gxu), set(fin)
        del self.events[ne:]
        del self.trace[nt:]

    def gprime(self, head, G, rot=1, gap=0, rad=3, margin=24):  # margin in original cells
        own = {(G['tile'], ln) for ln, _, _ in G['legs']}
        gx_ = [c[0] for c in G['tcells']]
        gy_ = [c[1] for c in G['tcells']]
        self.box = (min(gx_) - margin, min(gy_) - margin, max(gx_) + margin, max(gy_) + margin)
        try:
            return self._gprime(head, G, own, rot, gap, rad)
        finally:
            self.box = None

    def _gprime(self, head, G, own, rot, gap, rad):
        W = self.W
        I = self.R
        order = ring_order(G, rot, gap)
        seg0 = (len(self.trace), len(self.events))
        # pass 1 keeps away from G (room for pass 2 and the hooks): penalty on cells within distance rad of G
        pen = {}
        # review-6 scaling: the stubbed legs reach beyond rad of the window, so the leg bodies (Wb, g-side) are
        # penalty centres too (else pass 1 hugs a leg between Wt and Wb and seals pass 2 out); LGEN_PEN_LEGS=0: old
        centres = list(G['gcells'])
        if os.environ.get('LGEN_PEN_LEGS', '1') == '1':
            centres += [tuple(wb) for _, _, wb in G['legs']] + [tuple(c) for c in G['locs'].values()]
        for c in centres:
            for dx in range(-2 * rad, 2 * rad + 1):
                for dy in range(-2 * rad, 2 * rad + 1):
                    x, y = 2 * c[0] + 1 + dx, 2 * c[1] + 1 + dy
                    if 0 <= x < W and 0 <= y < self.H:
                        k = y * W + x
                        pen[k] = max(pen.get(k, 0), 2 * (2 * rad + 2 - max(abs(dx), abs(dy))))
        for slot in (0, 1):                                  # pass 1 over every Wt, pass 2 over every Wb
            seq = order if slot == 0 else order[::-1]
            sgn = 1 if slot == 0 else -1
            for ln, wt, wb in seq:
                f = I(wt if slot == 0 else wb)
                sgnf = lambda v: (v > 0) - (v < 0)
                sx_, sy_ = sgnf(wt[0] - wb[0]), sgnf(wt[1] - wb[1])  # leg direction (outward, unit)
                d = (-sy_ * sgn * rot, sx_ * sgn * rot)           # tangent: pass 1 sweeps in sense rot
                x, y = f % W, f // W
                w1, w2 = (y - d[1]) * W + (x - d[0]), (y + d[1]) * W + (x + d[0])
                if not (self.jump_ok(f, d) and (self.free(w1, True) or w1 == head) and self.free(w2, True)):
                    return None, ('slot not crossable in ring order', 'Wt' if slot == 0 else 'Wb', ln)
                dl = self.dead[1] | (self.dead[2] if G['level'] == 2 else set())
                pp = pen if slot == 0 else None
                if G['level'] == 1:
                    pp = dict(self.halo) if pp is None else {**self.halo, **pen}
                elif self.halo2:
                    pp = dict(self.halo2) if pp is None else {**self.halo2, **pen}
                path, cost = self.dijkstra(head, {w1}, G['level'], own, pen=pp, dead=dl)
                if path is None and ln == seq[0][0]:      # first approach: retry without the search window
                    path, cost = self.dijkstra(head, {w1}, G['level'], own, pen=pp, dead=dl,
                                               box=(-10 ** 6, -10 ** 6, 10 ** 6, 10 ** 6))
                if path is None:
                    return None, ('no path to', 'Wt' if slot == 0 else 'Wb', ln)
                self.commit(path)
                self.jump('Wt' if slot == 0 else 'Wb', f, (G['tile'], ln))
                self.add(w2)
                head = w2
        dl = self.dead[1] | (self.dead[2] if G['level'] == 2 else set())     # legs of G's FINISHED earlier in time
        if self.placement == 'hk':
            hk = self._hooks_old(head, G, own, dl)
            if isinstance(hk, tuple):
                return None, hk
        else:
            head, hk = self._checks(head, G, own, dl)
            if head is None:
                return None, hk
        if G['level'] == 1:
            self.finished.add(G['scd'])
        self.dead[G['level']] |= own
        self.gseg.append(dict(key=(G['tile'], G['name'], G['level']), level=G['level'], cid=self.cur,
                              t0=seg0[0], t1=len(self.trace), e0=seg0[1], e1=len(self.events), own=set(own),
                              kind=G.get('ckind'), checks=list(G['checks']), locs=dict(G['locs'])))
        return head, hk

    def _hooks_old(self, head, G, own, dl):
        """review-6 state (positive control only): every location reachable from the head; hook curves NOT drawn;
        with rule 'own' they may cross own stubs (GX) -- the F1 bug. Records the crossing list of every hook path."""
        W, I = self.W, self.R
        hk, rec = {}, {}
        for p, c in G['locs'].items():
            i = I(c)
            x, y = i % W, i // W
            tg = {(y + dy) * W + (x + dx) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
                  if 0 <= x + dx < W and 0 <= y + dy < self.H}
            tg = {j for j in tg if self.free(j, True) or j == head}
            path, cost = self.dijkstra(head, tg, G['level'], set(), dead=(own | dl) if self.rule == 'own' else dl)
            if path is None:
                return ('location not reachable', p)
            hk[p] = sum(1 for _, jv in path if jv)
            rec[p] = [self.classify(jv[0], jv[1], own) for _, jv in path if jv]
        self.hookrec[(G['tile'], G['name'], G['level'])] = rec
        return hk

    def classify(self, kind, f, own, finished=None):
        """a crossing of a G' chain piece, as seen by that G' (own = its legs): ('GXo', letter) own stub,
        ('CHXm', letter) own middle segment, ('GXf',) stub of a leg of a finished G', ('GXp',) stub of a pending leg
        (never allowed), ('W',) any other floor (main corridor, other legs' middles, SCD interiors), ('SX',)"""
        if kind == 'SX':
            return ('SX',)
        lg = self.leg.get(f)
        if kind == 'GX':
            if lg in own:
                return ('GXo', lg[1].split('.')[-1])
            fin = finished if finished is not None else (self.dead[1] | self.dead[2])
            return ('GXf',) if lg in fin else ('GXp',)
        if kind == 'CHX' and self.role[f] == MIDR and lg in own:
            return ('CHXm', lg[1].split('.')[-1])
        return ('W',)

    def reserve_locations(self, Gs):
        """review 6 repair F2 (Ani placement): the non-floor 4-neighbour points of every check location are the
        roots of its wire tree (the private corridor from the location to its SO In / SD exit boxes). Reserved from
        the start, so no chain piece takes them; released (if unused) when the location's own G' is done."""
        W = self.W
        for G in Gs:
            key = (G['tile'], G['name'], G['level'])
            for p, c in G['locs'].items():
                i = self.R(c)
                pts = []
                for j in (i + 1, i - 1, i + W, i - W):
                    if not self.fl[j] and not self.occ[j] and not self.res[j] and not self.near[j]:
                        self.res[j] = 1
                        pts.append(j)
                self.tree0[(key, p)] = pts

    def keepout_l1(self, G1s):
        """l2first drawing order (level-2 curve drawn before the level-1 curve, time order unchanged): keep room for
        each level-1 G' (SCD composite) while level 2 is drawn -- the two side points (and the next ones) of every
        tile-leg slot, and for every level-1 location a box point next to its wire-tree root, a chain point next to
        that box and the chain point's two side points. Returns the reserved points (released before level 1)."""
        W = self.W
        out = []

        def take(j):
            if 0 <= j < len(self.res) and self.free(j, True):
                self.res[j] = 1
                out.append(j)
        for G in G1s:
            key = (G['tile'], G['name'], G['level'])
            if os.environ.get('LGEN_L1_KEEP_SLOTS', '0') == '1':      # too strong: level 2 then fails (off)
                for ln, wt, wb in G['legs']:
                    sx_, sy_ = (wt[0] > wb[0]) - (wt[0] < wb[0]), (wt[1] > wb[1]) - (wt[1] < wb[1])
                    d = -sy_ + sx_ * W                  # side direction (perpendicular to the leg)
                    for c in (wt, wb):
                        f = self.R(c)
                        for k in (1, 2):
                            take(f + k * d)
                            take(f - k * d)
            for p in G['locs']:
                for t in self.tree0.get((key, p), ()):
                    for u in (1, -1, W, -W):              # one box/chain spot per tree root
                        b, j = t + u, t + 2 * u
                        if self.free(b, True) and self.free(j, True):
                            take(b)
                            take(j)
                            break
        return out

    def _wreg(self, seq, level):
        # interior wire points only (not the box, not the tree point); consecutive entries that are not adjacent
        # (an SX jump of the wire) leave the point non-straight, so it is never crossed
        for u, w, v in zip(seq, seq[1:], seq[2:]):
            self.wgeo[w] = (level, u, v)

    def _wire_moves(self, i, level):
        """wire moves from point i: plain steps to free points (cost 1), or an SX jump over a straight piece of an
        already drawn chain piece (the wire is that SX's LATER line, used once; cost 4). A level-1 wire may jump
        only level-1 pieces (level-2 pieces are later in time); every drawn piece is earlier in time otherwise."""
        W = self.W
        for d, s in ((1, (1, 0)), (-1, (-1, 0)), (W, (0, 1)), (-W, (0, -1))):
            j = i + d
            if self.free(j, True):
                yield j, 1, None
            elif self.occ[j] and not self.fl[j] and j not in self.jumped and self.sx_ok(j, s) and \
                    self.free(j + d, True) and (level == 2 or self.pcid.get(j) == 1):
                yield j + d, 4, j

    def _wire(self, src, T, level, depth=40):
        """cheapest wire from the box point src to a point 4-adjacent to the wire tree T: returns (points, jumps)
        with points = [src, ..., last] (jumped chain points not included) and jumps = the chain points it SX-jumps,
        in order from the box; None if there is none within `depth`. A wire crosses no floor and no wire, and
        crosses chain pieces only by SX as the later line; its points stay reserved (no chain ever uses them)."""
        W = self.W
        adjT = lambda j: any(abs(j - t) in (1, W) for t in T)
        if adjT(src):
            return [src], []
        dist, prev = {src: 0}, {src: None}
        pq = [(0, src)]
        while pq:
            dd, i = heapq.heappop(pq)
            if dd > dist[i]:
                continue
            if i != src and adjT(i):
                pts, jumps = [i], []
                while prev[i] is not None:
                    i0, jp = prev[i]
                    if jp is not None:
                        jumps.append(jp)
                    pts.append(i0)
                    i = i0
                return pts[::-1], jumps[::-1]
            if dd >= depth:
                continue
            for j, w, jp in self._wire_moves(i, level):
                if j in T:
                    continue
                nd = dd + w
                if nd < dist.get(j, 1 << 30):
                    dist[j] = nd
                    prev[j] = (i, jp)
                    heapq.heappush(pq, (nd, j))
        return None

    def _region(self, T, level, depth=40):
        """points a box may sit on, with their wire cost to the tree T (same moves as _wire)"""
        W = self.W
        seen = {}
        pq = []
        for t in T:
            for j in (t + 1, t - 1, t + W, t - W):
                if j not in seen and j not in T and self.free(j, True):
                    seen[j] = 0
                    pq.append((0, j))
        heapq.heapify(pq)
        while pq:
            dd, i = heapq.heappop(pq)
            if dd > seen[i] or dd >= depth:
                continue
            for j, w, jp in self._wire_moves(i, level):
                if j in T:
                    continue
                if dd + w < seen.get(j, 1 << 30):
                    seen[j] = dd + w
                    heapq.heappush(pq, (dd + w, j))
        return seen

    def _checks(self, head, G, own, dl):
        """Ani's Fig. 23 check walks, drawn on the chain (review 6 repair F2). For check i = (a_i, b_i):
          Out_{i-1} -> Op_i : the chain passes a point j next to the SO_i box p, and p is joined to b_i by a wire;
          Op_i -> SD_i      : the chain piece ends at a point q (the SD_i box), joined to a_i by a wire;
          Out_i             : a new chain piece starts at p (SO_i's exit).
        A wire (see _wire) is a path of reserved wall points from the box to the location's wire tree (its non-floor
        4-neighbours, then earlier plain wires of the same location): it crosses no floor and no wire, crosses a chain
        piece only by an SX as the later line, and no chain ever uses or crosses it. So in the sense of review 6 F2
        both hooks are crossing-free dead ends before t, and only the chain-only edges cross anything. Allowed
        crossings on them (repair F1): SX over the chain; WCX over own DEAD middle segments (own legs are not passed
        as `own`, so their MIDR points are crossable); GX on stubs of legs of FINISHED G's only (dl); CHX over other
        floor. Rule 'own' (positive control) adds the own stubs to the GX set.
        Bounded backtracking over the contact choices (LGEN_CHECK_TRIES Dijkstra calls per G')."""
        W = self.W
        key = (G['tile'], G['name'], G['level'])
        dx_ = (dl | own) if self.rule == 'own' else dl
        tree0 = {p: frozenset(self.tree0.get((key, p), ())) for p in G['locs']}
        allt = {t for v in tree0.values() for t in v}
        lev = G['level']
        for t in allt:
            self.res[t] = 1
        adj = lambda i: (i + 1, i - 1, i + W, i - W)
        depth = int(os.environ.get('LGEN_WIRE_DEPTH', '40'))
        budget = [int(os.environ.get('LGEN_CHECK_TRIES', '200'))]
        BR = 3                                          # alternatives tried per contact
        checks = G['checks']
        fail = ['no checks']

        def reserve(path):
            for u in path:
                self.res[u] = 1

        def rec(k, head, tree, used):
            if k == len(checks):
                return head, used
            a, b = checks[k]
            # ---- Op_k: the chain passes j; the SO box p is a free neighbour of j with a wire to b's tree
            Rb = self._region(tree[b], lev, depth)
            J = {}
            for p, dp in Rb.items():
                for j in adj(p):
                    if j != head and j != p and self.free(j, True):
                        J[j] = min(J.get(j, 1 << 30), dp)
            for _ in range(BR):
                if not J or budget[0] <= 0:
                    break
                budget[0] -= 1
                path, cost = self.dijkstra(head, set(J), lev, set(), dead=dx_,
                                           tpen={j: WIRE_PEN * d for j, d in J.items()})
                if path is None:
                    fail[0] = ('no chain edge to Op', k, b)
                    break
                sn = self.snapshot()
                self.commit(path)
                j = self.lastp[self.cur]
                J.pop(j, None)
                got = None
                for p in sorted((q for q in adj(j) if q in Rb and self.free(q, True)), key=lambda q: (Rb[q], q)):
                    wp = self._wire(p, tree[b], lev, depth=depth)
                    if wp is not None:
                        got = (p, wp)
                        break
                if not got:
                    fail[0] = ('no SO wire', k, b)
                    self.restore(sn)
                    continue
                p, (wp, wjp) = got
                reserve(wp)
                wp = wp[1:]
                tb = min(t for t in tree[b] if abs(t - (wp[-1] if wp else p)) in (1, W))
                self._wreg([p] + list(wp) + [tb], lev)
                tree_b = tree[b] | set(wp) if not wjp else tree[b]
                self.events.append(('OP', j, (key, k, p, tb, wp, wjp)))
                self.ev_ti.append(len(self.trace) - 1)
                for jp in wjp:
                    self.jumped.add(jp)
                    self.events.append(('WSX', jp, (key, k, 'SO')))
                    self.ev_ti.append(len(self.trace) - 1)
                tree1 = dict(tree)
                tree1[b] = tree_b
                # ---- SD_k: the chain piece ends at q, with a wire to a's tree
                Ra = self._region(tree1[a], lev, depth)
                for _ in range(BR):
                    if not Ra or budget[0] <= 0:
                        break
                    budget[0] -= 1
                    path2, cost2 = self.dijkstra(j, set(Ra), lev, set(), dead=dx_,
                                                 tpen={q: WIRE_PEN * d for q, d in Ra.items()})
                    if path2 is None:
                        fail[0] = ('no chain edge to SD', k, a)
                        break
                    sn2 = self.snapshot()
                    self.commit(path2)
                    q = self.lastp[self.cur]
                    Ra.pop(q, None)
                    wq = self._wire(q, tree1[a], lev, depth=depth)
                    if wq is None:
                        fail[0] = ('no SD wire', k, a)
                        self.restore(sn2)
                        continue
                    wq, wjq = wq
                    wq = wq[1:]
                    reserve(wq)
                    last = wq[-1] if wq else q
                    ta = min(t for t in tree1[a] if abs(t - last) in (1, W))
                    self._wreg([q] + list(wq) + [ta], lev)
                    tree2 = dict(tree1)
                    if not wjq:
                        tree2[a] = tree1[a] | set(wq)
                    self.events.append(('SD', q, (key, k, ta, wq, wjq)))
                    self.ev_ti.append(len(self.trace) - 1)
                    for jp in wjq:
                        self.jumped.add(jp)
                        self.events.append(('WSX', jp, (key, k, 'SD')))
                        self.ev_ti.append(len(self.trace) - 1)
                    # ---- Out_k: a new piece starts at the SO box p
                    self.res[p] = 0
                    self.start(p, side_ok=True)
                    self.events.append(('OUT', p, (key, k)))
                    self.ev_ti.append(len(self.trace) - 1)
                    r = rec(k + 1, p, tree2, used | {ta, tb})
                    if r is not None:
                        return r
                    self.restore(sn2)
                self.restore(sn)
            return None

        r = rec(0, head, tree0, frozenset())
        if r is None:
            for t in allt:
                self.res[t] = 0
            return None, fail[0]
        head, used = r
        for t in allt - used:                        # roots no wire attaches to are released
            self.res[t] = 0
        return head, {'contacts': 3 * len(checks)}

    # ---------------- both levels of one block, routed tile by tile (two chain heads)
    VARIANTS = [(1, 0, 3), (-1, 0, 3), (1, 1, 3), (-1, 1, 3), (1, 0, 1), (-1, 0, 1), (1, 0, 6), (-1, 0, 6),
                (1, 2, 3), (-1, 2, 3), (1, 1, 1), (-1, 1, 1)]

    def _route_g(self, h, G, margin):
        for v in self.VARIANTS:
            sn = self.snapshot()
            nh, info = self.gprime(h, G, *v, margin=margin)
            if nh is not None:
                return nh, (G['tile'], G['name'], info, v)
            self.last = (G['tile'], G['name'], info)
            self.restore(sn)
            self.retries += 1
        return None, None

    def _tile_solutions(self, tid, h1, h2, g1, g2s, margin):
        """generator over joint routings of one tile: level-1 G' (variant) then level-2 G's (permutation);
        yields (h1', h2', log1, log2); the router state is that routing while the caller holds it"""
        v1s = self.VARIANTS if g1 else [None]
        deadline = time.time() + float(os.environ.get('LGEN_TILE_SECS', '90'))
        for v1 in v1s:
            if time.time() > deadline:
                return
            sn1 = self.snapshot()
            if g1:
                self.cur = 1
                nh1, info = self.gprime(h1, g1, *v1, margin=margin)
                if nh1 is None:
                    self.last = (tid, 'scd', info)
                    self.restore(sn1)
                    continue
                l1 = [(tid, 'scd', info, v1)]
            else:
                nh1, l1 = h1, []
            # phase 0: the old greedy routing per permutation (first variant that routes, per G'); phase 1:
            # depth-first over the variants of every level-2 G' (review-6 repair: the caller's lane lookahead can
            # reject a routing and get the next one). The first solution is the old one, so templates that routed
            # before are unchanged.
            for phase in ((0,) if not g2s else (0, 1)):
                for perm in itertools.permutations(g2s):
                    if time.time() > deadline:
                        break
                    sn2 = self.snapshot()
                    self.cur = 2
                    if not g2s:
                        yield nh1, h2, l1, []
                    else:
                        for hh, l2 in self._route_seq(h2, list(perm), margin, [], deadline, greedy=phase == 0):
                            yield nh1, hh, l1, l2
                    self.restore(sn2)
            self.restore(sn1)

    def _route_seq(self, hh, Gs, margin, l2, deadline, greedy=False):
        if not Gs:
            yield hh, l2
            return
        G = Gs[0]
        for v in self.VARIANTS:
            if time.time() > deadline:
                return
            sn = self.snapshot()
            nh, info = self.gprime(hh, G, *v, margin=margin)
            if nh is not None:
                yield from self._route_seq(nh, Gs[1:], margin, l2 + [(G['tile'], G['name'], info, v)], deadline,
                                           greedy)
                self.restore(sn)
                if greedy:
                    return
                continue
            self.last = (G['tile'], G['name'], info)
            self.retries += 1
            self.restore(sn)

    def _can_reach(self, h, t, lv):
        """can the chain head h still get to the lane exit t (geometry only, no commit)?"""
        self.res[t] = 0
        try:
            path, _ = self.dijkstra(h, {t}, lv, set(), dead=self.dead[1] | (self.dead[2] if lv == 2 else set()),
                                    box=(-10 ** 6, -10 ** 6, 10 ** 6, 10 ** 6))
        finally:
            self.res[t] = 1
        return path is not None or h == t

    def joint(self, s1, t1, G1s, s2, t2, G2s):
        """level-1 chain s1 -> every level-1 G' -> t1 and level-2 chain s2 -> every level-2 G' -> t2, both visiting
        the tiles in the same order (so 'SCD finished' at level-1 time = tiles before it in that order)"""
        W = self.W
        self.retries = getattr(self, 'retries', 0)
        self.last = None
        for t in (t1, t2):
            if t is not None:
                self.res[t] = 1
        self.cur = 1
        h1 = self.start(s1) if s1 is not None else None
        self.cur = 2
        h2 = self.start(s2) if s2 is not None else None
        g1 = {G['tile']: G for G in G1s}
        g2 = defaultdict(list)
        for G in G2s:
            g2[G['tile']].append(G)
        todo = sorted(set(g1) | set(g2))
        log1, log2, hist = [], [], []
        center = {}
        for tid in todo:
            cs = [c for G in g2[tid] + ([g1[tid]] if tid in g1 else []) for c in G['tcells']]
            center[tid] = (sum(c[0] for c in cs) / len(cs), sum(c[1] for c in cs) / len(cs))
        rewinds, force, fails = 0, None, defaultdict(int)
        t_start = time.time()
        budget = float(os.environ.get('LGEN_BUDGET', '1500'))
        while todo:
            if time.time() - t_start > budget:
                return None, None, ('time budget exceeded', len(todo), 'tiles left')
            ref = h2 if h2 is not None else h1
            hx, hy = (ref % W) // 2, (ref // W) // 2
            dist = lambda tid: abs(center[tid][0] - hx) + abs(center[tid][1] - hy)
            todo.sort(key=dist)
            cands = [force] if force in todo else todo[:3]
            got = None
            for margin in (24, 60):
                for tid in cands:
                    sn = self.snapshot()
                    sol = None
                    for cand in self._tile_solutions(tid, h1, h2, g1.get(tid), g2[tid], margin):
                        # lookahead (review-6 placement draws more of the curve): both heads must still reach
                        # their lane exits, else the boxes/wires just drawn have sealed a head in
                        if all(h is None or t is None or self._can_reach(h, t, lv)
                               for h, t, lv in ((cand[0], t1, 1), (cand[1], t2, 2))):
                            sol = cand
                            break
                        self.last = (tid, 'lookahead', 'a chain head cannot reach its lane exit any more')
                    if sol is not None:
                        got = (tid, sn, h1, h2, sol)
                        break
                    self.restore(sn)
                if got:
                    break
            if not got:
                stuck = cands[0]
                fails[stuck] += 1
                near = [k for k, e in enumerate(hist) if abs(center[e[0]][0] - center[stuck][0]) +
                        abs(center[e[0]][1] - center[stuck][1]) < 140]
                if os.environ.get('LGEN_DEBUG'):
                    print('stuck', stuck, 'cands', cands, 'hist', len(hist), 'near', len(near), 'fails', fails[stuck],
                          self.last, flush=True)
                if not near and hist and os.environ.get('LGEN_FAR_REWIND', '1') == '1':
                    near = list(range(len(hist)))      # review-6 repair: no nearby earlier tile -> rewind the latest ones
                if not near or rewinds >= 400 or fails[stuck] > 20:
                    return None, None, self.last or (stuck, 'no routing found')
                rewinds += 1
                # rewind to before the fails[stuck]-th nearest earlier tile (deeper on repeated failure)
                k = near[-1] if fails[stuck] == 1 else near[max(0, len(near) - 2)]
                tid0, sn0, a1, a2, n1, n2 = hist[k]
                for e in hist[k:]:
                    todo.append(e[0])
                del hist[k:]
                self.restore(sn0)
                del log1[n1:]
                del log2[n2:]
                h1, h2 = a1, a2
                force = stuck
                continue
            tid, sn, a1, a2, sol = got
            if os.environ.get('LGEN_PROGRESS'):
                print(f'  [{time.time() - t_start:6.0f}s] tile {tid} done, {len(todo) - 1} left, rewinds {rewinds}',
                      file=sys.stderr, flush=True)
            hist.append((tid, sn, a1, a2, len(log1), len(log2)))
            todo.remove(tid)
            force = None
            h1, h2 = sol[0], sol[1]
            log1.extend(sol[2])
            log2.extend(sol[3])
        self.rewinds = rewinds
        for h, t, lv in ((h1, t1, 1), (h2, t2, 2)):
            if t is None:
                continue
            self.res[t] = 0
            self.cur = lv
            path, cost = self.dijkstra(h, {t}, lv, set(), dead=self.dead[1] | (self.dead[2] if lv == 2 else set()))
            if path is None:
                return None, None, ('no way back to the lane', lv)
            self.commit(path)
        return log1, log2, None


def block_template(b, parity, coin=None, xe=None, strategies=('joint', 'l1first', 'l2first')):
    """route both excursions of block b: parity 0 = level-1 lane bottom (L->R), level-2 lane top (R->L);
    parity 1 = level-1 top (R->L), level-2 bottom (L->R). Geometric strategies (time order is always level 1
    then level 2; only the order in which the two curves are DRAWN differs): 'joint' = both chains tile by tile,
    'l1first' = whole level-1 chain drawn first, 'l2first' = whole level-2 chain drawn first; the first that
    succeeds is kept. Returns dict with events, logs, lane crossings."""
    if os.environ.get('LGEN_STRATS'):
        strategies = tuple(os.environ['LGEN_STRATS'].split(','))
    for k, strat in enumerate(strategies):
        if os.environ.get('LGEN_PROGRESS'):
            print(f'strategy {strat}', file=sys.stderr, flush=True)
        res = _block_template(b, parity, coin, xe, strat)
        if not any(v['err'] for v in res['levels'].values()):
            break
    res['strategy'] = strat
    res['strategies_tried'] = k + 1
    return res


def _block_template(b, parity, coin, xe, strat):
    Rt = Router(b, coin)
    W = Rt.W
    lanes = {0: ((LANES[1], 1), (LANES[0], -1)), 1: ((LANES[0], -1), (LANES[1], 1))}[parity]
    lane_x = {}
    for yl in LANES:
        cross = []
        Y = 2 * yl + 1
        for X in range(W):
            i = Y * W + X
            Rt.res[i] = 1
            if Rt.fl[i]:
                assert Rt.jump_ok(i, (1, 0)) and Rt.role[i] == CORR and not Rt.near[i], ('lane cannot cross', b.kind, X, yl)
                cross.append(X)
        lane_x[yl] = cross
    res = dict(kind=b.kind, parity=parity, lanes={yl: len(v) for yl, v in lane_x.items()}, levels={})
    if not b.tiles:
        return res
    cx = xe if xe is not None else int(sum(c[0] for t in b.tiles for c in t['cells']) / sum(len(t['cells']) for t in b.tiles))
    ends = {}
    Gl = {lv: gprimes(b.tiles, lv) for lv in (1, 2)}
    if Rt.placement == 'ani':
        Rt.reserve_locations(Gl[1] + Gl[2])
    for level, (yl, delta) in zip((1, 2), lanes):
        if not Gl[level]:
            ends[level] = (None, None)
            continue
        Y = 2 * yl + 1
        yin = Y - 1 if yl == LANES[1] else Y + 1
        x = 2 * cx
        while not (Rt.free(yin * W + x) and Rt.free(yin * W + x + delta) and not Rt.fl[Y * W + x]
                   and not Rt.fl[Y * W + x + delta]):
            x += 1
        ends[level] = (yin * W + x, yin * W + x + delta)
    t0 = time.time()
    if strat == 'joint' or not (Gl[1] and Gl[2]):
        log1, log2, err = Rt.joint(ends[1][0], ends[1][1], Gl[1], ends[2][0], ends[2][1], Gl[2])
    else:
        first = 1 if strat == 'l1first' else 2
        logs, err = {}, None
        keep = Rt.keepout_l1(Gl[1]) if first == 2 and os.environ.get('LGEN_L1_KEEP', '0') == '1' else []
        for lv in (first, 3 - first):
            if lv == 1:
                for t in keep:                  # release the level-1 keep-out before the level-1 curve is drawn
                    Rt.res[t] = 0
            a = Rt.joint(ends[1][0], ends[1][1], Gl[1], None, None, []) if lv == 1 else                 Rt.joint(None, None, [], ends[2][0], ends[2][1], Gl[2])
            logs[lv] = a[0] if lv == 1 else a[1]
            if a[2]:
                err = a[2]
                break
        log1, log2 = logs.get(1), logs.get(2)
    secs = round(time.time() - t0, 1)
    for lv, lg in ((1, log1), (2, log2)):
        if Gl[lv]:
            res['levels'][lv] = dict(gprimes=len(Gl[lv]), err=err, log=lg, secs=secs)
    res['events'] = Rt.events
    res['router'] = Rt
    if not err:
        res['validate'] = validate(Rt, b)
    return res


def summarize(res):
    ev = defaultdict(int)
    for kind, f, info in res.get('events', []):
        if kind == 'CHX':
            ev['CHX.' + ['wall', 'win', 'slot', 'mid', 'scdint', 'loc', 'corr', 'coin', 'gx'][info]] += 1
        else:
            ev[kind] += 1
    return dict(ev)


def render(Rt, x0, y0, x1, y1):
    W = Rt.W
    ev = {f: k for k, f, _ in Rt.events}
    out = []
    for y in range(y0, y1):
        row = ''
        for x in range(x0, x1):
            i = y * W + x
            if i in ev:
                row += {'Wt': 'T', 'Wb': 'B', 'SX': 'x', 'CHX': 'c', 'GX': 'g', 'OP': 'o', 'SD': 'd',
                        'OUT': 'u'}.get(ev[i], '?')
            elif Rt.fl[i]:
                row += '.:sm#L,kG'[Rt.role[i]]
            elif Rt.occ[i]:
                row += '*'
            elif Rt.near[i]:
                row += 'n'
            elif Rt.res[i]:
                row += 'w'
            else:
                row += ' '
        out.append(row)
    return '\n'.join(out)


def template_record(res):
    """compact JSON record of a block template (counts + per-G' log), no router object"""
    out = dict(kind=str(res['kind']), parity=res['parity'], lanes=res['lanes'], counts=summarize(res), levels={})
    for k, v in res['levels'].items():
        out['levels'][k] = dict(gprimes=v['gprimes'], err=v['err'], secs=v['secs'],
                                hooks_jumps=sum(sum(h.values()) for _, _, h, _ in (v['log'] or [])),
                                visited=[[a, b_] for a, b_, _, _ in (v['log'] or [])])
    Rt = res.get('router')
    if Rt is not None:
        out['chain_points'] = len(Rt.trace)
        out['retries'] = getattr(Rt, 'retries', 0)
        out['validate'] = res.get('validate')
    out['strategy'] = res.get('strategy')
    if Rt is not None:
        out['gseq'] = gprime_items(Rt)
        out['placement'], out['gx_rule'] = Rt.placement, Rt.rule
        if Rt.hookrec:
            out['hooks'] = [dict(key=[str(v) for v in k], locs={p: [list(x) for x in v] for p, v in d.items()})
                            for k, d in Rt.hookrec.items()]
    return out


# ============================================================ 8. whole instance: assembly, checks, outputs
MACHINE_BLOCKS = dict(WCX=222, SO=50, SD=11, SX=83)     # Push-1F blocks per machinery gadget (B2 §3.6; SX = SO + 3 SD)
MDIR = os.path.join(ROOT, 'build', 'machinery')        # concrete machinery boards (M_build.py, M-machinery.md)


def machinery_boards():
    """the concrete WCX / SO / SD / SX boards drawn by M_build.py and checked by M_verify.py, if they are built:
    {kind: dict(W, H, boulders, floor)}; None if build/machinery is missing (then only the B2 §3.6 estimate is used)."""
    out = {}
    for k in ('WCX', 'SO', 'SD', 'SX'):
        f = os.path.join(MDIR, k + '.json')
        if not os.path.exists(f):
            return None
        j = json.load(open(f))
        out[k] = dict(W=j['W'], H=j['H'], boulders=j['boulders'], floor=j['floor'])
    return out


def m_block(kind, s=0):
    """optional block type: one concrete machinery board (M_build) under grid symmetry s, its external ports on
    the block midlines with straight stubs to the border. WCX / SX: L, R = the crossed hallway (arms L, R before the
    symmetry), Tp, Bt = the check line (arms T, B). The block pitch is the board's own (WCX does not fit P = 469),
    so these blocks are not placed in the P-pitch macro grid; check_mblock asserts the same locality contract as
    check_block. Returns the Block (b.kind = ('M', kind, s))."""
    rows = open(os.path.join(MDIR, kind + '.txt')).read().split()
    j = json.load(open(os.path.join(MDIR, kind + '.json')))
    W0, H0 = j['W'], j['H']
    W, H = XB.sym_size(s, W0, H0)
    f = lambda x, y: XB.sym(s, x, y, W0, H0)
    ext = {e: f(*c) for e, c in j['ext'].items()}
    side = {}
    for e, (x, y) in ext.items():
        side[e] = 'L' if x == 0 else 'R' if x == W - 1 else 'T' if y == 0 else 'B'
    xs = {x for e, (x, y) in ext.items() if side[e] in 'TB'}
    ys = {y for e, (x, y) in ext.items() if side[e] in 'LR'}
    assert len(xs) <= 1 and len(ys) <= 1, ('ports not on common midlines', kind, ext)
    cx = xs.pop() if xs else W // 2
    cy = ys.pop() if ys else H // 2
    half = max(cx, W - 1 - cx, cy, H - 1 - cy) + 6
    Pm = 2 * half + 1
    ox, oy = half - cx, half - cy
    b = Block(('M', kind, s), Pm, Pm)
    b.mid = half
    for y, r in enumerate(rows):
        for x, ch in enumerate(r):
            if ch in '.0':
                gx, gy = f(x, y)
                b.put((gx + ox, gy + oy), ch, ('mboard', kind))
    for e, (x, y) in ext.items():
        sd = side[e]
        d = {'L': (-1, 0), 'R': (1, 0), 'T': (0, -1), 'B': (0, 1)}[sd]
        c = (x + ox + d[0], y + oy + d[1])
        end = (c[0] if sd in 'TB' else (0 if sd == 'L' else Pm - 1), c[1] if sd in 'LR' else (0 if sd == 'T' else Pm - 1))
        b.line(c, end, ('mstub', e))
        b.arms[sd] = e
    return b


def check_mblock(b):
    """check_block's contract for a block of its own pitch: floor on the border ring only at the arm midpoints, arms
    straight for 3 cells with walls beside; a stub 8-touches the board only at its own port cell (4-adjacent)."""
    W, H, m = b.W, b.H, b.mid
    cell = {'T': (m, 0), 'B': (m, H - 1), 'L': (0, m), 'R': (W - 1, m)}
    mids = {cell[a] for a in b.arms}
    for (x, y) in b.floor:
        if x in (0, W - 1) or y in (0, H - 1):
            assert (x, y) in mids, ('floor on border ring off an arm', b.kind, (x, y))
    for (mx, my) in mids:
        d = (0, 1) if my == 0 else (0, -1) if my == H - 1 else (1, 0) if mx == 0 else (-1, 0)
        for k in range(3):
            c = (mx + d[0] * k, my + d[1] * k)
            assert c in b.floor, ('arm not straight', b.kind, c)
            assert all(s not in b.floor for s in ((c[0] + d[1], c[1] + d[0]), (c[0] - d[1], c[1] - d[0]))),                 ('arm has a floor neighbour', b.kind, c)
    for c, o in b.owner.items():
        if o[0] != 'mstub':
            continue
        touch = [(c[0] + dx, c[1] + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                 if b.owner.get((c[0] + dx, c[1] + dy), ('',))[0] == 'mboard']
        assert len(touch) <= 1, ('stub touches the board in several cells', b.kind, c, touch)
        for t in touch:
            assert abs(t[0] - c[0]) + abs(t[1] - c[1]) == 1, ('stub touches the board diagonally', b.kind, c, t)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                o2 = b.owner.get((c[0] + dx, c[1] + dy))
                assert o2 is None or o2[0] == 'mboard' or o2 == o, ('two stubs 8-adjacent', b.kind, c)
    return True


def coin_lint(b):
    """Z1/Z2 lint (D_game.coin_lint) on the coin tile region of the coin block, plus the Z1 sufficient rule: no
    window cell within Chebyshev 3 of Z u {E} (windows exist only in other blocks, so the distance is at least the
    distance from Z u {E} to this block's border)."""
    import D_game as DG
    c = b.coin
    x0, y0 = c['A'][0] - 6, c['T'][1] - 8
    x1, y1 = c['B'][0] + 2, c['E'][1] + 4
    rows = []
    for y in range(y0, y1 + 1):
        r = ''
        for x in range(x0, x1 + 1):
            ch = b.floor.get((x, y))
            r += '#' if ch is None else ('T' if ch == 'T' else '.')
        rows.append(r)
    zx0, zx1, zy = c['A'][0] - x0, c['B'][0] - x0, c['T'][1] - y0
    L = DG.Level('\n'.join(rows) + f'\n:zone {zx0} {zy} {zx1} {zy}\n')
    lint = DG.coin_lint(L)
    ZE = [c['T'], c['A'], c['B'], c['E']]
    border = min(min(p[0], p[1], b.W - 1 - p[0], b.H - 1 - p[1]) for p in ZE)
    win_in_block = [p for p, o in b.owner.items() if o[0] == 'tile' and len(o) > 2 and o[2] in ('comp', 'port')]
    return dict(lint={str(k): v for k, v in lint.items()}, z_to_block_border=border,
                windows_in_coin_block=len(win_in_block), Z1_rule_ok=border > 3 and not win_in_block,
                Z2_ok=all(v['Z2_ok'] for v in lint.values()), Z1_ok=all(v['Z1_ok'] for v in lint.values()),
                tile='\n'.join(rows))


def window_reach():
    """exact per-window boulder reach (C-audit Z1 step 1) for the two window types of the main layer"""
    import A_core as K, A2_scd as S2
    out = {}
    for nm, rows in (('protodiode', S2.PROTODIODE), ('proto_precursor', S2.PROTO_PRECURSOR)):
        bd = K.Board(rows)
        C = K.explore(bd)
        reach = {bd.cells[i] for B in C.states for i in range(len(bd.cells)) if B >> i & 1}
        ports = {bd.cells[i] for i in bd.ports.values()}
        out[nm] = dict(states=len(C.states), reach=len(reach), port_cells_reached=len(reach & ports))
    return out


_TPL = {}
# crossover templates on disk: 'r6_' = routed by the review-6-repaired router (Ani placement, GX only on finished
# legs); the review-6 state's templates are the untagged xtemplate_<fx><fy><p>.json (kept for comparison)
TPL_TAG = os.environ.get('LGEN_TPL_TAG', 'r6_')


def floor_hash(b):
    """geometry key of a block for the router: its floor cells (boulders ignored: the router reads only floor),
    owners' roles and placed tiles. Two blocks with equal hash get the same routing."""
    import hashlib
    h = hashlib.sha256()
    h.update(repr(sorted(b.floor)).encode())
    h.update(repr([(t['kind'], sorted(map(tuple, t['cells'])), sorted(t['legs'])) for t in b.tiles]).encode())
    return h.hexdigest()[:16]


# F4 (r6b): the finite template library. Only blocks with placed tiles (G's) need a routed check path; over 320
# instances (seeds 3, 11) these are exactly the scdc (4P wide) and dio (2P wide) tile blocks with all their top arms,
# and the 4 crossover flips, each in 2 parities: 12 templates, routed once and stored on disk. Every other block type
# (E, V, H, BL, BR, jn of any width, coin) carries only the two straight lanes (asserted in _block_template).
LIBRARY_TILES = {('scdc', 4), ('dio', 2)}


def template_for(key, b, parity, coin=None, x_ok=True):
    """cached block template (crossover templates also cached on disk, build/lgen/xtemplate_<fx><fy><parity>.json;
    r6b: the G'-carrying tile templates too, build/lgen/ttemplate_<tag><kind>_<parity>.json, checked against the
    block's floor hash)"""
    k = (key, parity)
    if k in _TPL:
        return _TPL[k]
    path = None
    if key[0] == 'tile' and b.tiles:
        full = all(('T', i) in b.arms for i in range(b.W // P))
        assert (key[1], b.W // P) in LIBRARY_TILES and full, ("G'-carrying tile block outside the library", key)
        path = os.path.join(OUT, f'ttemplate_{TPL_TAG}{key[1]}_{parity}.json')
        if os.path.exists(path):
            rec = json.load(open(path))
            assert rec.get('floor_hash') == floor_hash(b), ('library tile template geometry mismatch', key, parity)
            _TPL[k] = rec
            return rec
        if not x_ok:
            return None
    if key[0] == 'X':
        path = os.path.join(OUT, f'xtemplate_{TPL_TAG}{int(key[1])}{int(key[2])}{parity}.json')
        if os.path.exists(path):
            rec = json.load(open(path))
            assert rec.get('floor_hash') == floor_hash(b), ('crossover template geometry mismatch', key, parity, path)
            _TPL[k] = rec
            return rec
        if not x_ok:
            return None
    rec = template_record(block_template(b, parity, coin))
    rec['floor_hash'] = floor_hash(b)
    if path:
        json.dump(rec, open(path, 'w'), indent=1)
    _TPL[k] = rec
    return rec


def assemble(inst, name, x_ok=True):
    t0 = time.time()
    N = netlist(inst)
    truth = g6_winner(inst)
    w_net, n_net = solve_net(N)
    contract(N)
    Bs = Bus(N)
    Bs.order()
    Bs.rows()
    Lv = Level(Bs)
    Lv.blocks()
    Lv.check_static()
    paths = Lv.trace()
    Nn = Lv.network(paths)
    w_lay, n_lay = solve_net(Nn)
    R = Lv.R
    res = dict(name=name, instance=dict(F=inst['F'], X=inst['X'], Y=inst['Y'], a0=inst['a0'], first=inst['first']),
               g6=truth, S1_netlist=dict(win=w_net, positions=n_net), S2_layout=dict(win=w_lay, positions=n_lay),
               netlist=stats(N), tiles=len(Bs.tiles), edges=len(Bs.edges), columns=Lv.C, track_rows=R,
               crossovers=Lv.nX, static_checks='passed (check_block, check_tile_block, arm matching, trace)')
    tot = defaultdict(int)
    gp = {1: 0, 2: 0}
    missing = []
    for (c, r), k in sorted(Lv.g.items(), key=lambda kv: str(kv)):
        par = (R - r) % 2
        if k[0] == 'tile':
            if k[2] != 0:
                continue
            b = Lv.tb[k[1]]
            T = Bs.tiles[k[1]]
            key = ('tile', T['kind'], b.W, tuple(sorted(str(a) for a in b.arms)))
            rec = template_for(key, b, par, getattr(b, 'coin', None), x_ok=x_ok)
            if rec is None:
                missing.append((key, par))
                continue
        elif k[0] == 'X':
            rec = template_for(k, Lv.lib[k], par, x_ok=x_ok)
            if rec is None:
                missing.append((k, par))
                continue
        else:
            rec = template_for((k,), Lv.lib[k], par)
        for lv, v in rec['levels'].items():
            assert v['err'] is None, ('template failed', k, par, v['err'])
            gp[int(lv)] += v['gprimes']
        for ev, n in rec['counts'].items():
            tot[ev] += n
        for yl, n in rec['lanes'].items():
            tot['CHX.lane'] += n
        if rec.get('placement') == 'hk':
            tot['hook crossings (bound, not drawn)'] += sum(v.get('hooks_jumps', 0) for v in rec['levels'].values())
    tot['SX.margin'] += 1           # the descent from t to the bottom strip crosses row 0's bottom lane once
    nscd = sum(1 for T in Bs.tiles.values() if T['kind'] in ('scd', 'scdc'))
    ndio = sum(1 for T in Bs.tiles.values() if T['kind'] == 'dio')
    exp1 = nscd + 20 * Lv.nX
    exp2 = 4 * nscd + ndio + 126 * Lv.nX
    res['missing_templates'] = sorted({str(m) for m in missing})
    res['gprimes_routed'] = gp
    res['gprimes_expected'] = {1: exp1, 2: exp2}
    res['check_locations'] = 25 * exp1 + 4 * (ndio + 46 * Lv.nX)
    res['legs'] = 21 * exp1 + 4 * (ndio + 46 * Lv.nX)
    res['coverage_ok'] = (not missing) and gp[1] == exp1 and gp[2] == exp2 and \
        tot.get('Wt', 0) == res['legs'] and tot.get('Wb', 0) == res['legs']
    res['crossings'] = dict(tot)
    nchecks = 2 * exp1 + 4 * 2 * (nscd + 20 * Lv.nX) + 2 * 2 * (nscd + 20 * Lv.nX) + 2 * (ndio + 46 * Lv.nX)
    wcx = tot.get('Wt', 0) + tot.get('Wb', 0) + sum(v for k, v in tot.items() if k.startswith('CHX')) + \
        tot.get('GX', 0)
    res['contacts_drawn'] = dict(OP=tot.get('OP', 0), SD=tot.get('SD', 0), OUT=tot.get('OUT', 0), expected=nchecks,
                                 ok=tot.get('OP', 0) == tot.get('SD', 0) == tot.get('OUT', 0) == nchecks)
    res['coverage_ok'] = res['coverage_ok'] and res['contacts_drawn']['ok']
    res['machinery'] = dict(WCX=wcx, SO=nchecks, SD=nchecks,
                            SX=tot.get('SX', 0) + tot.get('WSX', 0) + tot.get('XW', 0) + tot.get('SX.margin', 0))
    res['machinery_blocks_est'] = sum(MACHINE_BLOCKS[k] * v for k, v in res['machinery'].items())
    mb = machinery_boards()
    if mb:          # counts backed by the concrete boards (placement / hook curves still not drawn: M-machinery.md)
        m = res['machinery']
        res['machinery_boards'] = dict(
            per_board=mb, boulders=sum(mb[k]['boulders'] * v for k, v in m.items()),
            floor_cells=sum(mb[k]['floor'] * v for k, v in m.items()),
            board_cells=sum(mb[k]['W'] * mb[k]['H'] * v for k, v in m.items()),
            source='build/machinery (M_build.py, checked by M_verify.py)')
    floor = sum(len(Lv.lib[k].floor) for k in Lv.g.values() if k[0] != 'tile') + sum(len(b.floor) for b in Lv.tb.values())
    boulders = 166 * Lv.nX + sum(sum(1 for ch in b.floor.values() if ch == '0') for b in Lv.tb.values())
    res['main_layer'] = dict(macro_cols_rows=(Lv.C + 2, R + 1), cells_wh=((Lv.C + 2) * P, (R + 1) * P + 8),
                             floor_cells=floor, boulders=boulders, teleport_traps=1 if 'coin' in N.g else 0)
    coin_b = [b for tn, b in Lv.tb.items() if Bs.tiles[tn]['kind'] == 'coin']
    res['Z'] = coin_lint(coin_b[0]) if coin_b else 'no coin (n_Y = 0)'
    res['secs'] = round(time.time() - t0, 1)
    return res, Lv


def macro_text(Lv):
    ch = {'V': '|', 'H': '-', 'BL': '+', 'BR': '+'}
    out = []
    for r in range(Lv.R, -1, -1):
        row = ''
        for c in range(Lv.C):
            k = Lv.g.get((c, r))
            if k is None:
                row += ' '
            elif k[0] == 'X':
                row += 'X'
            elif k[0] == 'tile':
                kind = Lv.Bs.tiles[k[1]]['kind']
                row += {'scdc': 'S', 'scd': 'S', 'dio': 'd', 'coin': 'C', 'jn': 'j'}[kind] if k[2] == 0 else '_'
            else:
                row += ch[k]
        out.append(row)
    return '\n'.join(out)


def noforce_winner(inst):
    """negative control: B's write paths without the forced closes (review5_t1 'noforce'), as a netlist"""
    return R5.build(inst['F'], inst['X'], inst['Y'], inst['a0'], 'noforce', inst['first'])[0]


def validate(Rt, b):
    """independent replay of a routed block template (does not trust the router's bookkeeping):
    (1) the chain pieces are 4-connected point sequences; (2) a floor point is visited only as the middle of a
    straight crossing whose two neighbours are non-floor; (3) no window / location / coin / corner point is ever
    crossed, no point within the coin halo is used; (4) every leg slot of every tile in the block is crossed exactly
    once, and nothing else crosses a slot; (5) every point is used at most twice, and twice only for a straight
    perpendicular self-crossing (SX); (6) per leg: Wt crossed before Wb on the same chain; (7) lane rows only as
    lane points."""
    W = Rt.W
    errs = []
    tr, cid, starts = [], [], set()
    st_idx = set(Rt.starts)
    nout = sum(1 for e in Rt.events if e[0] == 'OUT')
    for c in sorted(set(Rt.tcid)):                  # concatenate the chains, each in its own order (pieces kept)
        first = True
        for k, (p, kc) in enumerate(zip(Rt.trace, Rt.tcid)):
            if kc != c:
                continue
            if first or k in st_idx:
                starts.add(len(tr))
            first = False
            tr.append(p)
    if len(Rt.starts) != len(set(Rt.tcid)) + nout:
        errs.append(('piece count', len(Rt.starts), len(set(Rt.tcid)), nout))
    seen = defaultdict(list)
    for k, p in enumerate(tr):
        seen[p].append(k)
        if k and k not in starts:
            q = tr[k - 1]
            if abs(p - q) not in (1, W):
                errs.append(('not 4-connected', k))
    for p, ks in seen.items():
        if Rt.fl[p]:
            if len(ks) != 1:
                errs.append(('floor point used twice', p))
            k = ks[0]
            if k == 0 or k + 1 >= len(tr) or (k in starts) or (k + 1 in starts):
                errs.append(('floor point at a chain end', p))
                continue
            a, c = tr[k - 1], tr[k + 1]
            if a - p != p - c or Rt.fl[a] or Rt.fl[c]:
                errs.append(('floor crossing not straight', p))
            if Rt.role[p] in (WIN, LOC, COINC):
                errs.append(('forbidden point crossed', p, Rt.role[p]))
        else:
            if len(ks) > 2:
                errs.append(('point used 3 times', p))
            if len(ks) == 2:
                k1, k2 = ks
                d1 = {tr[k1 - 1] - p, tr[k1 + 1] - p} if 0 < k1 < len(tr) - 1 else set()
                d2 = {tr[k2 - 1] - p, tr[k2 + 1] - p} if 0 < k2 < len(tr) - 1 else set()
                if not (d1 in ({1, -1}, {W, -W}) and d2 in ({1, -1}, {W, -W}) and d1 != d2):
                    errs.append(('self-crossing not straight/perpendicular', p))
        if Rt.near[p]:
            errs.append(('coin halo used', p))
    slots = {}
    for t in b.tiles:
        for ln, L in t['legs'].items():
            slots[Rt.R(L['Wt'])] = (t['id'], ln, 'Wt')
            slots[Rt.R(L['Wb'])] = (t['id'], ln, 'Wb')
    crossed = {p: slots[p] for p in seen if p in slots}
    if len(crossed) != len(slots):
        errs.append(('slots not crossed', len(slots) - len(crossed)))
    pos = {}
    for p, (tid, ln, s) in crossed.items():
        pos[(tid, ln, s)] = seen[p][0]
    for (tid, ln, s), k in pos.items():
        if s == 'Wt' and (tid, ln, 'Wb') in pos and pos[(tid, ln, 'Wb')] < k:
            errs.append(('Wb before Wt', tid, ln))
    ev = {f: kind for kind, f, _ in Rt.events}
    for p in crossed:
        if ev.get(p) not in ('Wt', 'Wb'):
            errs.append(('slot crossed by a non-delimiter', p))
    rr = validate_rules(Rt, b, seen)
    errs += rr['errors']
    return dict(ok=not errs, errors=errs[:10], points=len(tr), floor_crossings=sum(1 for p in seen if Rt.fl[p]),
                self_crossings=sum(1 for p, ks in seen.items() if len(ks) == 2), slots=len(slots),
                rules=rr['counts'])


def validate_rules(Rt, b, seen=None):
    """review 6 repairs, replayed independently of the router's dead/finished bookkeeping:
    (F1) time order = level-1 G's in routing order, then level-2 G's; a GX (WCX on a leg's g-side stub) is allowed
         only on a leg of a G' that ended EARLIER in that order (never its own G', never a pending one); a CHX on an
         own middle segment only after the G''s last Wb; never a crossing of the own SCD's interior at level 1;
    (F2) Ani placement: every check i of every G' has exactly one OP, SD, OUT event, in that order; the SO box p
         is 4-adjacent to the OP point j and is the first point of the next piece; the SD point q ends a piece; the
         wire points tb, ta are 4-adjacent to the boxes and to the location cells b_i, a_i and are never chain points;
         no point of a location's wire is crossed or used by any chain."""
    W = Rt.W
    errs = []
    cnt = defaultdict(int)
    if seen is None:
        seen = defaultdict(list)
        for k, p in enumerate(Rt.trace):
            seen[p].append(k)
    segs = sorted(Rt.gseg, key=lambda g: (g['level'], g['e0']))
    finished = set()
    inseg = {}
    for g in segs:
        for e in range(g['e0'], g['e1']):
            inseg[e] = g
    order = {id(g): n for n, g in enumerate(segs)}
    fin_before = {}
    for g in segs:
        fin_before[id(g)] = set(finished)
        finished |= g['own']
    all_l1 = {l for g in segs if g['level'] == 1 for l in g['own']}
    for e, (kind, f, info) in enumerate(Rt.events):
        g = inseg.get(e)
        if kind == 'GX' or (kind == 'CHX' and Rt.role[f] == GXR):
            lg = Rt.leg.get(f)
            if g is None:            # lane return after the block's last G': everything of that level finished
                ok = lg in (all_l1 if Rt.tcid[Rt.ev_ti[e]] == 1 else finished)
            else:
                ok = lg in fin_before[id(g)] and lg not in g['own']
            cnt['GX'] += 1
            if not ok:
                errs.append(('GX on a leg whose G\' is not finished', lg, g['key'] if g else None))
                cnt['GX_bad'] += 1
        if g is None or kind not in ('CHX', 'GX'):
            continue
        lg = Rt.leg.get(f)
        if Rt.role[f] == MIDR and lg in g['own']:
            last_wb = max(k for k in range(g['e0'], g['e1']) if Rt.events[k][0] == 'Wb')
            cnt['CHX_own_mid'] += 1
            if e < last_wb:
                errs.append(('own middle crossed before the delimiters are done', lg, g['key']))
        if g['level'] == 1 and Rt.scd.get(f) == g['key'][0] and Rt.role[f] in (SCDINT, MIDR) and \
                not (lg and lg[1].startswith('tile.')):
            errs.append(('own SCD interior crossed at level 1', g['key']))
    if Rt.placement == 'ani':
        wires, wlev = set(), {}
        adjc = lambda u, v: abs(u - v) in (1, W)
        for g in segs:
            evs = [(e, Rt.events[e]) for e in range(g['e0'], g['e1']) if Rt.events[e][0] in ('OP', 'SD', 'OUT')]
            want = [(kk, i) for i in range(len(g['checks'])) for kk in ('OP', 'SD', 'OUT')]
            if [(x[1][0], x[1][2][1]) for x in evs] != want:
                errs.append(('contact order', g['key']))
                continue
            tree = {l: {t for t in Rt.tree0.get((g['key'], l), ()) if adjc(t, Rt.R(c))}
                    for l, c in g['locs'].items()}
            for i, (a, bb) in enumerate(g['checks']):
                (_, (_, j, (_, _, p, tb, wp, jpp))), (eq, (_, q, (_, _, ta, wq, jpq))), (eo, (_, po, _)) =                     evs[3 * i: 3 * i + 3]
                k_out = Rt.ev_ti[eo]
                ok = po == p and adjc(p, j) and k_out in Rt.starts and Rt.trace[k_out] == p
                for box, w, t, l, jps in ((p, wp, tb, bb, jpp), (q, wq, ta, a, jpq)):
                    seq = [box] + list(w) + [t]
                    for u3, w3, v3 in zip(seq, seq[1:], seq[2:]):
                        wlev[w3] = (g['level'], u3, v3)
                    used_j = []
                    for u, v in zip(seq, seq[1:]):
                        if adjc(u, v):
                            continue
                        m = (u + v) // 2                 # an SX jump of the wire over a straight chain point
                        if abs(u - v) in (2, 2 * W) and m in jps and m in seen and not Rt.fl[m] and                                 {abs(x - m) for x in (Rt.pn[m][0], Rt.pn[m][1])} == ({W} if abs(u - v) == 2 else {1})                                 and (g['level'] == 2 or Rt.pcid.get(m) == 1):
                            used_j.append(m)
                        else:
                            ok = False
                    ok &= used_j == list(jps) and t in tree[l]
                    ok &= not any(Rt.fl[u] for u in w)
                    if not jps:
                        tree[l] |= set(w)
                    wires |= set(w) | {t}
                    cnt['wire_SX'] += len(jps)
                # q ends its piece: the next trace entry of the same chain starts a piece (it is p)
                nxt = [k for k in range(Rt.ev_ti[eq] + 1, len(Rt.trace)) if Rt.tcid[k] == Rt.tcid[k_out]][:1]
                ok &= nxt == [k_out]
                if not ok:
                    errs.append(('contact geometry', g['key'], i))
                cnt['checks'] += 1
        # XW: a level-1 chain point that crosses a level-2 wire straight and perpendicular (SX, chain earlier)
        xwp = {}
        for e2, (kd, f2, _) in enumerate(Rt.events):
            if kd == 'XW':
                xwp[f2] = e2
        okx = set()
        for f2, e2 in xwp.items():
            ks = seen.get(f2, [])
            g2 = inseg.get(e2)
            wl = wlev.get(f2)
            if len(ks) == 1 and not Rt.occ[f2] and g2 is not None and g2['level'] == 1 and wl is not None                     and wl[0] == 2 and 0 < ks[0] < len(Rt.trace) - 1:
                a2, b2 = Rt.trace[ks[0] - 1], Rt.trace[ks[0] + 1]
                u2, v2 = wl[1], wl[2]
                if a2 + b2 == 2 * f2 and u2 + v2 == 2 * f2 and {abs(a2 - f2), abs(u2 - f2)} == {1, W}:
                    okx.add(f2)
                    cnt['XW'] += 1
                    continue
            errs.append(('bad wire crossing', f2))
        bad = [t for t in wires if (t in seen or Rt.occ[t]) and t not in okx]
        if bad:
            errs.append(('wire point used by a chain', len(bad)))
        if any(Rt.near[t] or Rt.fl[t] for t in wires):
            errs.append(('wire point on floor or in the coin halo',))
        cnt['wire_points'] = len(wires)
    return dict(errors=errs, counts=dict(cnt))


def gprime_items(Rt):
    """per routed G' (time order per level): its check-path piece as a list of items in trace order, for the
    abstract end-to-end test L_e2e.py: ('Wt'|'Wb', letter) delimiters; Router.classify kinds for every other
    crossing ('GXo', letter) / ('CHXm', letter) / ('GXf',) / ('GXp',) / ('W',); ('SXa', n) / ('SXb', n) the earlier
    and the later line of the n-th SX whose both lines lie on this piece (SX with another piece: no item, it is a
    leak-free pass); ('OP'|'SD'|'OUT', i) the contacts of check i."""
    first = {}
    for k, p in enumerate(Rt.trace):
        first.setdefault(p, k)
    segs = sorted(Rt.gseg, key=lambda g: (g['level'], g['e0']))
    finished = set()
    out = []
    for g in segs:
        items = []
        nsx = 0
        wsx = {}                       # wire SX over a chain point of THIS piece -> its SX id
        for e in range(g['e0'], g['e1']):
            kind, f, info = Rt.events[e]
            if kind == 'WSX':
                k0 = first[f]
                if g['t0'] <= k0 < g['t1'] and Rt.tcid[k0] == g['cid']:
                    wsx[f] = nsx
                    items.append((k0, ('SXa', nsx)))
                    nsx += 1
        for e in range(g['e0'], g['e1']):
            kind, f, info = Rt.events[e]
            ti = Rt.ev_ti[e]
            letter = lambda lg: lg[1].split('.')[-1]
            if kind in ('Wt', 'Wb'):
                items.append((ti, (kind, letter(info))))
            elif kind in ('WSX', 'XW'):
                pass                   # XW: SX of this piece with another G''s wire = leak-free pass (no item)
            elif kind in ('OP', 'SD'):
                # the wire's SX crossings, box -> location; one on another piece is a leak-free pass (no item)
                items.append((ti, (kind, info[1], [wsx[x] for x in info[-1] if x in wsx])))
            elif kind == 'OUT':
                items.append((ti, (kind, info[1])))
            elif kind == 'SX':
                k0 = first[f]
                if g['t0'] <= k0 < g['t1'] and Rt.tcid[k0] == g['cid']:
                    items.append((k0, ('SXa', nsx)))
                    items.append((ti, ('SXb', nsx)))
                    nsx += 1
            else:
                items.append((ti, Rt.classify(kind, f, g['own'], finished)))
        finished |= g['own']
        items.sort(key=lambda x: x[0])
        out.append(dict(key=[str(v) for v in g['key']], level=g['level'], kind=g['kind'], checks=g['checks'],
                        items=[list(it) for _, it in items]))
    return out


# ============================================================ 9. S3: abstract postselection end-to-end (SCD level)
def checkable_scd():
    """abstract checkable SCD: ideal button SCD (O opens, I -> J iff open, closes) plus the O -> J leak of the raw
    Fig. 37 composite (B2_e2e 'raw'), which leaves it broken ('x'); broken is absorbing and keeps the leak
    (O -> J any number of times); by definition of broken (Def. 5.2) the check [O -> O, I -> J] is legal
    exactly from 'o' and 'c', so 'x' has no I -> J."""
    import A_core as K
    return K.abstract(['I', 'J', 'O'], 'c', {
        'c': {'O': [('O', 'o'), ('J', 'x')]},
        'o': {'O': [('O', 'o'), ('J', 'x')], 'I': [('J', 'c')]},
        'x': {'O': [('O', 'x'), ('J', 'x')]}})


def s3_game(Nn, chain=True, leak=True, chx=True, leaky=None):
    import A_core as K, A_check as AC, B2_e2e as BE
    Bd = BE.Builder()
    coin = None
    scds = []
    dios = [n for n, G in Nn.g.items() if G['kind'] == 'dio']
    split = {}
    for n in (dios if chain and chx else []):
        split[n] = Bd.node(f'chx.{n}')
    for n, G in sorted(Nn.g.items()):
        k, pm = G['kind'], G['ports']
        if k == 'dio':
            Bd.add(n, AC.T_diode(), {'A': split.get(n, pm['A']), 'B': pm['B']})
        elif k == 'xo':
            Bd.add(n, K.abstract(sorted(pm), 'x', {'x': {'A1': [('B1', 'x')], 'A2': [('B2', 'x')]}}), dict(pm))
        elif k == 'coin':
            coin = (pm['E'], [pm['A'], pm['B']])
        elif k == 'scd':
            scds.append(n)
    cio = []
    for n in scds:
        G = Nn.g[n]
        S = checkable_scd() if leak and (leaky is None or n in leaky) else AC.T_scd_button()

        def place(gside, n=n, S=S, G=G):
            Bd.add(n, S, dict(gside), G['init'])
            return {}
        if chain:
            cio.append(Bd.gprime(n, place, dict(G['ports']), [('O', 'O'), ('I', 'J')]))
        else:
            place(dict(G['ports']))
    t = Nn.goal
    if not chain:
        return BE.Game(Bd.gs, coin, Nn.start, t, Bd.inits)
    cur = t
    chxs = []
    for n, a in split.items():                    # CHX on every diode input hallway (main corridor x chain)
        bt, tp = Bd.wcx(Nn.g[n]['ports']['A'], a, f'{n}.chx')
        chxs.append((bt, tp))
    seq = list(cio)
    for i, x in enumerate(chxs):                  # interleave the CHX among the G's along the chain
        seq.insert(min(len(seq), (i * (len(cio) + 1)) // max(1, len(chxs)) + i), x)
    for a, b in seq:
        Bd.chain(cur, a)
        cur = b
    Bd.chain(cur, 'g')
    return BE.Game(Bd.gs, coin, Nn.start, 'g', Bd.inits)


def s3(inst, cap=4_000_000, group=2):
    """per instance: the generated network with the SCD-level check path; leaks enabled on groups of `group` SCDs
    (every SCD in some group); 'checked' must equal G6 in every run; 'nochain' (goal t, no check path) shows
    whether the leak is exploitable; 'noleak' = ideal SCDs + chain."""
    N = netlist(inst)
    contract(N)
    Bs = Bus(N)
    Bs.order()
    Bs.rows()
    Lv = Level(Bs)
    Lv.blocks()
    Nn = Lv.network(Lv.trace())
    scds = sorted(n for n, G in Nn.g.items() if G['kind'] == 'scd')
    groups = [scds[i:i + group] for i in range(0, len(scds), group)]
    out = dict(scds=len(scds), runs=0, checked=set(), nochain=set(), maxpos=0, caps=0)
    G = s3_game(Nn, leak=False)
    r, _, _ = G.solve(cap=cap)
    out['noleak'] = r['win']
    for gr in groups:
        for mode, kw in (('checked', {}), ('nochain', dict(chain=False))):
            G = s3_game(Nn, leaky=set(gr), **kw)
            try:
                r, _, _ = G.solve(cap=cap)
            except RuntimeError:
                out['caps'] += 1
                continue
            out[mode].add(r['win'])
            out['maxpos'] = max(out['maxpos'], r['positions'])
            out['runs'] += 1
    out['checked'], out['nochain'] = sorted(out['checked']), sorted(out['nochain'])
    return out

if __name__ == '__main__' and '--tile' in sys.argv:
    rng = random.Random(1)
    inst = random_instance(rng)
    N = netlist(inst); contract(N)
    B = Bus(N); B.order(); B.rows()
    Lv = Level(B); Lv.blocks()
    for kind in ('scdc', 'dio'):
        tn = [t for t in B.tiles if B.tiles[t]['kind'] == kind][0]
        for par in (0, 1):
            r = block_template(Lv.tb[tn], par)
            print(kind, par, r['lanes'], {k: (v['gprimes'], v['err'], v['secs']) for k, v in r['levels'].items()},
                  summarize(r))
            for k, v in r['levels'].items():
                for l in (v['log'] or [])[:30]:
                    print('   ', k, l)


if __name__ == '__main__' and '--s1' in sys.argv:
    rng = random.Random(1)
    for t in range(20):
        inst = random_instance(rng)
        N = netlist(inst)
        w, n = solve_net(N)
        contract(N)
        w2, n2 = solve_net(N)
        B = Bus(N)
        t0 = time.time()
        c = B.order()
        nx_, h = B.rows()
        Lv = Level(B)
        Lv.blocks()
        Lv.check_static()
        paths = Lv.trace()
        Nn = Lv.network(paths)
        w3, n3 = solve_net(Nn)
        print(g6_winner(inst), w, w2, w3, n, n2, n3, 'tiles', len(B.tiles), 'edges', len(B.edges), 'cols',
              len(B.col), 'X', c, nx_, Lv.nX, 'rows', h, 'dead', len(B.dead), f'{time.time()-t0:.1f}s')


if __name__ == '__main__' and '--dbg' in sys.argv:
    rng = random.Random(1)
    inst = random_instance(rng)
    N = netlist(inst); contract(N)
    B = Bus(N); B.order(); B.rows()
    Lv = Level(B); Lv.blocks()
    kind, par = sys.argv[2], int(sys.argv[3])
    tn = [t for t in B.tiles if B.tiles[t]['kind'] == kind][0]
    r = block_template(Lv.tb[tn], par)
    print(r['levels'])
    t = Lv.tb[tn].tiles[0]
    xs = [c[0] for c in t['cells']]; ys = [c[1] for c in t['cells']]
    print(render(r['router'], min(xs) - 8, min(ys) - 10, max(xs) + 9, max(ys) + 6))


if __name__ == '__main__' and '--xblock' in sys.argv:
    fx, fy, par = (int(v) for v in sys.argv[sys.argv.index('--xblock') + 1:][:3])
    os.makedirs(OUT, exist_ok=True)
    t0 = time.time()
    b = x_block(bool(fx), bool(fy))
    r = block_template(b, par)
    rec = template_record(r)
    rec['floor_hash'] = floor_hash(b)
    rec['secs'] = round(time.time() - t0, 1)
    json.dump(rec, open(os.path.join(OUT, f'xtemplate_{TPL_TAG}{fx}{fy}{par}.json'), 'w'), indent=1)
    print(json.dumps({k: v for k, v in rec.items() if k != 'levels'}),
          {k: (v['gprimes'], v['err'], v['secs']) for k, v in rec['levels'].items()}, flush=True)


if __name__ == '__main__' and '--mblock' in sys.argv:
    # the optional machinery block type: every board, all 8 symmetries, locality contract
    for kind in ('WCX', 'SX', 'SO', 'SD'):
        for s_ in range(8):
            b = m_block(kind, s_)
            check_mblock(b)
        print(f'{kind}: m_block pitch {b.W}, arms {sorted(b.arms)}, {sum(1 for ch in b.floor.values() if ch == "0")} '
              f'boulders; check_mblock ok under all 8 symmetries')

if __name__ == '__main__' and '--run' in sys.argv:
    a = sys.argv[sys.argv.index('--run') + 1:]
    K = int(a[0]) if a else 20
    seed = int(a[1]) if len(a) > 1 else 3
    os.makedirs(OUT, exist_ok=True)
    rng = random.Random(seed)
    rows, nc1, nc2 = [], [0, 0], [0, 0]
    t0 = time.time()
    for k in range(K):
        inst = random_instance(rng)
        res, Lv = assemble(inst, f'inst{seed}_{k}', x_ok=False)
        Nn = Lv.network(Lv.trace(), flip=True)
        wf, _ = solve_net(Nn)
        nc2[0] += 1
        nc2[1] += wf != res['g6']
        nc1[0] += 1
        nc1[1] += noforce_winner(inst) != res['g6']
        ok = res['g6'] == res['S1_netlist']['win'] == res['S2_layout']['win']
        if res['netlist'].get('scd', 0) <= 20:
            res['S3'] = s3(inst, cap=6_000_000, group=1)
            res['S3']['ok'] = res['S3']['checked'] == [res['g6']] and res['S3']['noleak'] == res['g6'] \
                and res['S3']['caps'] == 0
        name = res['name']
        json.dump(res, open(os.path.join(OUT, name + '.json'), 'w'), indent=1, default=str)
        open(os.path.join(OUT, name + '.txt'), 'w').write(macro_text(Lv) + chr(10))
        rows.append(dict(name=name, g6=res['g6'], S1=res['S1_netlist']['win'], S2=res['S2_layout']['win'],
                         ok=ok, nX=res['crossovers'], cov=res['coverage_ok'], missing=len(res['missing_templates']),
                         gp=res['gprimes_routed'], S3=res.get('S3'), locs=res['check_locations'], Z=None if isinstance(res['Z'], str)
                         else (res['Z']['Z1_ok'], res['Z']['Z2_ok'], res['Z']['Z1_rule_ok']),
                         machinery=res['machinery'], blocks=res['machinery_blocks_est'],
                         mboards=None if 'machinery_boards' not in res else
                         {k: res['machinery_boards'][k] for k in ('boulders', 'floor_cells', 'board_cells')},
                         main=res['main_layer'], N=sum(len(C) for C in inst['F']) + len(inst['X']) + len(inst['Y'])
                         + len(inst['F'])))
        print(json.dumps(rows[-1], default=str), flush=True)
    summ = dict(seed=seed, K=K, all_ok=all(r['ok'] for r in rows), yes=sum(r['g6'] for r in rows),
                no=sum(not r['g6'] for r in rows), coverage_all=all(r['cov'] for r in rows),
                S3_runs=sum(1 for r in rows if r['S3']), S3_all_ok=all(r['S3']['ok'] for r in rows if r['S3']),
                S3_leak_exploitable_without_chain=sum(1 for r in rows if r['S3'] and True in r['S3']['nochain']
                                                      and not r['g6']),
                NC1_noforce_mismatches=nc1, NC2_flipped_crossovers_mismatches=nc2, window_reach=window_reach(),
                rows=rows, secs=round(time.time() - t0, 1))
    json.dump(summ, open(os.path.join(OUT, f'summary_{seed}.json'), 'w'), indent=1, default=str)
    print(json.dumps({k: v for k, v in summ.items() if k != 'rows'}, default=str))
