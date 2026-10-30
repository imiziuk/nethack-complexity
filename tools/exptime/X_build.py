#!/usr/bin/env python3
"""X_build.py -- the ABD+20 Fig. 12 directed crossover as ONE concrete planar NetHack boulder map (workstream X).

Input (read-only imports): A2_xover.Build/xover (the VERIFIED fully flat network: 20 base button-SCDs + 46 diodes),
tools/visual/animate_gadgets.scd_build (the flat 17x20 SCD tile = Ani et al. Fig. 37: 1-toggle + precursor +
2 protodiodes, 6 boulders) and A2_scd.PROTODIODE (network diodes, 1 boulder each).

Pipeline
  1. wiring graph G (gadgets + junction nodes); planarity with the 4 external ports on the outer face in the
     interleaved order A1, A2, B1, B2 (and NON-planarity for A1, B1, A2, B2 = it really is a crossing) -- networkx;
  2. straight-line planar drawing: Tutte (barycentric) inside a square frame, then a crossing-preserving spreading
     pass (every move is rejected if it creates an edge crossing);
  3. tiles: each gadget = a copy of its tile under one of the 8 grid symmetries (the movement rules are symmetric), chosen
     so that its ports' cyclic order equals the drawing's rotation at that vertex; port stubs to even/even cells;
  4. corridors: one Steiner tree per junction node on the even/even sub-grid (1-wide corridors), sequential maze
     routing with re-ordering on failure; a net may never touch a cell 8-adjacent to another net or tile;
  5. assertions on the finished map (independent of the router): tiles pairwise not 8-adjacent; every corridor
     component (4-connected floor outside tiles) 8-touches tiles only in the zone of exactly the intended ports and no
     other corridor; one corridor component per junction node; external ports on the map boundary.
Outputs: build/xover/crossover.txt (map: '#' wall, '.' floor, '0' boulder) and build/xover/crossover.json (tiles,
ports, check ports, corridors). Usage: python X_build.py [--seed N]
"""
import json, math, os, random, sys, time
from collections import deque

import numpy as np
import networkx as nx

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools', 'visual'))
import A2_xover as X
import A2_scd as S2
import animate_gadgets as AG          # read-only: SCD tile (scd_build asserts its own internal adjacency)

OUT = os.path.join(ROOT, 'build', 'xover')
EXT = ['A1', 'A2', 'B1', 'B2']


# ============================================================ 1. network + graph
def network():
    bd = X.Build()
    X.xover(bd, 'A1', 'B1', 'A2', 'B2', 3)
    return bd


def graph(bd):
    G = nx.Graph()
    for n, (s, pm) in bd.g.items():
        for p, v in pm.items():
            assert not G.has_edge(n, 'N:' + v), ('gadget with two ports on one node', n, p, v)
            G.add_edge(n, 'N:' + v, port=p)
    return G


def planarity(G):
    res = {}
    for name, order in (('interleaved A1,A2,B1,B2', ['A1', 'A2', 'B1', 'B2']),
                        ('non-interleaved A1,B1,A2,B2', ['A1', 'B1', 'A2', 'B2'])):
        H = G.copy()
        for e in EXT:
            H.add_edge('hub', 'N:' + e)
        for a, b in zip(order, order[1:] + order[:1]):
            H.add_edge('N:' + a, 'N:' + b)
        res[name] = nx.check_planarity(H)[0]
    res['G alone'] = nx.check_planarity(G)[0]
    return res


# ============================================================ 2. planar drawing
def _orient(a, b, c):
    return (b[..., 0] - a[..., 0]) * (c[..., 1] - a[..., 1]) - (b[..., 1] - a[..., 1]) * (c[..., 0] - a[..., 0])


def _cross(p1, p2, A, B):
    d1, d2 = _orient(A, B, p1), _orient(A, B, p2)
    d3, d4 = _orient(p1, p2, A), _orient(p1, p2, B)
    return ((d1 * d2) < 0) & ((d3 * d4) < 0)


