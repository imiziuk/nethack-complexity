#!/usr/bin/env python3
"""M_build.py -- the check-path machinery (Ani et al. Figs. 19-21, 33) as concrete cell-level boulder boards.

Workstream M (proofs/exptime/M-machinery.md). Imports B2_ani (Fig. 32 boards WMC / NR / WO, the Fig. 33 / 20 / 21
wiring), A_core, X_build (Tile, choose_sym, sym*, Layout routing, check_map) read-only.

Hierarchy (each level is the wiring of B2_ani's composition functions, drawn as one planar map):
  SD  = WMC + NR (vertical) + NR + WO                                 (Fig. 33a, B2_ani.sd_from)
  SO  = WO + 4 SD                                                     (Fig. 33b, so_from)
  MSC = SD + WMC                                                      (Fig. 33c, msc_from)
  SX  = 2 SO + 3 SD                                                   (Fig. 20, sx_from)
  WCX = 3 SO + 3 MSC + 3 SD   (B2_ani's free hallway L-a is drawn as one corridor: node a = L)   (Fig. 21, wcx_from)
Every level: wiring graph + rim (external ports in the required cyclic order) planar (networkx); Tutte drawing with
the external ports pinned on the frame sides; every sub-board copied under a grid symmetry whose port cyclic order is
the drawing's rotation (X_build.choose_sym); port stubs; negotiated-congestion corridor routing (X_build.Layout);
X_build.check_map on the finished level (sub-boards pairwise not 8-adjacent, one corridor per node, corridors touch
sub-boards only at their port cells, wiring == the composition's network up to node renaming).
The finished board of a level is a Tile for the next level (cells = its floor, ports = its frame openings).

Outputs build/machinery/<G>.txt (map: '#' wall, '.' floor, '0' boulder; external port cells are the frame openings)
and <G>.json (size, boulders, ext port cells + side, every base-board copy: kind, symmetry, cell map from the
canonical Fig. 32 board (all bounding-box cells, walls included) to global cells, flat network wiring).
Usage: python M_build.py [G ...]   (default all five; each level reuses the lower levels' boards from this run)
"""
import json, math, os, sys, time
from collections import deque

import numpy as np
import networkx as nx

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
import B2_ani as BA
import X_build as XB

OUT = os.path.join(ROOT, 'build', 'machinery')
BASE = {'WMC': BA.WMC, 'NR': BA.NR, 'WO': BA.WO}

