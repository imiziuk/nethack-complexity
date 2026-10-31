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
ports, check ports, corridors, delimiter-ready check legs). Usage: python X_build.py [--seed N]
Tile version 2 (review 5 repair 1, 2026-10-29): scd_tile()/diode_tile() put every check location on its own LEG-cell
hallway (Wb slot, mid, Wt slot) before its junction, as B2_e2e.gprime; v1 tiles (joined *.ABC / *.CD, unsound checks)
are kept as scd_tile_v1()/diode_tile_v1(); the v1 map is saved as build/xover/crossover_v1.*.
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
    # de-degeneration (2026-10-30, review 5 repair 1 rebuild). Tutte on this non-3-connected graph can leave two
    # edges at a gadget collinear (overlapping), so the rotation there is undefined and choose_sym may pick a port order
    # that contradicts the embedding (corridors then cannot be routed). Nudge one endpoint of the tightest pair,
    # accepting a move only if it creates no crossing (ok) and raises the minimum incident-edge angle at every gadget
    # it touches; the result is a genuinely planar drawing whose rotation system is well defined.
    gad = [i for i, v in enumerate(V) if v in G and v not in pin]     # gadgets AND junction nodes
    gnb = [[j for j in nb[i] if V[j] in G] for i in range(len(V))]

    def mingap(i):
        if len(gnb[i]) < 2:
            return 7.0
        an = sorted(math.atan2(P[j][1] - P[i][1], P[j][0] - P[i][0]) for j in gnb[i])
        return min([b - a for a, b in zip(an, an[1:])] + [an[0] + 2 * math.pi - an[-1]])
    thr = math.radians(4)
    fixed = set(i for i, v in enumerate(V) if v in pin)
    for rnd in range(6000):
        worst = min(gad, key=mingap)
        if mingap(worst) >= thr:
            break
        an = sorted((math.atan2(P[j][1] - P[worst][1], P[j][0] - P[worst][0]), j) for j in gnb[worst])
        pairs = list(zip(an, an[1:])) + [(an[-1], (an[0][0] + 2 * math.pi, an[0][1]))]
        (_, j1), (_, j2) = min(pairs, key=lambda pq: pq[1][0] - pq[0][0])
        moved = False
        for j in (j1, j2):
            if j in fixed:
                continue
            aff = [worst] + [k for k in gnb[j] if k != worst]
            before = min(mingap(k) for k in aff)
            for mag in (.002, .005, .01, .02, .04):
                for _ in range(12):
                    ang = rng.rand() * 2 * math.pi
                    q = P[j] + mag * np.array([math.cos(ang), math.sin(ang)])
                    if not (0 < q[0] < 1 and 0 < q[1] < 1) or not ok(j, q):
                        continue
                    old = P[j].copy()
                    P[j] = q
                    if min(mingap(k) for k in aff) > before + 1e-9:
                        moved = True
                        break
                    P[j] = old
                if moved:
                    break
            if moved:
                break
        if not moved:
            break
    # clearance pass: no drawing edge may pass through the body of a gadget it does not touch (vertex-edge distance
    # >= R of the gadget). Otherwise the placed tile covers that edge and its corridor must go round the tile on a
    # side the drawing does not fix (found 2026-10-30: junction N28 -> g038 passed 4 deg off g034's centre, which made
    # N28 and x15 unroutable at every scale). Moves keep planarity (ok) and the 4-degree angle bound.
    GE = np.array([(ix[a], ix[b]) for a, b in G.edges()])
    gv = [i for i, v in enumerate(V) if v in G and not v.startswith('N:')]
    Rg = np.array([R[i] for i in gv])

    def viol(Pm):
        A, B = Pm[GE[:, 0]], Pm[GE[:, 1]]
        out = np.zeros(len(gv))
        for k, i in enumerate(gv):
            d = B - A
            t = np.clip(((Pm[i] - A) * d).sum(1) / np.maximum((d * d).sum(1), 1e-12), 0, 1)
            dist = np.sqrt(((A + t[:, None] * d - Pm[i]) ** 2).sum(1))
            incm = (GE[:, 0] == i) | (GE[:, 1] == i)
            out[k] = np.maximum(Rg[k] - dist[~incm], 0).sum()
        return out
    vv = viol(P)
    for rnd in range(4000):
        if vv.max() <= 0:
            break
        k = int(vv.argmax())
        i = gv[k]
        cand = [i] + [int(j) for j in GE[(GE[:, 0] == i) | (GE[:, 1] == i)].ravel() if j != i]
        # also the endpoints of the offending edges
        A, B = P[GE[:, 0]], P[GE[:, 1]]
        d = B - A
        t = np.clip(((P[i] - A) * d).sum(1) / np.maximum((d * d).sum(1), 1e-12), 0, 1)
        dist = np.sqrt(((A + t[:, None] * d - P[i]) ** 2).sum(1))
        incm = (GE[:, 0] == i) | (GE[:, 1] == i)
        offend = np.where(~incm & (dist < R[i]))[0]
        cand += [int(j) for e in offend for j in GE[e]]
        tot0 = vv.sum()
        moved = False
        for j in dict.fromkeys(cand):
            if j in fixed:
                continue
            for mag in (.005, .01, .02, .04):
                for _ in range(8):
                    ang = rng.rand() * 2 * math.pi
                    q = P[j] + mag * np.array([math.cos(ang), math.sin(ang)])
                    if not (0 < q[0] < 1 and 0 < q[1] < 1) or not ok(j, q):
                        continue
                    old = P[j].copy()
                    P[j] = q
                    aff = [j] + [u for u in gnb[j]]
                    if min(mingap(u) for u in aff if u in gad or u == j) >= thr:
                        v2 = viol(P)
                        if v2.sum() < tot0 - 1e-9:
                            vv = v2
                            moved = True
                            break
                    P[j] = old
                if moved:
                    break
            if moved:
                break
        if not moved:
            break
    print(f'  drawing: clearance pass {rnd} rounds, remaining vertex-edge violation {vv.sum():.4f}')
    # final planarity of the straight-line drawing (all edges incl. frame)
    for e in range(len(E)):
        a, b = E[e]
        oth = np.where((E[:, 0] != a) & (E[:, 1] != a) & (E[:, 0] != b) & (E[:, 1] != b))[0]
        assert not _cross(P[a], P[b], P[E[oth, 0]], P[E[oth, 1]]).any(), 'drawing not planar'
    # non-degeneracy: the incident edges of every gadget leave in pairwise distinct directions (rotation defined)
    gap = 7.0
    for v in G:
        if v in pin or len(G[v]) < 2:
            continue
        an = sorted(math.atan2(P[ix[u]][1] - P[ix[v]][1], P[ix[u]][0] - P[ix[v]][0]) for u in G[v])
        gap = min([gap] + [b - a for a, b in zip(an, an[1:])] + [an[0] + 2 * math.pi - an[-1]])
    print(f'  drawing: min angle between incident edges at a gadget or junction {math.degrees(gap):.1f} deg')
    assert gap > math.radians(1), 'degenerate drawing'
    return {v: (float(P[ix[v]][0]), float(P[ix[v]][1])) for v in G}