def drawing(G, kind, seed):
    rng = np.random.RandomState(seed)
    H = G.copy()
    pin = {'N:A1': (0, .5), 'N:A2': (.5, 0), 'N:B1': (1, .5), 'N:B2': (.5, 1),
           'c:TL': (0, 0), 'c:TR': (1, 0), 'c:BR': (1, 1), 'c:BL': (0, 1)}
    ring = ['N:A2', 'c:TR', 'N:B1', 'c:BR', 'N:B2', 'c:BL', 'N:A1', 'c:TL']
    for a, b in zip(ring, ring[1:] + ring[:1]):
        H.add_edge(a, b)
    V = list(H)
    ix = {v: i for i, v in enumerate(V)}
    E = np.array([(ix[a], ix[b]) for a, b in H.edges()])
    P = np.array([pin.get(v, (.5 + rng.rand() * .01, .5 + rng.rand() * .01)) for v in V])
    nb = [[ix[u] for u in H[v]] for v in V]
    free = [i for i, v in enumerate(V) if v not in pin]
    for _ in range(3000):                                   # Tutte / barycentric
        for i in free:
            P[i] = P[nb[i]].mean(0)
    R = np.array([{'scd': .055, 'dio': .022}.get(kind.get(v), .012) for v in V])
    inc = [np.where((E[:, 0] == i) | (E[:, 1] == i))[0] for i in range(len(V))]
    noninc = [[np.where((E[:, 0] != E[e, 0]) & (E[:, 1] != E[e, 0]) & (E[:, 0] != E[e, 1]) & (E[:, 1] != E[e, 1]))[0]
               for e in inc[i]] for i in range(len(V))]

    def ok(i, q):
        Q = P.copy()
        Q[i] = q
        for e, oth in zip(inc[i], noninc[i]):
            a, b = E[e]
            if _cross(Q[a], Q[b], Q[E[oth, 0]], Q[E[oth, 1]]).any():
                return False
        return True

    step = .02
    for sweep in range(500):
        for i in rng.permutation(free):
            d = P[i] - P
            dist = np.sqrt((d ** 2).sum(1)) + 1e-9
            want = (R[i] + R) * 1.7
            f = ((np.maximum(want - dist, 0) / dist)[:, None] * d).sum(0)
            for j in nb[i]:
                f -= (P[i] - P[j]) * .05
            n = np.linalg.norm(f)
            if n < 1e-12:
                continue
            q = P[i] + f / n * min(step, n)
            if 0 < q[0] < 1 and 0 < q[1] < 1 and ok(i, q):
                P[i] = q
        step *= .995
    # final planarity of the straight-line drawing (all edges incl. frame)
    for e in range(len(E)):
        a, b = E[e]
        oth = np.where((E[:, 0] != a) & (E[:, 1] != a) & (E[:, 0] != b) & (E[:, 1] != b))[0]
        assert not _cross(P[a], P[b], P[E[oth, 0]], P[E[oth, 1]]).any(), 'drawing not planar'
    return {v: (float(P[ix[v]][0]), float(P[ix[v]][1])) for v in G}


# ============================================================ 3. tiles
class Tile:
    """local tile: cells {(x,y): ch} (only floor-ish chars: '.', '0'), ports {name: (cell, dir, zone)},
    comps [(name, kind 'pp'|'pd', (ox, oy))], checks {name: [cells]}"""
    def __init__(self, kind, cells, ports, comps, checks, W, H):
        self.kind, self.cells, self.ports, self.comps, self.checks, self.W, self.H = kind, cells, ports, comps, checks, W, H