# composition specs = B2_ani's *_from functions (same instance names, same port -> node maps)
SPEC = {
    'SD': dict(parts={'wmc': ('WMC', {'L': 'X', 'R': 'J', 'T': 'N'}),
                      'nrv': ('NR', {'L': 'J', 'R': 'N'}),
                      'nrh': ('NR', {'L': 'J', 'R': 'W'}),
                      'wo': ('WO', {'L': 'W', 'T': 'N', 'R': 'Y'})},
               sides={'X': 'L', 'Y': 'R'}),
    'SO': dict(parts={'sd1': ('SD', {'X': 'In', 'Y': 'W'}),
                      'wo': ('WO', {'L': 'W', 'T': 'Bn', 'R': 'E'}),
                      'sd2': ('SD', {'X': 'E', 'Y': 'Out'}),
                      'up': ('SD', {'X': 'Bn', 'Y': 'Op'}),
                      'dn': ('SD', {'X': 'Op', 'Y': 'Bn'})},
               sides={'In': 'L', 'Op': 'T', 'Out': 'R'}),
    'MSC': dict(parts={'sd': ('SD', {'X': 'T', 'Y': 'Tw'}),
                       'wmc': ('WMC', {'L': 'L', 'R': 'R', 'T': 'Tw'})},
                sides={'L': 'L', 'T': 'T', 'R': 'R'}),
    'SX': dict(parts={'sd1': ('SD', {'X': 'L', 'Y': 'C'}), 'sd2': ('SD', {'X': 'C', 'Y': 'Rd'}),
                      'sd3': ('SD', {'X': 'Rd', 'Y': 'R'}),
                      'sot': ('SO', {'Op': 'Rd', 'In': 'Tp', 'Out': 'C'}),
                      'sob': ('SO', {'Op': 'Rd', 'In': 'C', 'Out': 'Bt'})},
               sides={'L': 'L', 'Tp': 'T', 'R': 'R', 'Bt': 'B'}),
    'WCX': dict(parts={'mscL': ('MSC', {'L': 'L', 'R': 'm', 'T': 'u'}),
                       'mscM': ('MSC', {'L': 'r', 'R': 'm', 'T': 'v'}),
                       'mscR': ('MSC', {'L': 'R', 'R': 'r', 'T': 'w'}),
                       'sda': ('SD', {'X': 'Bt', 'Y': 'b'}), 'sdb': ('SD', {'X': 'b', 'Y': 'L'}),
                       'sdc': ('SD', {'X': 'L', 'Y': 'u'}),
                       'soB': ('SO', {'Op': 'b', 'In': 'm', 'Out': 'w'}),
                       'soUL': ('SO', {'Op': 'u', 'In': 'm', 'Out': 'v'}),
                       'soUR': ('SO', {'Op': 'v', 'In': 'r', 'Out': 'Tp'})},
                sides={'L': 'L', 'Tp': 'T', 'R': 'R', 'Bt': 'B'}),
    # one Thm 5.3 check unit (Ani Fig. 23) for a check a -> b: SO O_i (opening op, entrance from b) + SD D_i
    # (op -> a) placed together, the hooks SD exit -> a and b -> SO entrance, the hook from b crossing one
    # delimiter-pass chain segment wi -> wo through an SX (chain first = L->R, hook later = Tp->Bt: time order)
    'HK': dict(parts={'sx': ('SX', {'L': 'wi', 'R': 'wo', 'Tp': 'b', 'Bt': 'h'}),
                      'so': ('SO', {'Op': 'op', 'In': 'h', 'Out': 'out'}),
                      'sd': ('SD', {'X': 'op', 'Y': 'a'})},
               sides={'b': ('T', .5), 'wi': ('L', .25), 'wo': ('R', .25), 'op': ('L', .75), 'out': ('R', .75),
                      'a': ('B', .3)}),
}
ORDER = ['SD', 'SO', 'MSC', 'SX', 'WCX', 'HK']
SIDE_DIR = {'L': (-1, 0), 'T': (0, -1), 'R': (1, 0), 'B': (0, 1)}


def side_of(s):
    """'L' or ('L', f): side + position f in (0, 1) along it (x for T/B, y for L/R)"""
    return (s, .5) if isinstance(s, str) else (s[0], s[1])


def side_pos(s):
    sd, f = side_of(s)
    return {'L': (0, f), 'T': (f, 0), 'R': (1, f), 'B': (f, 1)}[sd]


def rim_order(sides):
    """external ports in clockwise order (screen coordinates, y down): top left->right, right top->bottom, ..."""
    def key(e):
        sd, f = side_of(sides[e])
        return ({'T': 0, 'R': 1, 'B': 2, 'L': 3}[sd], f if sd in 'TR' else 1 - f)
    return sorted(sides, key=key)


# ============================================================ tiles
def base_tile(kind):
    rows = BASE[kind]
    H, W = len(rows), max(map(len, rows))
    cells, ports = {}, {}
    for y, r in enumerate(rows):
        for x, ch in enumerate(r.ljust(W, '#')):
            if ch == '#':
                continue
            if ch.isupper():
                d = (-1, 0) if x == 0 else (1, 0) if x == W - 1 else (0, -1) if y == 0 else (0, 1)
                assert x in (0, W - 1) or y in (0, H - 1)
                cells[(x, y)] = '.'
                ports[ch] = ((x, y), d, [(x, y)])
            else:
                cells[(x, y)] = ch
    t = XB.Tile(kind, cells, ports, [], {}, W, H)
    # every bounding-box cell of the canonical board (walls too) -> tile-local cell
    t.parts = [((), kind, {(x, y): (x, y) for y in range(H) for x in range(W)})]
    return t