# ============================================================ 3. tiles
class Tile:
    """local tile: cells {(x,y): ch} (only floor-ish chars: '.', '0'), ports {name: (cell, dir, zone)},
    comps [(name, kind 'pp'|'pd', (ox, oy))], checks {name: [cells]}.
    v2 tiles also carry legs {name: {gside, cells, Wb, mid, Wt, node}} (one delimiter-ready hallway per check
    location, B2 §3.2 / B2_e2e `gprime`) and nodes {node: [(comp, port letter) or ('tile', port)]} (intended joins)."""
    def __init__(self, kind, cells, ports, comps, checks, W, H, legs=None, nodes=None):
        self.kind, self.cells, self.ports, self.comps, self.checks, self.W, self.H = kind, cells, ports, comps, checks, W, H
        self.legs, self.nodes = legs or {}, nodes or {}


# ---------------- v2 tiles (review 5 repair 1): every check location on its own delimited leg
LEG = 3          # leg cells from the g-side outward: Wb slot, mid, Wt slot; the next cell is the outer junction


class _TB:
    """tile builder: components from S2's boards, legs, junction cells, tile ports; owner map for the checks."""
    def __init__(self):
        self.cells, self.owner, self.cport = {}, {}, {}
        self.comps, self.legs, self.nodes, self.ports = [], {}, {}, {}

    def _put(self, c, ch, own):
        assert c not in self.owner, ('tile overlap', c, own, self.owner.get(c))
        self.cells[c] = ch
        self.owner[c] = own

    def comp(self, name, kind, ox, oy, track=None):
        rows = S2.PROTO_PRECURSOR if kind == 'pp' else S2.PROTODIODE
        for y, r in enumerate(rows):
            for x, ch in enumerate(r):
                if ch == '#':
                    continue
                c = (ox + x, oy + y)
                if ch.isupper():
                    self._put(c, '.', ('port', name, ch))
                    self.cport[(name, ch)] = c
                else:
                    self._put(c, '0' if (ch == '0' and track is None) or (track is not None and y == 2 and x in track)
                              else '.', ('comp', name))
        self.comps.append((name, kind, (ox, oy)))

    def leg(self, name, gside, d, node):
        cs = [(gside[0] + d[0] * k, gside[1] + d[1] * k) for k in range(1, LEG + 1)]
        for c in cs:
            self._put(c, '.', ('leg', name))
        self.legs[name] = dict(gside=gside, cells=cs, Wb=cs[0], mid=cs[1:-1], Wt=cs[-1], node=node)
        return (cs[-1][0] + d[0], cs[-1][1] + d[1])           # first cell beyond the leg (outer junction)

    def sleg(self, name, port, d, node, sv=0, shift=0, turn=1):
        """leg with a g-side stub (review 6 scaling): from the port, `turn` cells along d, |shift| cells sideways,
        then along d again until the path has advanced sv cells along d; the last stub cell is the g-side (the check
        location, L_gen) and the leg's Wb is the next cell. sv = shift = 0: the plain leg (g-side = port cell).
        The stub cells lie outside every raw gadget window; they are the port's location region (L_gen role GXR)."""
        x, y = port
        path = []
        side = ((1 if shift > 0 else -1), 0) if d[0] == 0 else (0, (1 if shift > 0 else -1))
        if shift:
            assert 1 <= turn <= sv, ('stub turn', name, sv, turn)
        for k in range(turn if shift else sv):
            x, y = x + d[0], y + d[1]
            path.append((x, y))
        for k in range(abs(shift)):
            x, y = x + side[0], y + side[1]
            path.append((x, y))
        for k in range(sv - turn if shift else 0):
            x, y = x + d[0], y + d[1]
            path.append((x, y))
        for c in path:
            self._put(c, '.', ('gstub', name))
        gside = path[-1] if path else port
        nxt = self.leg(name, gside, d, node)
        self.legs[name]['port'] = port
        self.legs[name]['stub'] = path[:-1]
        return nxt

    def junction(self, node, cells, members):
        for c in cells:
            self._put(c, '.', ('node', node))
        self.nodes[node] = members

    def tport(self, p, c, d, leg=None, approach=()):
        """tile port: optional approach hallway (cells after the leg), then port cell c, stub direction d;
        zone = port cell + approach + the tile-level leg cells (the stub may run beside them)"""
        for a in approach:
            self._put(a, '.', ('tport', p))
        self._put(c, '.', ('tport', p))
        self.ports[p] = (c, d, [c] + list(approach) + (list(self.legs[leg]['cells']) if leg else []))

    def finish(self):
        """shift everything so that the smallest coordinates are 0; returns (W, H)"""
        mx, my = min(x for x, _ in self.cells), min(y for _, y in self.cells)
        f = lambda c: (c[0] - mx, c[1] - my)
        self.cells = {f(c): v for c, v in self.cells.items()}
        self.owner = {f(c): v for c, v in self.owner.items()}
        self.cport = {k: f(c) for k, c in self.cport.items()}
        self.comps = [(n, k, f(o)) for n, k, o in self.comps]
        self.legs = {l: dict(gside=f(Lg['gside']), cells=[f(c) for c in Lg['cells']], Wb=f(Lg['Wb']),
                             mid=[f(c) for c in Lg['mid']], Wt=f(Lg['Wt']), node=Lg['node'],
                             port=f(Lg.get('port', Lg['gside'])), stub=[f(c) for c in Lg.get('stub', [])])
                     for l, Lg in self.legs.items()}
        self.ports = {p: (f(c), d, [f(z) for z in zone]) for p, (c, d, zone) in self.ports.items()}
        return max(x for x, _ in self.cells) + 1, max(y for _, y in self.cells) + 1

    def size(self):
        return self.finish()