def scd_tile():
    rows, owner = AG.scd_build()
    cells = {}
    for y, r in enumerate(rows):
        for x, ch in enumerate(r):
            if ch != '#':
                cells[(x, y)] = '0' if ch == '0' else '.'
    # closed door: precursor blocks at local track x=3,5 (A2: (3,5) = closed); the tile ships with (4,6) = open
    _, ox, oy = AG.SCD_PARTS['prec']
    for x in (4, 6):
        cells[(ox + x, oy + 2)] = '.'
    for x in (3, 5):
        cells[(ox + x, oy + 2)] = '0'
    zone = lambda c: [cell for cell, o in owner.items() if o == 'corr:' + c]
    ports = {'O': (AG.SCD_PORTS['O'], (-1, 0), zone('O')), 'I': (AG.SCD_PORTS['I'], (-1, 0), zone('I')),
             'J': (AG.SCD_PORTS['J'], (1, 0), zone('J'))}
    comps = [(n, 'pp' if n in ('tog', 'prec') else 'pd', (ox_, oy_)) for n, (_, ox_, oy_) in AG.SCD_PARTS.items()]
    checks = {}
    for n, (loc, ox_, oy_) in AG.SCD_PARTS.items():
        for y, r in enumerate(loc):
            for x, ch in enumerate(r):
                if ch in 'dg':                                  # hidden check pockets D, G
                    checks[f'{n}.{ch.upper()}'] = [(ox_ + x, oy_ + y)]
    checks['tog.ABC'] = zone('tT')                              # toggle's joined A/B/C hallway (closed T)
    checks['prec.ABC'] = zone('T')                              # precursor's T junction (A/B/C hallways)
    checks['d1.CD'] = zone('cd1')
    checks['d2.CD'] = zone('cd2')
    return Tile('scd', cells, ports, comps, checks, AG.SCD_W, AG.SCD_H)


DIODE_ROWS = ["#.#.##",
              "#.0..#",
              "##.#.#",
              "##...#",
              "######"]


def diode_tile():
    cells = {(x, y): ch for y, r in enumerate(DIODE_ROWS) for x, ch in enumerate(r) if ch != '#'}
    ports = {'A': ((1, 0), (0, -1), [(1, 0)]), 'B': ((3, 0), (0, -1), [(3, 0)])}
    return Tile('dio', cells, ports, [('d', 'pd', (0, 0))], {'d.CD': [(2, 3), (3, 3), (4, 3)]},
                len(DIODE_ROWS[0]), len(DIODE_ROWS))


def sym(t, x, y, W, H):
    """grid symmetry t in 0..7 of the W x H box -> new (x, y)"""
    if t & 4:
        x = W - 1 - x
    for _ in range(t & 3):                                       # rotate 90 deg: (x, y) -> (H-1-y, x)
        x, y, W, H = H - 1 - y, x, H, W
    return x, y


def sym_dir(t, d):
    dx, dy = d
    if t & 4:
        dx = -dx
    for _ in range(t & 3):
        dx, dy = -dy, dx
    return dx, dy


def sym_size(t, W, H):
    return (H, W) if t & 1 else (W, H)


def cyc_equal(a, b):
    n = len(a)
    return any(list(a[k:] + a[:k]) == list(b) for k in range(n))


def choose_sym(tile, vpos, nbr):
    """nbr: {port: (x, y) of the neighbour node in the drawing}. Pick the symmetry whose port directions have the
    drawing's cyclic order (rotation system) and the smallest angular error."""
    best = None
    ang_n = {p: math.atan2(nbr[p][1] - vpos[1], nbr[p][0] - vpos[0]) for p in tile.ports}
    order_n = sorted(tile.ports, key=lambda p: ang_n[p])
    for t in range(8):
        W2, H2 = sym_size(t, tile.W, tile.H)
        cx, cy = (W2 - 1) / 2, (H2 - 1) / 2
        ang_p = {}
        for p, (c, d, _) in tile.ports.items():
            x, y = sym(t, *c, tile.W, tile.H)
            dx, dy = sym_dir(t, d)
            ang_p[p] = math.atan2(y + 4 * dy - cy, x + 4 * dx - cx)
        order_p = sorted(tile.ports, key=lambda p: ang_p[p])
        if len(tile.ports) >= 3 and not cyc_equal(order_p, order_n):
            continue
        err = sum(abs((ang_p[p] - ang_n[p] + math.pi) % (2 * math.pi) - math.pi) for p in tile.ports)
        if best is None or err < best[0]:
            best = (err, t)
    return best[1]