def flat_net(kind, prefix=(), pm=None):
    """flattened network of a gadget kind: list of (path, base kind, {port: flat node}); external nodes keep the
    outer names given by pm (default: their own names)."""
    if kind in BASE:
        return [(prefix, kind, dict(pm))]
    sp = SPEC[kind]
    pm = pm or {e: e for e in sp['sides']}
    out = []
    for n, (k, ipm) in sp['parts'].items():
        sub = {p: (pm[v] if v in sp['sides'] else '/'.join(prefix + (v,))) for p, v in ipm.items()}
        out += flat_net(k, prefix + (n,), sub)
    return out


class _BD:
    def __init__(self, g):
        self.g = g


# ============================================================ drawing (X_build.drawing with general pins)
def drawing(G, sides, R, seed):
    rng = np.random.RandomState(seed)
    H = G.copy()
    pin = {'N:' + e: side_pos(s) for e, s in sides.items()}
    pin.update({'c:TL': (0, 0), 'c:TR': (1, 0), 'c:BR': (1, 1), 'c:BL': (0, 1)})
    ring = []
    for sd, corner in (('T', 'c:TR'), ('R', 'c:BR'), ('B', 'c:BL'), ('L', 'c:TL')):
        ring += ['N:' + e for e in rim_order(sides) if side_of(sides[e])[0] == sd] + [corner]
    for a, b in zip(ring, ring[1:] + ring[:1]):
        H.add_edge(a, b)
    # Tutte needs 3-connectivity (the interior hangs on the rim at 2 vertices only, e.g. SD): take the planar
    # embedding with a hub outside the ring, put one virtual vertex into every inner face (adjacent to its corners),
    # run Tutte on that, then drop the virtual vertices
    Hh = H.copy()
    for v in ring:
        Hh.add_edge('hub', v)
    okp, emb = nx.check_planarity(Hh)
    assert okp
    faces, seen = [], set()
    for v in emb.nodes():
        for w in emb.neighbors_cw_order(v):
            if (v, w) in seen:
                continue
            f = emb.traverse_face(v, w, mark_half_edges=seen)
            faces.append(f)
    Hv = H.copy()
    for k, f in enumerate(faces):
        if 'hub' in f:
            continue
        for u in dict.fromkeys(f):
            Hv.add_edge(('virt', k), u)
    V = list(H) + [v for v in Hv if v not in H]
    ix = {v: i for i, v in enumerate(V)}
    E = np.array([(ix[a], ix[b]) for a, b in H.edges()])
    P = np.array([pin.get(v, (.3 + rng.rand() * .4, .3 + rng.rand() * .4)) for v in V], dtype=float)
    nbv = [[ix[u] for u in Hv[v]] for v in V]
    freev = [i for i, v in enumerate(V) if v not in pin]
    for _ in range(4000):
        for i in freev:
            P[i] = P[nbv[i]].mean(0)
    V = list(H)
    P = P[:len(V)]
    nb = [[ix[u] for u in H[v]] for v in V]
    free = [i for i, v in enumerate(V) if v not in pin]
    Rv = np.array([R.get(v, .015) for v in V])
    inc = [np.where((E[:, 0] == i) | (E[:, 1] == i))[0] for i in range(len(V))]
    noninc = [[np.where((E[:, 0] != E[e, 0]) & (E[:, 1] != E[e, 0]) & (E[:, 0] != E[e, 1]) & (E[:, 1] != E[e, 1]))[0]
               for e in inc[i]] for i in range(len(V))]

    gnb = [[j for j in nb[i] if V[j] in G] for i in range(len(V))]

    def mingap(Q, i):
        if len(gnb[i]) < 2:
            return 7.0
        an = sorted(math.atan2(Q[j][1] - Q[i][1], Q[j][0] - Q[i][0]) for j in gnb[i])
        return min([b - a for a, b in zip(an, an[1:])] + [an[0] + 2 * math.pi - an[-1]])

    def ok(i, q):
        Q = P.copy()
        Q[i] = q
        for e, oth in zip(inc[i], noninc[i]):
            a, b = E[e]
            if XB._cross(Q[a], Q[b], Q[E[oth, 0]], Q[E[oth, 1]]).any():
                return False
        for k in [i] + gnb[i]:            # keep incident edges at least 10 deg apart (or no worse than before)
            if V[k] in G and mingap(Q, k) < min(math.radians(10), mingap(P, k)):
                return False
        return True

    def planar_now():
        for e in range(len(E)):
            a, b = E[e]
            oth = np.where((E[:, 0] != a) & (E[:, 1] != a) & (E[:, 0] != b) & (E[:, 1] != b))[0]
            if XB._cross(P[a], P[b], P[E[oth, 0]], P[E[oth, 1]]).any():
                return False
        return True
    if not planar_now():
        return None
    step = .02
    for sweep in range(400):
        for i in rng.permutation(free):
            d = P[i] - P
            dist = np.sqrt((d ** 2).sum(1)) + 1e-9
            want = (Rv[i] + Rv) * 1.7
            f = ((np.maximum(want - dist, 0) / dist)[:, None] * d).sum(0)
            for j in nb[i]:
                f -= (P[i] - P[j]) * .05
            n = np.linalg.norm(f)
            if n < 1e-12:
                continue
            q = P[i] + f / n * min(step, n)
            if 0.02 < q[0] < .98 and 0.02 < q[1] < .98 and ok(i, q):
                P[i] = q
        step *= .995
    if not planar_now():
        return None
    gap = 7.0
    for v in G:
        if v in pin or len(G[v]) < 2:
            continue
        an = sorted(math.atan2(P[ix[u]][1] - P[ix[v]][1], P[ix[u]][0] - P[ix[v]][0]) for u in G[v])
        gap = min([gap] + [b - a for a, b in zip(an, an[1:])] + [an[0] + 2 * math.pi - an[-1]])
    if gap < math.radians(3):
        return None
    return {v: (float(P[ix[v]][0]), float(P[ix[v]][1])) for v in G}