def tile_regions(cells, owner, cut=(), corner_floor=None):
    """hero-connectivity regions of a tile with component interiors removed and the `cut` cells walled (closed
    delimiters). 4-moves, plus diagonal moves whenever some corner cell is floor (over-approximation: boulders and the
    Sokoban corner rule ignored, so a separation found here is real). Returns {cell: region id} for non-interior cells."""
    cut = set(cut)
    corner_floor = corner_floor or (lambda c: c in cells)
    free = {c for c in cells if owner[c][0] != 'comp' and c not in cut}
    reg, k = {}, 0
    for c0 in sorted(free):
        if c0 in reg:
            continue
        reg[c0] = k
        dq = deque([c0])
        while dq:
            x, y = dq.popleft()
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    t = (x + dx, y + dy)
                    if (dx or dy) and t in free and t not in reg and \
                            (not (dx and dy) or corner_floor((x + dx, y)) or corner_floor((x, y + dy))):
                        reg[t] = k
                        dq.append(t)
        k += 1
    return reg


def comp_owner(cells, comps):
    """owner map for ANY tile (v1 or v2, local or placed): comps = [(name, kind, {(lx, ly): cell})]; component
    port cells -> ('port', name, letter), other component cells -> ('comp', name), the rest -> ('corr',)."""
    owner, cport = {c: ('corr',) for c in cells}, {}
    for name, kind, cm in comps:
        rows = S2.PROTO_PRECURSOR if kind == 'pp' else S2.PROTODIODE
        for (lx, ly), c in cm.items():
            c = tuple(c)
            ch = rows[ly][lx]
            if ch.isupper():
                owner[c] = ('port', name, ch)
                cport[(name, ch)] = c
            else:
                owner[c] = ('comp', name)
    return owner, cport


def local_comps(tile):
    out = []
    for name, kind, (ox, oy) in tile.comps:
        rows = S2.PROTO_PRECURSOR if kind == 'pp' else S2.PROTODIODE
        out.append((name, kind, {(lx, ly): (ox + lx, oy + ly) for ly, r in enumerate(rows)
                                 for lx, ch in enumerate(r) if ch != '#'}))
    return out


def check_regions(cells, owner, cport, cut=()):
    """{(comp, letter): region name} of every component port with `cut` cells walled (used by review5_abc/cd)."""
    reg = tile_regions(cells, owner, cut)
    return {k: f'r{reg[c]}' for k, c in cport.items()}


def check_tile_legs(t,cells=None, owner=None, cport=None, legs=None, tports=None, corner_floor=None):
    """assert the v2 tile contract (also used by X_verify on every placed copy, in global coordinates):
    (i) no cuts: hero regions of component ports / tile ports == the intended nodes (dead pockets alone);
    (ii) component-level Wb (and, separately, Wt) cells cut: every component port alone in its region;
    (iii) tile-level legs' Wb (and Wt) cut: every tile port separated from every component port.
    Returns {(comp, letter): region-name under (ii)} (distinct names = split check legs)."""
    cells = cells if cells is not None else t.cells
    owner = owner if owner is not None else t.owner
    cport = cport if cport is not None else t.cport
    legs = legs if legs is not None else t.legs
    tports = tports if tports is not None else {p: c for p, (c, _, _) in t.ports.items()}
    pts = dict(cport)
    pts.update({('tile', p): c for p, c in tports.items()})
    reg = tile_regions(cells, owner, (), corner_floor)
    groups = {}
    for k, c in pts.items():
        groups.setdefault(reg[c], set()).add(k)
    want = [set(map(tuple, m)) for m in t.nodes.values()]
    got = list(groups.values())
    for g in got:
        assert len(g) == 1 or g in want, ('unintended join', g)
    for w in want:
        assert w in got, ('intended node not connected', w)
    comp_legs = [l for l in legs if not l.startswith('tile.')]
    tile_legs = [l for l in legs if l.startswith('tile.')]
    out = {}
    for slot in ('Wb', 'Wt'):
        reg = tile_regions(cells, owner, [tuple(legs[l][slot]) for l in comp_legs], corner_floor)
        seen = {}
        for k, c in cport.items():
            assert reg[c] not in seen, ('two component ports share a check region', k, seen.get(reg[c]), slot)
            seen[reg[c]] = k
        if slot == 'Wb':
            out = {k: f'{k[0]}.{k[1]}' for k in cport}
        if tile_legs:
            reg = tile_regions(cells, owner, [tuple(legs[l][slot]) for l in tile_legs], corner_floor)
            for p, c in tports.items():
                assert all(reg[c] != reg[c2] for c2 in cport.values()), ('tile port not delimited', p, slot)
    # every leg is a simple straight hallway: consecutive cells 4-adjacent, gside 4-adjacent to cells[0]
    for l, Lg in legs.items():
        seq = [tuple(Lg['gside'])] + [tuple(c) for c in Lg['cells']]
        assert all(abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1 for a, b in zip(seq, seq[1:])), ('leg not a hallway', l)
    return out