# ============================================================ 4. placement + routing
class Layout:
    def __init__(self, bd, pos, scale, margin=6):
        self.bd = bd
        T = {'scd': scd_tile(), 'dio': diode_tile()}
        self.tiles = {}
        self.node_of = {}           # (gadget, port) -> node
        xs, ys = [], []
        for n, (s, pm) in bd.g.items():
            tile = T['scd' if 'O' in pm else 'dio']
            t = choose_sym(tile, pos[n], {p: pos['N:' + v] for p, v in pm.items()})
            W2, H2 = sym_size(t, tile.W, tile.H)
            self.tiles[n] = dict(kind=tile.kind, sym=t, W=W2, H=H2, tile=tile,
                                 center=(pos[n][0] * scale, pos[n][1] * scale))
            for p, v in pm.items():
                self.node_of[(n, p)] = v
        self.pos = pos
        self.scale = scale
        self.margin = margin

    def place(self):
        """integer origins; stubs; owner map. Returns False if tiles collide."""
        sc = self.scale
        lo_x = lo_y = 10 ** 9
        hi_x = hi_y = -10 ** 9
        for n, T in self.tiles.items():
            cx, cy = T['center']
            T['ox'] = int(round(cx - T['W'] / 2))
            T['oy'] = int(round(cy - T['H'] / 2))
        # global frame: shift so that everything fits with a border; map is (2*NC+1) square-ish
        minx = min(T['ox'] for T in self.tiles.values()) - 12
        miny = min(T['oy'] for T in self.tiles.values()) - 12
        for T in self.tiles.values():
            T['ox'] -= minx
            T['oy'] -= miny
            T['ox'] += T['ox'] & 1                                 # even origin (cosmetic only)
            T['oy'] += T['oy'] & 1
        self.W = max(T['ox'] + T['W'] for T in self.tiles.values()) + 12
        self.H = max(T['oy'] + T['H'] for T in self.tiles.values()) + 12
        self.W += 1 - self.W % 2                                    # odd sizes: frame on even lines 0 and W-1
        self.H += 1 - self.H % 2
        self.own = np.zeros((self.H, self.W), dtype=np.int32)       # 0 free/wall, >0 owner id
        self.ch = np.full((self.H, self.W), '#', dtype='<U1')
        self.ids = {}
        self.names = [None]

        def oid(name):
            if name not in self.ids:
                self.ids[name] = len(self.names)
                self.names.append(name)
            return self.ids[name]

        # tiles
        for n, T in self.tiles.items():
            tile, t = T['tile'], T['sym']
            g = (lambda ox, oy, t, W, H: lambda c: (ox + sym(t, c[0], c[1], W, H)[0], oy + sym(t, c[0], c[1], W, H)[1]))(T['ox'], T['oy'], t, tile.W, tile.H)
            T['g'] = g
            k = oid('T:' + n)
            T['cells'] = []
            for c, chv in tile.cells.items():
                x, y = g(c)
                if not (0 < x < self.W - 1 and 0 < y < self.H - 1):
                    return False
                # tiles may not overlap / be 8-adjacent to another tile
                y0, y1, x0, x1 = max(y - 1, 0), y + 2, max(x - 1, 0), x + 2
                blk = self.own[y0:y1, x0:x1]
                if ((blk != 0) & (blk != k)).any():
                    return False
                self.own[y, x] = k
                self.ch[y, x] = chv
                T['cells'].append((x, y))
        # stubs (owned by the junction node's net)
        self.terms = {}                                             # node -> list of terminal cells
        for n, T in self.tiles.items():
            tile, t = T['tile'], T['sym']
            T['ports'] = {}
            xs = [c[0] for c in T['cells']]
            ys = [c[1] for c in T['cells']]
            bx0, bx1, by0, by1 = min(xs), max(xs), min(ys), max(ys)
            tcx, tcy = (bx0 + bx1) / 2, (by0 + by1) / 2
            for p, (c, d, zone) in tile.ports.items():
                v = self.node_of[(n, p)]
                k = oid('N:' + v)
                x, y = T['g'](c)
                dx, dy = sym_dir(t, d)
                stub = []
                while not ((dx > 0 and x >= bx1 + 2) or (dx < 0 and x <= bx0 - 2) or
                           (dy > 0 and y >= by1 + 2) or (dy < 0 and y <= by0 - 2)):
                    x, y = x + dx, y + dy
                    stub.append((x, y))
                px, py = (dy != 0), (dx != 0)                     # perpendicular axis
                if dx == 0 and x % 2:
                    x += 1 if x > tcx else -1
                    stub.append((x, y))
                if dy == 0 and y % 2:
                    y += 1 if y > tcy else -1
                    stub.append((x, y))
                if (dx and x % 2) or (dy and y % 2):
                    x, y = x + dx, y + dy
                    stub.append((x, y))
                for (sx, sy) in stub:
                    if not (0 < sx < self.W - 1 and 0 < sy < self.H - 1):
                        return False
                    if self.own[sy, sx] not in (0, k):
                        return False
                    self.own[sy, sx] = k
                    self.ch[sy, sx] = '.'
                T['ports'][p] = dict(cell=T['g'](c), zone=[T['g'](z) for z in zone], stub=stub, node=v)
                self.terms.setdefault(v, []).append((x, y))
        # stub cells must not be 8-adjacent to foreign tiles/stubs (except the own tile's port zone)
        for n, T in self.tiles.items():
            kt = self.ids['T:' + n]
            for p, P in T['ports'].items():
                k = self.ids['N:' + P['node']]
                zone = set(P['zone'])
                for (sx, sy) in P['stub']:
                    for ddx in (-1, 0, 1):
                        for ddy in (-1, 0, 1):
                            o = self.own[sy + ddy, sx + ddx]
                            if o in (0, k):
                                continue
                            if o == kt and (sx + ddx, sy + ddy) in zone:
                                continue
                            return False
        # external ports: openings in the frame, stub to an even/even terminal
        self.ext = {}
        mid_x, mid_y = (self.W // 2) & ~1, (self.H // 2) & ~1
        spots = {'A1': [(0, mid_y), (1, mid_y), (2, mid_y)], 'B1': [(self.W - 1, mid_y), (self.W - 2, mid_y), (self.W - 3, mid_y)],
                 'A2': [(mid_x, 0), (mid_x, 1), (mid_x, 2)], 'B2': [(mid_x, self.H - 1), (mid_x, self.H - 2), (mid_x, self.H - 3)]}
        for e, cells in spots.items():
            k = oid('N:' + e)
            for (x, y) in cells:
                if self.own[y, x] not in (0, k):
                    return False
                self.own[y, x] = k
                self.ch[y, x] = '.'
            self.ext[e] = cells[0]
            self.terms.setdefault(e, []).append(cells[-1])
        return True

    # ---------------- routing
    def route(self, seed=0, tries=60, log=print):
        rng = random.Random(seed)
        base_own = self.own.copy()
        base_ch = self.ch.copy()
        nodes = sorted(self.terms)
        span = lambda v: (max(x for x, _ in self.terms[v]) - min(x for x, _ in self.terms[v]) +
                          max(y for _, y in self.terms[v]) - min(y for _, y in self.terms[v]))
        order = sorted(nodes, key=span)
        for attempt in range(tries):
            self.own = base_own.copy()
            self.ch = base_ch.copy()
            self.paths = {}
            failed = []
            for v in order:
                if not self.route_net(v):
                    failed.append(v)
            log(f'  routing attempt {attempt}: {len(failed)} nets failed {failed[:8]}')
            if not failed:
                return True
            rest = [v for v in order if v not in failed]
            rng.shuffle(rest)
            order = failed + sorted(rest, key=span) if attempt % 2 == 0 else failed + rest
        return False

    def route_net(self, v):
        k = self.ids['N:' + v]
        foreign = (self.own != 0) & (self.own != k)
        bad = foreign.copy()
        bad[1:, :] |= foreign[:-1, :]
        bad[:-1, :] |= foreign[1:, :]
        b2 = bad.copy()
        b2[:, 1:] |= bad[:, :-1]
        b2[:, :-1] |= bad[:, 1:]
        bad = b2
        bad[0, :] = bad[-1, :] = True
        bad[:, 0] = bad[:, -1] = True
        terms = list(self.terms[v])
        for (x, y) in terms:
            assert x % 2 == 0 and y % 2 == 0, ('terminal off grid', v, (x, y))
            if bad[y, x]:
                return False
        tree = {terms[0]}
        todo = set(terms[1:]) - tree
        cells = set()
        W, H = self.W, self.H
        while todo:
            prev = {c: None for c in tree}
            dq = deque(tree)
            hit = None
            while dq:
                c = dq.popleft()
                if c in todo:
                    hit = c
                    break
                x, y = c
                for dx, dy in ((2, 0), (-2, 0), (0, 2), (0, -2)):
                    nx_, ny_ = x + dx, y + dy
                    if not (0 < nx_ < W - 1 and 0 < ny_ < H - 1):
                        continue
                    t = (nx_, ny_)
                    if t in prev or bad[ny_, nx_] or bad[y + dy // 2, x + dx // 2]:
                        continue
                    prev[t] = c
                    dq.append(t)
            if hit is None:
                return False
            c = hit
            while prev[c] is not None:
                p = prev[c]
                cells.add(c)
                cells.add(((c[0] + p[0]) // 2, (c[1] + p[1]) // 2))
                tree.add(c)
                c = p
            tree.add(hit)
            todo.discard(hit)
        for (x, y) in cells:
            self.own[y, x] = k
            self.ch[y, x] = '.'
        self.paths[v] = sorted(cells)
        return True


# ============================================================ 5. independent map checks
def check_map(rows, tiles, ext, bd):
    """rows: final map. tiles: {gadget: {'cells': [...], 'ports': {p: {'cell', 'zone'}}}}. Returns wiring
    {gadget: {port: corridor-component id}}, component cells. Raises AssertionError on any violation."""
    H, W = len(rows), len(rows[0])
    floor = {(x, y) for y in range(H) for x in range(W) if rows[y][x] != '#'}
    tile_of = {}
    for n, T in tiles.items():
        for c in T['cells']:
            assert c in floor
            assert c not in tile_of, ('tiles overlap', c)
            tile_of[c] = n
    # (i) tiles pairwise not 8-adjacent
    for c, n in tile_of.items():
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                o = tile_of.get((c[0] + dx, c[1] + dy))
                assert o is None or o == n, ('tiles 8-adjacent', n, o, c)
    # (ii) corridor components = 4-connected floor outside tiles
    corr = floor - set(tile_of)
    comp = {}
    ncomp = 0
    for c in sorted(corr):
        if c in comp:
            continue
        dq = deque([c])
        comp[c] = ncomp
        while dq:
            x, y = dq.popleft()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                t = (x + dx, y + dy)
                if t in corr and t not in comp:
                    comp[t] = ncomp
                    dq.append(t)
        ncomp += 1
    # (iii) distinct corridors never 8-adjacent; corridors 8-touch tiles only inside intended port zones,
    #       and the port cell itself is 4-adjacent to its corridor
    zone_of = {}
    for n, T in tiles.items():
        for p, P in T['ports'].items():
            for z in P['zone']:
                zone_of[z] = (n, p)
    touch = {}
    for c, k in comp.items():
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                t = (c[0] + dx, c[1] + dy)
                if t in comp:
                    assert comp[t] == k, ('corridors 8-adjacent', c, t)
                elif t in tile_of:
                    assert t in zone_of, ('corridor touches tile interior outside a port zone', c, t, tile_of[t])
                    touch.setdefault(zone_of[t], set()).add(k)
    wiring = {}
    for n, T in tiles.items():
        for p, P in T['ports'].items():
            ks = touch.get((n, p), set())
            assert len(ks) == 1, ('port not on exactly one corridor', n, p, ks)
            (k,) = ks
            x, y = P['cell']
            assert any(comp.get((x + dx, y + dy)) == k for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))), \
                ('port cell not 4-adjacent to its corridor', n, p)
            wiring.setdefault(n, {})[p] = k
    extk = {}
    for e, c in ext.items():
        x, y = c
        assert x in (0, W - 1) or y in (0, H - 1), ('external port not on the boundary', e)
        assert c in comp, e
        extk[e] = comp[c]
    # boundary: only the 4 openings
    for y in range(H):
        for x in range(W):
            if (x in (0, W - 1) or y in (0, H - 1)) and (x, y) in floor:
                assert (x, y) in ext.values(), ('hole in the frame', (x, y))
    # (iv) wiring graph == the VERIFIED A2 network up to renaming of junction nodes
    used = {k for d in wiring.values() for k in d.values()} | set(extk.values())
    assert used == set(range(ncomp)), ('dangling corridor component', set(range(ncomp)) - used)
    ren = {}
    for n, (s, pm) in bd.g.items():
        assert set(pm) == set(wiring[n]), n
        for p, v in pm.items():
            k = wiring[n][p]
            assert ren.setdefault(v, k) == k, ('node split over corridors', v)
    assert len(set(ren.values())) == len(ren), 'two nodes share a corridor'
    for e, k in extk.items():
        assert ren[e] == k, ('external port on wrong corridor', e)
    assert set(tiles) == set(bd.g)
    return wiring, extk, comp, ncomp


# ============================================================ compaction
def _removable_rows(fl, own, tile_ids):
    """rows y whose floor cells are all vertical pass-throughs of one corridor (floor above/below, same owner,
    walls left/right, no tile cell) and whose removal does not make two different owners 8-adjacent."""
    H, W = fl.shape
    out = []
    for y in range(1, H - 1):
        r = fl[y]
        if not r.any():
            ok = True
        else:
            xs = np.nonzero(r)[0]
            ok = (not np.isin(own[y, xs], tile_ids).any() and fl[y - 1, xs].all() and fl[y + 1, xs].all()
                  and (own[y - 1, xs] == own[y, xs]).all() and (own[y + 1, xs] == own[y, xs]).all()
                  and not fl[y, xs - 1].any() and not fl[y, xs + 1].any())
        if ok:
            a, b = y - 1, y + 1                                   # these become adjacent
            for dx in (-1, 0, 1):
                fa = fl[a, 1:-1]
                fb = fl[b, 1 + dx:W - 1 + dx]
                both = fa & fb
                if (own[a, 1:-1][both] != own[b, 1 + dx:W - 1 + dx][both]).any():
                    ok = False
                    break
        if ok:
            out.append(y)
    return out


def compact(L):
    """delete pass-through rows/columns (one at a time, re-checked) and remap every stored coordinate."""
    tile_ids = np.array([k for name, k in L.ids.items() if name.startswith('T:')])
    keep_x = list(range(L.W))
    keep_y = list(range(L.H))
    ch, own = L.ch, L.own
    changed = True
    while changed:
        changed = False
        for axis in (0, 1):
            fl = ch != '#'
            if axis == 1:
                cand = _removable_rows(fl.T, own.T, tile_ids)
            else:
                cand = _removable_rows(fl, own, tile_ids)
            # delete greedily, non-neighbouring candidates only (neighbours are re-checked next round)
            sel, last = [], -10
            for y in cand:
                if y > last + 1:
                    sel.append(y)
                    last = y
            if not sel:
                continue
            changed = True
            if axis == 0:
                ch = np.delete(ch, sel, 0)
                own = np.delete(own, sel, 0)
                keep_y = [v for i, v in enumerate(keep_y) if i not in set(sel)]
            else:
                ch = np.delete(ch, sel, 1)
                own = np.delete(own, sel, 1)
                keep_x = [v for i, v in enumerate(keep_x) if i not in set(sel)]
    mx = {v: i for i, v in enumerate(keep_x)}
    my = {v: i for i, v in enumerate(keep_y)}

    def f(c):
        return (mx[c[0]], my[c[1]]) if c[0] in mx and c[1] in my else None

    def fl_(cs):
        return [f(c) for c in cs if f(c) is not None]
    for n, T in L.tiles.items():
        T['cells'] = fl_(T['cells'])
        g0 = T['g']
        T['g'] = (lambda g0: lambda c: f(g0(c)))(g0)
        for p, P in T['ports'].items():
            P['cell'] = f(P['cell'])
            P['zone'] = fl_(P['zone'])
            P['stub'] = fl_(P['stub'])
    L.ext = {e: f(c) for e, c in L.ext.items()}
    L.paths = {v: fl_(p) for v, p in L.paths.items()}
    L.pos_map = (keep_x, keep_y)
    L.ch, L.own = ch, own
    L.H, L.W = ch.shape


# ============================================================ main
def main():
    seed = int(sys.argv[sys.argv.index('--seed') + 1]) if '--seed' in sys.argv else 1
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    bd = network()
    G = graph(bd)
    kind = {n: ('scd' if 'O' in pm else 'dio') for n, (s, pm) in bd.g.items()}
    nscd = sum(k == 'scd' for k in kind.values())
    print(f'== network: {len(bd.g)} gadgets ({nscd} SCDs, {len(bd.g) - nscd} diodes), '
          f'{G.number_of_nodes() - len(bd.g)} junction nodes, {G.number_of_edges()} gadget-port edges')
    pl = planarity(G)
    print('== planarity (networkx):', pl)
    assert pl['interleaved A1,A2,B1,B2'] and not pl['non-interleaved A1,B1,A2,B2']
    pos = drawing(G, kind, seed)
    print(f'== planar straight-line drawing done ({time.time() - t0:.0f}s)')
    scale = int(sys.argv[sys.argv.index("--scale") + 1]) if "--scale" in sys.argv else 260
    while True:
        L = Layout(bd, pos, scale)
        if L.place():
            print(f'  placement at scale {scale}: map {L.W} x {L.H}')
            if L.route(seed):
                break
            print('  routing failed, enlarging')
        scale = int(scale * 1.08)
        assert scale < 2000
    rows = [''.join(r) for r in L.ch]
    tiles = {n: dict(cells=T['cells'], ports={p: dict(cell=P['cell'], zone=P['zone']) for p, P in T['ports'].items()})
             for n, T in L.tiles.items()}
    check_map(rows, tiles, L.ext, bd)
    print(f'== routed map {L.W} x {L.H} passes the checks; compacting')
    compact(L)
    rows = [''.join(r) for r in L.ch]
    tiles = {n: dict(cells=T['cells'], ports={p: dict(cell=P['cell'], zone=P['zone']) for p, P in T['ports'].items()})
             for n, T in L.tiles.items()}
    wiring, extk, comp, ncomp = check_map(rows, tiles, L.ext, bd)
    print(f'== map checks passed: {len(tiles)} tiles pairwise non-adjacent, {ncomp} corridors (one per junction '
          f'node), never 8-adjacent, touching tiles only at the intended ports; wiring == A2 network')
    nb = sum(r.count('0') for r in rows)
    nfloor = sum(len(r) - r.count('#') for r in rows)
    print(f'== size: {L.W} x {L.H} = {L.W * L.H} cells, {nfloor} floor cells, {nb} boulders')
    # serialise
    out = dict(W=L.W, H=L.H, seed=seed, scale=L.scale, ext=L.ext, boulders=nb,
               tiles={}, corridors={v: p for v, p in L.paths.items()}, pos=pos)
    for n, T in L.tiles.items():
        tile, t = T['tile'], T['sym']
        out['tiles'][n] = dict(
            kind=T['kind'], sym=t, ox=T['ox'], oy=T['oy'], W=tile.W, H=tile.H, cells=T['cells'],
            local={f'{x},{y}': T['g']((x, y)) for (x, y) in tile.cells},
            local_ports={p: list(c) for p, (c, d, z) in tile.ports.items()},
            ports={p: dict(cell=P['cell'], zone=P['zone'], stub=P['stub'], node=P['node']) for p, P in T['ports'].items()},
            comps=[dict(name=cn, kind=ck, cells={f'{lx},{ly}': T['g']((ox + lx, oy + ly))
                                                  for ly, r in enumerate(S2.PROTO_PRECURSOR if ck == 'pp' else S2.PROTODIODE)
                                                  for lx, chh in enumerate(r) if chh != '#'})
                   for cn, ck, (ox, oy) in tile.comps],
            checks={c: [T['g'](z) for z in zs] for c, zs in tile.checks.items()})
    with open(os.path.join(OUT, 'crossover.txt'), 'w') as f:
        f.write('\n'.join(rows) + '\n')
    with open(os.path.join(OUT, 'crossover.json'), 'w') as f:
        json.dump(out, f)
    print(f'wrote build/xover/crossover.txt, crossover.json ({time.time() - t0:.0f}s)')


if __name__ == '__main__':
    main()