# ============================================================ layout of one level
class MLayout(XB.Layout):
    def __init__(self, spec, tiles, pos, scale):
        self.bd = _BD({n: (None, dict(pm)) for n, (k, pm) in spec['parts'].items()})
        self.sides = spec['sides']
        self.tiles, self.node_of, self.nobody = {}, {}, []
        for n, (k, pm) in spec['parts'].items():
            tile = tiles[k]
            nbr = {p: pos['N:' + v] for p, v in pm.items()}
            t = XB.choose_sym(tile, pos[n], nbr, need_body=len(tile.ports) <= 2)
            if t is None:
                t = XB.choose_sym(tile, pos[n], nbr)
                self.nobody.append(n)
            W2, H2 = XB.sym_size(t, tile.W, tile.H)
            self.tiles[n] = dict(kind=k, sym=t, W=W2, H=H2, tile=tile, center=(pos[n][0] * scale, pos[n][1] * scale))
            for p, v in pm.items():
                self.node_of[(n, p)] = v
        self.pos, self.scale, self.margin = pos, scale, 6

    def place(self):
        # X_build.Layout.place up to the external ports (copied: tiles + stubs), then ports on the requested sides
        ext_sides = self.sides
        ok = self._place_tiles()
        if not ok:
            return False
        self.ext = {}
        for e, s in ext_sides.items():
            sd, fr = side_of(s)
            mx = min(max(int(fr * (self.W - 1)) & ~1, 2), self.W - 3)
            my = min(max(int(fr * (self.H - 1)) & ~1, 2), self.H - 3)
            if sd == 'L':
                cells = [(0, my), (1, my), (2, my)]
            elif sd == 'R':
                cells = [(self.W - 1, my), (self.W - 2, my), (self.W - 3, my)]
            elif sd == 'T':
                cells = [(mx, 0), (mx, 1), (mx, 2)]
            else:
                cells = [(mx, self.H - 1), (mx, self.H - 2), (mx, self.H - 3)]
            k = self._oid('N:' + e)
            for (x, y) in cells:
                if self.own[y, x] not in (0, k):
                    return False
                self.own[y, x] = k
                self.ch[y, x] = '.'
            self.ext[e] = cells[0]
            self.terms.setdefault(e, []).append(cells[-1])
        return True

    def _oid(self, name):
        if name not in self.ids:
            self.ids[name] = len(self.names)
            self.names.append(name)
        return self.ids[name]

    def _place_tiles(self):
        for n, T in self.tiles.items():
            cx, cy = T['center']
            T['ox'] = int(round(cx - T['W'] / 2))
            T['oy'] = int(round(cy - T['H'] / 2))
        minx = min(T['ox'] for T in self.tiles.values()) - 12
        miny = min(T['oy'] for T in self.tiles.values()) - 12
        self.shift = (minx, miny)
        for T in self.tiles.values():
            T['ox'] -= minx
            T['oy'] -= miny
            T['ox'] += T['ox'] & 1
            T['oy'] += T['oy'] & 1
        self.W = max(T['ox'] + T['W'] for T in self.tiles.values()) + 12
        self.H = max(T['oy'] + T['H'] for T in self.tiles.values()) + 12
        self.W += 1 - self.W % 2
        self.H += 1 - self.H % 2
        self.own = np.zeros((self.H, self.W), dtype=np.int32)
        self.ch = np.full((self.H, self.W), '#', dtype='<U1')
        self.ids, self.names = {}, [None]
        for n, T in self.tiles.items():
            tile, t = T['tile'], T['sym']
            g = (lambda ox, oy, t, W, H: lambda c: (ox + XB.sym(t, c[0], c[1], W, H)[0],
                                                    oy + XB.sym(t, c[0], c[1], W, H)[1]))(T['ox'], T['oy'], t, tile.W, tile.H)
            T['g'] = g
            k = self._oid('T:' + n)
            T['cells'] = []
            for c, chv in tile.cells.items():
                x, y = g(c)
                if not (0 < x < self.W - 1 and 0 < y < self.H - 1):
                    return False
                blk = self.own[max(y - 1, 0):y + 2, max(x - 1, 0):x + 2]
                if ((blk != 0) & (blk != k)).any():
                    return False
                self.own[y, x] = k
                self.ch[y, x] = chv
                T['cells'].append((x, y))
        self.terms = {}
        for n, T in self.tiles.items():
            tile, t = T['tile'], T['sym']
            T['ports'] = {}
            xs = [c[0] for c in T['cells']]
            ys = [c[1] for c in T['cells']]
            bx0, bx1, by0, by1 = min(xs), max(xs), min(ys), max(ys)
            tcx, tcy = (bx0 + bx1) / 2, (by0 + by1) / 2
            for p, (c, d, zone) in tile.ports.items():
                v = self.node_of[(n, p)]
                k = self._oid('N:' + v)
                x, y = T['g'](c)
                dx, dy = XB.sym_dir(t, d)
                stub = []
                while not ((dx > 0 and x >= bx1 + 2) or (dx < 0 and x <= bx0 - 2) or
                           (dy > 0 and y >= by1 + 2) or (dy < 0 and y <= by0 - 2)):
                    x, y = x + dx, y + dy
                    stub.append((x, y))
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
        return True