SCD_VARIANTS = (0, 1, 2)


def scd_tile_r5(variant=0):
    """v2 SCD tile (Fig. 37: 1-toggle + precursor + 2 protodiodes, 6 boulders, closed). Unlike v1 every L' location of
    every component (pp: A, B, C, E, F; pd: A, B, C, D) and the SCD's own O, I, J get their own LEG-cell hallway with a
    Wb and a Wt slot before the junction (tT, T, X, Y, cd1, cd2, gsO, gsI, gsJ), exactly the e_l edges of B2_e2e.gprime:
    gside -- WCX_b -- mid -- WCX_t -- outer. Hidden locations D, G stay 1-cell pockets.
    All three tile ports leave from the LEFT side; variant k fixes their top-to-bottom order: 0 = O, I, J;
    1 = I, J, O (O's approach wraps round the top, right and bottom); 2 = J, O, I (J's approach wraps round the right
    and the top). The tile body lies in the sector between the first and last port; Layout picks the variant whose
    body sector is the drawing's widest sector at that gadget (otherwise the body covers foreign edges)."""
    L = LEG
    b = _TB()
    tx, ty = max(1, L - 2), L + 1
    b.comp('tog', 'pp', tx, ty, track=(4, 6))                     # 1-toggle in state r
    px0, py0 = tx + 5, ty + 6 + 2 * L
    b.comp('prec', 'pp', px0, py0, track=(3, 5))                  # precursor state 2 = SCD closed
    dy0 = py0 + 6 + 2 * L
    b.comp('d1', 'pd', px0, dy0)
    b.comp('d2', 'pd', px0 + 5, dy0)
    U, D, Lf, R = (0, -1), (0, 1), (-1, 0), (1, 0)
    cp = b.cport
    # toggle's closed A/B/C junction tT
    for P in 'ABC':
        b.leg(f'tog.{P}', cp[('tog', P)], U, 'tT')
    b.junction('tT', [(x, ty - L - 1) for x in range(tx + 2, tx + 8)], [('tog', P) for P in 'ABC'])
    # tog.E -> gsO -> tile leg -> port O
    gsO = b.leg('tog.E', cp[('tog', 'E')], D, 'gsO')
    b.junction('gsO', [gsO], [('tog', 'E'), ('tile', 'O')])
    o_port = b.leg('tile.O', gsO, Lf, 'O')   # port placed below, after the J approach (variant 1 wraps it)
    # T = tog.F + prec.A/B/C
    t = b.leg('tog.F', cp[('tog', 'F')], D, 'T')
    for P in 'ABC':
        b.leg(f'prec.{P}', cp[('prec', P)], U, 'T')
    b.junction('T', [(x, t[1]) for x in range(t[0], px0 + 8)], [('tog', 'F')] + [('prec', P) for P in 'ABC'])
    # X = prec.E + d1.B ; Y = prec.F + d2.A
    for nd, (c1, p1), (c2, p2) in (('X', ('prec', 'E'), ('d1', 'B')), ('Y', ('prec', 'F'), ('d2', 'A'))):
        j = b.leg(f'{c1}.{p1}', cp[(c1, p1)], D, nd)
        j2 = b.leg(f'{c2}.{p2}', cp[(c2, p2)], U, nd)
        assert j == j2
        b.junction(nd, [j], [(c1, p1), (c2, p2)])
    # I = d1.A -> gsI -> tile leg -> port I ; J = d2.B -> gsJ -> tile leg -> port J
    gsI = b.leg('d1.A', cp[('d1', 'A')], U, 'gsI')
    b.junction('gsI', [gsI], [('d1', 'A'), ('tile', 'I')])
    b.tport('I', b.leg('tile.I', gsI, Lf, 'I'), Lf, 'tile.I')
    gsJ = b.leg('d2.B', cp[('d2', 'B')], U, 'gsJ')
    b.junction('gsJ', [gsJ], [('d2', 'B'), ('tile', 'J')])
    jx, jy = b.leg('tile.J', gsJ, R, 'J')     # first cell beyond the leg
    ybot = dy0 + 3 + L + 2
    ytop = ty - L - 3                         # free row above the tT junction
    if variant in (0, 1):                     # J: down the right side, left along the bottom, port bottom-left
        appr = [(jx, y) for y in range(jy, ybot + 1)] + [(x, ybot) for x in range(jx - 1, 0, -1)]
        b.tport('J', (0, ybot), Lf, 'tile.J', appr)
    else:                                     # J: up the right side, left along the top, down to just above O
        appr = ([(jx, y) for y in range(jy, ytop - 1, -1)] + [(x, ytop) for x in range(jx - 1, -1, -1)] +
                [(0, y) for y in range(ytop + 1, o_port[1] - 4)])
        b.tport('J', (0, o_port[1] - 4), Lf, 'tile.J', appr)
    if variant == 1:                          # O: up, right along the top, down the far right, left along the bottom
        xr, yb = jx + 2, ybot + 4
        appr = ([(0, y) for y in range(o_port[1], ytop - 1, -1)] + [(x, ytop) for x in range(1, xr + 1)] +
                [(xr, y) for y in range(ytop + 1, yb + 1)] + [(x, yb) for x in range(xr - 1, 0, -1)])
        b.tport('O', (0, yb), Lf, 'tile.O', appr)
    else:
        b.tport('O', o_port, Lf, 'tile.O')
    # cd1, cd2: diode C, D legs
    for dn in ('d1', 'd2'):
        jc = b.leg(f'{dn}.C', cp[(dn, 'C')], D, f'{dn}cd')
        jd = b.leg(f'{dn}.D', cp[(dn, 'D')], D, f'{dn}cd')
        b.junction(f'{dn}cd', [(x, jc[1]) for x in range(jc[0], jd[0] + 1)], [(dn, 'C'), (dn, 'D')])
    W, H = b.finish()
    cp = b.cport
    checks = {f'{n}.{P}': [c] for (n, P), c in cp.items()}       # check location = the leg's g-side (port cell)
    checks.update({f'scd.{p}': [b.legs[f'tile.{p}']['gside']] for p in 'OIJ'})
    T = Tile('scd', b.cells, b.ports, b.comps, checks, W, H, b.legs, b.nodes)
    T.owner, T.cport = b.owner, b.cport
    T.variant = variant
    check_tile_legs(T)
    return T


# review 6 scaling of the SCD tile (2026-10-31): the r5 tile could not be routed under the F1/F2 rules (both chains,
# Ani's check walks and their wires do not fit through the 1-cell gaps between adjacent legs). SCD_SV extra g-side
# stub cells on every component leg, and the legs of adjacent ports 1 cell apart (pp A|B, pd A|B, pd C|D) spread
# to SCD_SP columns apart; raw gadget windows, the node structure and the leg contract are unchanged.
SCD_SV = int(os.environ.get('XB_SCD_SV', '3'))
SCD_SP = int(os.environ.get('XB_SCD_SP', '6'))


def scd_tile(variant=0, sv=None, sp=None):
    """v2 SCD tile, review-6 scaled (see scd_tile_r5 for the structure: Fig. 37 1-toggle + precursor + 2 protodiodes,
    every L' location on its own LEG-cell hallway, tile ports O, I, J on the left in variant order).
    sv = g-side stub length of every component leg (the g-side = L_gen check location is the stub's last cell);
    sp = column distance of the spread legs (toggle/precursor A from B, d1.A from d1.B, d2.B from d2.A,
    d1.C from d1.D, d2.D from d2.C). sv = 0, sp = 2 is exactly scd_tile_r5."""
    sv = SCD_SV if sv is None else sv
    sp = SCD_SP if sp is None else sp
    assert sp >= 2 and (sv >= 1 or sp == 2)
    L = LEG
    b = _TB()
    U, D, Lf, R = (0, -1), (0, 1), (-1, 0), (1, 0)
    tx = max(1, L - 2)
    ty = sv + L + 1
    b.comp('tog', 'pp', tx, ty, track=(4, 6))                     # 1-toggle in state r
    yT = ty + 4 + sv + L + 1                                      # T / gsO junction row
    px0, py0 = tx + max(5, sp + 2), yT + 1 + L + sv       # prec A' (B - sp) stays right of tog.F
    b.comp('prec', 'pp', px0, py0, track=(3, 5))                  # precursor state 2 = SCD closed
    yN = py0 + 4 + sv + L + 1                                     # X / Y / gsI / gsJ junction row
    dy0 = yN + 1 + L + sv
    b.comp('d1', 'pd', px0, dy0)
    b.comp('d2', 'pd', px0 + 5, dy0)
    cp = b.cport
    # toggle's closed A/B/C junction tT (A spread left of B)
    sh = {'A': -(sp - 2), 'B': 0, 'C': 0}
    for P in 'ABC':
        b.sleg(f'tog.{P}', cp[('tog', P)], U, 'tT', sv, sh[P])
    b.junction('tT', [(x, ty - sv - L - 1) for x in range(tx + 4 - sp, tx + 8)], [('tog', P) for P in 'ABC'])
    # tog.E -> gsO -> tile leg -> port O
    gsO = b.sleg('tog.E', cp[('tog', 'E')], D, 'gsO', sv)
    b.junction('gsO', [gsO], [('tog', 'E'), ('tile', 'O')])
    o_port = b.leg('tile.O', gsO, Lf, 'O')
    xL = o_port[0] - max(0, sp - 3)                               # left edge column of the approaches (2 left of tog A')
    # T = tog.F + prec.A/B/C
    t = b.sleg('tog.F', cp[('tog', 'F')], D, 'T', sv)
    for P in 'ABC':
        b.sleg(f'prec.{P}', cp[('prec', P)], U, 'T', sv, sh[P])
    assert t[1] == yT
    b.junction('T', [(x, yT) for x in range(t[0], px0 + 8)], [('tog', 'F')] + [('prec', P) for P in 'ABC'])
    # X = prec.E + d1.B ; Y = prec.F + d2.A (aligned columns, single node cell)
    for nd, (c1, p1), (c2, p2) in (('X', ('prec', 'E'), ('d1', 'B')), ('Y', ('prec', 'F'), ('d2', 'A'))):
        j = b.sleg(f'{c1}.{p1}', cp[(c1, p1)], D, nd, sv)
        j2 = b.sleg(f'{c2}.{p2}', cp[(c2, p2)], U, nd, sv)
        assert j == j2 and j[1] == yN, (nd, j, j2)
        b.junction(nd, [j], [(c1, p1), (c2, p2)])
    # I = d1.A (spread left) -> gsI -> tile leg -> port I ; J = d2.B (spread right) -> gsJ -> tile leg -> port J
    gsI = b.sleg('d1.A', cp[('d1', 'A')], U, 'gsI', sv, -(sp - 2))
    b.junction('gsI', [gsI], [('d1', 'A'), ('tile', 'I')])
    b.tport('I', b.leg('tile.I', gsI, Lf, 'I'), Lf, 'tile.I')
    gsJ = b.sleg('d2.B', cp[('d2', 'B')], U, 'gsJ', sv, sp - 2)
    b.junction('gsJ', [gsJ], [('d2', 'B'), ('tile', 'J')])
    jx, jy = b.leg('tile.J', gsJ, R, 'J')     # first cell beyond the leg
    ycd = dy0 + 2 + sv + L + 1                # diode C/D junction row
    ybot = ycd + 2
    ytop = ty - sv - L - 3                    # free row above the tT junction
    if variant in (0, 1):                     # J: down the right side, left along the bottom, port bottom-left
        appr = [(jx, y) for y in range(jy, ybot + 1)] + [(x, ybot) for x in range(jx - 1, xL, -1)]
        b.tport('J', (xL, ybot), Lf, 'tile.J', appr)
    else:                                     # J: up the right side, left along the top, down to just above O
        appr = ([(jx, y) for y in range(jy, ytop - 1, -1)] + [(x, ytop) for x in range(jx - 1, xL - 1, -1)] +
                [(xL, y) for y in range(ytop + 1, o_port[1] - 4)])
        b.tport('J', (xL, o_port[1] - 4), Lf, 'tile.J', appr)
    if variant == 1:                          # O: up, right along the top, down the far right, left along the bottom
        xr, yb = jx + 2, ybot + 4
        appr = ([(x, o_port[1]) for x in range(o_port[0], xL - 1, -1)] +
                [(xL, y) for y in range(o_port[1] - 1, ytop - 1, -1)] + [(x, ytop) for x in range(xL + 1, xr + 1)] +
                [(xr, y) for y in range(ytop + 1, yb + 1)] + [(x, yb) for x in range(xr - 1, xL, -1)])
        b.tport('O', (xL, yb), Lf, 'tile.O', appr)
    else:
        b.tport('O', o_port, Lf, 'tile.O')
    # cd1, cd2: diode C, D legs (d1.C spread left of d1.D, d2.D spread right of d2.C)
    for dn, shc, shd in (('d1', -(sp - 2), 0), ('d2', 0, sp - 2)):
        jc = b.sleg(f'{dn}.C', cp[(dn, 'C')], D, f'{dn}cd', sv, shc)
        jd = b.sleg(f'{dn}.D', cp[(dn, 'D')], D, f'{dn}cd', sv, shd)
        assert jc[1] == jd[1] == ycd
        b.junction(f'{dn}cd', [(x, jc[1]) for x in range(jc[0], jd[0] + 1)], [(dn, 'C'), (dn, 'D')])
    W, H = b.finish()
    cp = b.cport
    checks = {f'{n}.{P}': [c] for (n, P), c in cp.items()}       # check location = the port cell (X_verify regions)
    checks.update({f'scd.{p}': [b.legs[f'tile.{p}']['gside']] for p in 'OIJ'})
    T = Tile('scd', b.cells, b.ports, b.comps, checks, W, H, b.legs, b.nodes)
    T.owner, T.cport = b.owner, b.cport
    T.variant = variant
    T.scale = (sv, sp)
    check_tile_legs(T)
    check_tile_spacing(T)
    return T