def graph_of(spec):
    G = nx.Graph()
    for n, (k, pm) in spec['parts'].items():
        for p, v in pm.items():
            assert not G.has_edge(n, 'N:' + v), (n, p, v)
            G.add_edge(n, 'N:' + v, port=p)
    return G


def planar_with_rim(spec):
    G = graph_of(spec)
    ring = rim_order(spec['sides'])
    Hh = G.copy()
    for e in ring:
        Hh.add_edge('hub', 'N:' + e)
    if len(ring) > 2:
        for a, b in zip(ring, ring[1:] + ring[:1]):
            Hh.add_edge('N:' + a, 'N:' + b)
    res = nx.check_planarity(Hh)[0]
    bad = None
    if len(ring) == 4:      # the non-crossing order must be non-planar (the gadget really crosses)
        r2 = [ring[0], ring[2], ring[1], ring[3]]
        H2 = G.copy()
        for e in r2:
            H2.add_edge('hub', 'N:' + e)
        for a, b in zip(r2, r2[1:] + r2[:1]):
            H2.add_edge('N:' + a, 'N:' + b)
        bad = nx.check_planarity(H2)[0]
    return res, bad


def tile_from_level(kind, rows, ext, sides, parts):
    """the finished board of a level as a Tile for the next level"""
    H, W = len(rows), len(rows[0])
    cells = {(x, y): rows[y][x] for y in range(H) for x in range(W) if rows[y][x] != '#'}
    ports = {e: (tuple(c), SIDE_DIR[side_of(sides[e])[0]], [tuple(c)]) for e, c in ext.items()}
    t = XB.Tile(kind, cells, ports, [], {}, W, H)
    t.parts = parts
    return t