def check_tile_spacing(T):
    """no unintended 8-adjacency: two floor cells that touch diagonally share a floor 4-neighbour (so a diagonal
    step adds no connection the 4-moves lack) unless both are inside one raw gadget window (Ani's boards)."""
    comp = {c for c, o in T.owner.items() if o[0] in ('comp', 'port')}
    for (x, y) in T.cells:
        for dx in (-1, 1):
            c2 = (x + dx, y + 1)
            if c2 in T.cells and ((x, y) not in comp or c2 not in comp):
                assert (x + dx, y) in T.cells or (x, y + 1) in T.cells, ('diagonal touch', (x, y), c2)


def diode_tile():
    """v2 network diode tile: Ani protodiode (1 boulder) with A, B (tile ports, up) and C, D (down, joined) each on
    its own LEG-cell delimited hallway (v1 joined C and D directly under the gadget)."""
    L = LEG
    b = _TB()
    b.comp('d', 'pd', 0, L + 1)
    cp = b.cport
    for P in 'AB':
        b.tport(P, b.leg(f'd.{P}', cp[('d', P)], (0, -1), P), (0, -1))
        b.nodes[P] = [('d', P), ('tile', P)]
    jc = b.leg('d.C', cp[('d', 'C')], (0, 1), 'cd')
    jd = b.leg('d.D', cp[('d', 'D')], (0, 1), 'cd')
    b.junction('cd', [(x, jc[1]) for x in range(jc[0], jd[0] + 1)], [('d', 'C'), ('d', 'D')])
    W, H = b.size()
    cp = b.cport                     # re-read after finish() shifted the coordinates (was stale: checks off by one)
    checks = {f'd.{P}': [c] for (n, P), c in cp.items()}
    T = Tile('dio', b.cells, b.ports, b.comps, checks, W, H, b.legs, b.nodes)
    T.owner, T.cport = b.owner, b.cport
    check_tile_legs(T)
    return T


# ---------------- v1 tiles (crossover_v1.*): joined check hallways *.ABC / *.CD -- UNSOUND checks (review 5 §3a)
def scd_tile_v1():
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


def diode_tile_v1():
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