def build_level(kind, tiles, log=print, seeds=range(1, 40)):
    spec = SPEC[kind]
    pl, npl = planar_with_rim(spec)
    log(f'== {kind}: {len(spec["parts"])} parts; wiring + rim planar: {pl}' +
        ('' if npl is None else f'; with the non-crossing port order: planar {npl}'))
    assert pl and not npl
    G = graph_of(spec)
    R = {n: .04 + .004 * max(tiles[k].W, tiles[k].H) / 10 for n, (k, pm) in spec['parts'].items()}
    for seed in seeds:
        pos = drawing(G, spec['sides'], R, seed)
        if pos is None:
            log(f'  seed {seed}: no non-degenerate planar drawing')
            continue
        size = sum(max(tiles[k].W, tiles[k].H) for k, _ in spec['parts'].values())
        scale = int(size * 1.6) + 20
        for attempt in range(14):
            L = MLayout(spec, tiles, pos, scale)
            if L.place() and (L.route_negotiated(iters=60, log=lambda s: None) or L.route(seed, tries=6, log=lambda s: None)):
                rows = [''.join(r) for r in L.ch]
                tl = {n: dict(cells=T['cells'], ports={p: dict(cell=P['cell'], zone=P['zone'])
                                                       for p, P in T['ports'].items()}) for n, T in L.tiles.items()}
                try:
                    XB.check_map(rows, tl, L.ext, L.bd)
                except AssertionError as e:
                    log(f'  seed {seed} scale {scale}: check_map failed {str(e)[:80]}')
                    scale = int(scale * 1.12)
                    continue
                W0, H0 = L.W, L.H
                XB.compact(L)
                crop(L)
                rows = [''.join(r) for r in L.ch]
                tl = {n: dict(cells=T['cells'], ports={p: dict(cell=P['cell'], zone=P['zone'])
                                                       for p, P in T['ports'].items()}) for n, T in L.tiles.items()}
                XB.check_map(rows, tl, L.ext, L.bd)
                log(f'  seed {seed} scale {scale}: {W0} x {H0} -> compacted {L.W} x {L.H}, routed, check_map ok (sub-boards not 8-adjacent, '
                    f'one corridor per node, wiring == {kind} network); symmetries '
                    f'{ {n: T["sym"] for n, T in L.tiles.items()} }')
                return L, rows
            scale = int(scale * 1.12)
        log(f'  seed {seed}: placement/routing failed up to scale {scale}')
    raise RuntimeError(f'{kind}: no layout')