def _sectors(order, ang):
    """clockwise (increasing-angle) sectors (a, b, width) between cyclically consecutive ports"""
    out = []
    for i, a in enumerate(order):
        b = order[(i + 1) % len(order)]
        out.append((a, b, (ang[b] - ang[a]) % (2 * math.pi)))
    return out


def choose_sym(tile, vpos, nbr, need_body=False):
    """nbr: {port: (x, y) of the neighbour node in the drawing}. Pick the symmetry whose port directions have the
    drawing's cyclic order (rotation system) and the smallest angular error. need_body: also require that the tile
    body (opposite the mean port direction) lies in the drawing's widest sector; returns None if impossible."""
    best = None
    ang_n = {p: math.atan2(nbr[p][1] - vpos[1], nbr[p][0] - vpos[0]) for p in tile.ports}
    order_n = sorted(tile.ports, key=lambda p: ang_n[p])
    wide = max(_sectors(order_n, ang_n), key=lambda s: s[2])[:2]
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
        if need_body:
            mx = sum(math.cos(a) for a in ang_p.values())
            my = sum(math.sin(a) for a in ang_p.values())
            body = math.atan2(-my, -mx)
            sec = [(a, b) for a, b, w in _sectors(order_p, ang_p) if (body - ang_p[a]) % (2 * math.pi) < w]
            if sec != [wide]:
                continue
        err = sum(abs((ang_p[p] - ang_n[p] + math.pi) % (2 * math.pi) - math.pi) for p in tile.ports)
        if best is None or err < best[0]:
            best = (err, t)
    return None if best is None else best[1]


# ============================================================ 4. placement + routing
class Layout:
    def __init__(self, bd, pos, scale, margin=6):
        self.bd = bd
        dio = diode_tile()
        scds = [scd_tile(k) for k in SCD_VARIANTS]
        self.tiles = {}
        self.node_of = {}           # (gadget, port) -> node
        self.nobody = []
        xs, ys = [], []
        for n, (s, pm) in bd.g.items():
            nbr = {p: pos['N:' + v] for p, v in pm.items()}
            if 'O' in pm:
                cand = [(tl, choose_sym(tl, pos[n], nbr, need_body=True)) for tl in scds]
                cand = [(tl, t) for tl, t in cand if t is not None]
                if not cand:                    # no variant puts the body in the widest sector: best effort
                    self.nobody.append(n)
                    cand = [(scds[0], choose_sym(scds[0], pos[n], nbr))]
                tile, t = cand[0]
            else:                               # diode: its body must also sit in its wider sector
                tile = dio
                t = choose_sym(tile, pos[n], nbr, need_body=True)
                if t is None:
                    self.nobody.append(n)
                    t = choose_sym(tile, pos[n], nbr)
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
        self.shift = (minx, miny)
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
        # tube widths (cells) around the straight-line drawing edges node -> terminal: keeping every net inside its
        # own tube fixes the homotopy class of each corridor to the planar drawing's (greedy shortest paths may go
        # round a tile on the wrong side and enclose another net's terminal); None = unrestricted (old router)
        tubes = [0.04 * self.scale, 0.07 * self.scale, 0.1 * self.scale] + [None] * tries
        for attempt in range(tries):
            self.own = base_own.copy()
            self.ch = base_ch.copy()
            self.paths = {}
            failed = []
            tw = tubes[attempt]
            for v in order:
                if not (self.route_net(v, tw) or (tw is not None and self.route_net(v))):
                    failed.append(v)
            log(f'  routing attempt {attempt} (tube {tw if tw is None else round(tw)}): {len(failed)} nets failed {failed[:8]}')
            if not failed:
                return True
            rest = [v for v in order if v not in failed]
            rng.shuffle(rest)
            order = failed + sorted(rest, key=span) if attempt % 2 == 0 else failed + rest
        return False

    def route_negotiated(self, iters=80, log=print):
        """negotiated-congestion routing (PathFinder style, 2026-10-30). Nets live on the coarse even/even grid; two
        nets conflict exactly when they share a coarse node (8-adjacency of distinct nets is impossible otherwise, see
        route_net's spacing rule). Each round rips up and re-routes every net as a Steiner tree (repeated multi-source
        Dijkstra) with node cost (1 + history) * (1 + pres * others_using_it); shared nodes raise their history.
        Stops when the nets are node-disjoint. The finished map is still re-checked by check_map."""
        import heapq
        W, H = self.W, self.H
        base_own = self.own.copy()
        nets = sorted(self.terms)
        legal = {}
        for v in nets:                                    # per-net legal cells (foreign tiles / stubs / frame excluded)
            k = self.ids['N:' + v]
            foreign = (base_own != 0) & (base_own != k)
            bad = foreign.copy()
            bad[1:, :] |= foreign[:-1, :]
            bad[:-1, :] |= foreign[1:, :]
            b2 = bad.copy()
            b2[:, 1:] |= bad[:, :-1]
            b2[:, :-1] |= bad[:, 1:]
            b2[0, :] = b2[-1, :] = True
            b2[:, 0] = b2[:, -1] = True
            legal[v] = ~b2
        hist = np.zeros((H, W))
        occ = np.zeros((H, W), dtype=np.int32)
        use = {v: set() for v in nets}
        pres = 0.5
        for it in range(iters):
            for v in nets:
                for c in use[v]:
                    occ[c[1], c[0]] -= 1
                lg = legal[v]
                terms = list(self.terms[v])
                tree = {terms[0]}
                todo = set(terms[1:])
                nodes = set(tree)
                ok = True
                while todo:
                    dist = {c: 0.0 for c in tree}
                    prev = {c: None for c in tree}
                    pq = [(0.0, c) for c in tree]
                    heapq.heapify(pq)
                    hit = None
                    while pq:
                        d, c = heapq.heappop(pq)
                        if d > dist[c]:
                            continue
                        if c in todo:
                            hit = c
                            break
                        x, y = c
                        for dx, dy in ((2, 0), (-2, 0), (0, 2), (0, -2)):
                            t = (x + dx, y + dy)
                            if not (0 < t[0] < W - 1 and 0 < t[1] < H - 1) or not lg[t[1], t[0]] \
                                    or not lg[y + dy // 2, x + dx // 2]:
                                continue
                            nd = d + (1 + hist[t[1], t[0]]) * (1 + pres * occ[t[1], t[0]])
                            if nd < dist.get(t, 1e18):
                                dist[t] = nd
                                prev[t] = c
                                heapq.heappush(pq, (nd, t))
                    if hit is None:
                        ok = False
                        break
                    c = hit
                    while c is not None and c not in tree:
                        nodes.add(c)
                        tree.add(c)
                        c = prev[c]
                    todo.discard(hit)
                if not ok:
                    log(f'  negotiated routing: net {v} has no legal tree at all')
                    return False
                use[v] = nodes
                for c in nodes:
                    occ[c[1], c[0]] += 1
            self.neg_use = use
            shared = np.argwhere(occ > 1)
            extra = ''
            if 0 < len(shared) <= 3:
                extra = ' ' + str([((int(x), int(y)), [v for v in nets if (x, y) in use[v]]) for y, x in shared])
            log(f'  negotiated round {it}: {len(shared)} shared coarse nodes{extra}')
            if len(shared) == 0:
                break
            for y, x in shared:
                hist[y, x] += 1
            pres *= 1.6
        else:
            return False
        # commit: every coarse node + the connector cells between tree-adjacent nodes of the same net
        self.own = base_own.copy()
        self.paths = {}
        for v in nets:
            k = self.ids['N:' + v]
            cells = set(use[v])
            for (x, y) in use[v]:
                for dx, dy in ((2, 0), (0, 2)):
                    if (x + dx, y + dy) in use[v] and legal[v][y + dy // 2, x + dx // 2]:
                        cells.add((x + dx // 2, y + dy // 2))
            for (x, y) in cells:
                self.own[y, x] = k
                self.ch[y, x] = '.'
            self.paths[v] = sorted(cells)
        return True

    def tube(self, v, r):
        """cells within distance r of the drawing segments from net v's node point to each of its terminals"""
        px, py = self.pos['N:' + v]
        p = np.array([px * self.scale - self.shift[0], py * self.scale - self.shift[1]])
        yy, xx = np.mgrid[0:self.H, 0:self.W]
        m = np.zeros((self.H, self.W), dtype=bool)
        for t in self.terms[v]:
            q = np.array(t, dtype=float)
            d = q - p
            L2 = max(float(d @ d), 1e-9)
            u = np.clip(((xx - p[0]) * d[0] + (yy - p[1]) * d[1]) / L2, 0, 1)
            m |= (xx - p[0] - u * d[0]) ** 2 + (yy - p[1] - u * d[1]) ** 2 <= r * r
        return m

    def route_net(self, v, tube=None):
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
        if tube is not None:
            bad = bad | ~self.tube(v, tube)
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
    seed = int(sys.argv[sys.argv.index('--seed') + 1]) if '--seed' in sys.argv else 2         # v2 map: seed 2 (seed 1 leaves one unroutable face, b25/o8)
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
    scale = int(sys.argv[sys.argv.index("--scale") + 1]) if "--scale" in sys.argv else 420
    while True:
        L = Layout(bd, pos, scale)
        if L.place():
            print(f'  placement at scale {scale}: map {L.W} x {L.H}; SCD variants {sorted(T["tile"].variant for T in L.tiles.values() if T["kind"] == "scd")}; body not in widest sector: {L.nobody}')
            if L.route_negotiated() or L.route(seed, tries=8):
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
            kind=T['kind'], variant=getattr(tile, 'variant', None), sym=t, ox=T['ox'], oy=T['oy'], W=tile.W, H=tile.H, cells=T['cells'],
            local={f'{x},{y}': T['g']((x, y)) for (x, y) in tile.cells},
            local_ports={p: list(c) for p, (c, d, z) in tile.ports.items()},
            ports={p: dict(cell=P['cell'], zone=P['zone'], stub=P['stub'], node=P['node']) for p, P in T['ports'].items()},
            comps=[dict(name=cn, kind=ck, cells={f'{lx},{ly}': T['g']((ox + lx, oy + ly))
                                                  for ly, r in enumerate(S2.PROTO_PRECURSOR if ck == 'pp' else S2.PROTODIODE)
                                                  for lx, chh in enumerate(r) if chh != '#'})
                   for cn, ck, (ox, oy) in tile.comps],
            checks={c: [T['g'](z) for z in zs] for c, zs in tile.checks.items()},
            legs={l: dict(gside=T['g'](Lg['gside']), cells=[T['g'](c) for c in Lg['cells']], Wb=T['g'](Lg['Wb']),
                          mid=[T['g'](c) for c in Lg['mid']], Wt=T['g'](Lg['Wt']), node=Lg['node'])
                  for l, Lg in tile.legs.items()})
    out['tile_version'] = 2
    out['leg_len'] = LEG
    with open(os.path.join(OUT, 'crossover.txt'), 'w') as f:
        f.write('\n'.join(rows) + '\n')
    with open(os.path.join(OUT, 'crossover.json'), 'w') as f:
        json.dump(out, f)
    print(f'wrote build/xover/crossover.txt, crossover.json ({time.time() - t0:.0f}s)')


if __name__ == '__main__':
    main()