def crop(L):
    """drop all-wall border rows/columns (keep a 1-cell wall frame; external ports stay on the frame)"""
    fl = L.ch != '#'
    ys, xs = np.nonzero(fl)
    x0, x1 = max(int(xs.min()) - 1, 0), min(int(xs.max()) + 1, L.W - 1)
    y0, y1 = max(int(ys.min()) - 1, 0), min(int(ys.max()) + 1, L.H - 1)
    for e, (x, y) in L.ext.items():
        assert x in (x0, x1) or y in (y0, y1), ('external port leaves the frame after crop', e)

    def f(c):
        return (c[0] - x0, c[1] - y0) if x0 <= c[0] <= x1 and y0 <= c[1] <= y1 else None

    def fl_(cs):
        return [f(c) for c in cs if f(c) is not None]
    for n, T in L.tiles.items():
        T['cells'] = fl_(T['cells'])
        g0 = T['g']
        T['g'] = (lambda g0: lambda c: None if g0(c) is None else f(g0(c)))(g0)
        for p, P in T['ports'].items():
            P['cell'] = f(P['cell'])
            P['zone'] = fl_(P['zone'])
            P['stub'] = fl_(P['stub'])
    L.ext = {e: f(c) for e, c in L.ext.items()}
    L.paths = {v: fl_(p) for v, p in L.paths.items()}
    L.ch, L.own = L.ch[y0:y1 + 1, x0:x1 + 1], L.own[y0:y1 + 1, x0:x1 + 1]
    L.H, L.W = L.ch.shape


def compose_parts(L):
    """base-board copies of a finished level: (path, kind, {canonical cell: global cell})"""
    out = []
    for n, T in L.tiles.items():
        for path, k, cm in T['tile'].parts:
            m = {bc: T['g'](tc) for bc, tc in cm.items()}
            out.append(((n,) + tuple(path), k, {bc: gc for bc, gc in m.items() if gc is not None}))
    return out


def save(kind, rows, ext, sides, parts, log=print):
    os.makedirs(OUT, exist_ok=True)
    H, W = len(rows), len(rows[0])
    nb = sum(r.count('0') for r in rows)
    nfloor = sum(len(r) - r.count('#') for r in rows)
    fn = flat_net(kind)
    js = dict(kind=kind, W=W, H=H, boulders=nb, floor=nfloor,
              ext={e: list(c) for e, c in ext.items()}, sides=sides,
              parts=[dict(path='/'.join(p), kind=k, sym_cells=[[bx, by, gx, gy] for (bx, by), (gx, gy) in sorted(cm.items())])
                     for p, k, cm in parts],
              net=[dict(path='/'.join(p), kind=k, ports=pm) for p, k, pm in fn],
              counts={k: sum(1 for _, kk, _ in parts if kk == k) for k in BASE})
    with open(os.path.join(OUT, kind + '.txt'), 'w') as f:
        f.write('\n'.join(rows) + '\n')
    with open(os.path.join(OUT, kind + '.json'), 'w') as f:
        json.dump(js, f)
    log(f'  wrote build/machinery/{kind}.txt/.json: {W} x {H}, {nfloor} floor, {nb} boulders, base boards {js["counts"]}')
    return js


def main():
    want = [a for a in sys.argv[1:] if a in SPEC] or ORDER
    t0 = time.time()
    tiles = {k: base_tile(k) for k in BASE}
    built = {}
    last = max(ORDER.index(w) for w in want)
    for kind in ORDER[:last + 1]:
        L, rows = build_level(kind, tiles)
        parts = compose_parts(L)
        js = save(kind, rows, L.ext, SPEC[kind]['sides'], parts)
        tiles[kind] = tile_from_level(kind, rows, L.ext, SPEC[kind]['sides'], parts)
        built[kind] = js
        print(f'  ({time.time() - t0:.0f}s)')
    return built


if __name__ == '__main__':
    main()
