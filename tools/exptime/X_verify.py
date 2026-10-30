#!/usr/bin/env python3
"""X_verify.py -- machine checks of the concrete crossover map built by X_build.py (workstream X).

  0. symmetry: every grid symmetry of the proto-precursor and protodiode boards gives an isomorphic gadget system
     (A_core.explore, exact state/transition bijection) -> rotated/reflected tile copies are VERIFIED copies;
  a. map -> wiring (X_build.check_map, re-run from the saved map only) -> Net2 of ideal SCDs + ideal diodes
     == directed crossover (sound + complete), negative controls fail;
  d. (tile v2) every placed tile: each check location on its own delimited leg (part_d, from the saved map);
  b. exact one-player port relation of that network in every reachable state (only A1->B1, A2->B2);
  c. concrete play on the full map with A_core.Board (one board, all 166 boulders):
     c1 scripted: realise A1->B1, A2->B2 (several rounds) move by move, planned per gadget on the canonical tile;
     c2 random walk (>= 100k moves) from random corridor cells / external ports;
     both run through one tracker that asserts after every move: boulders stay on their components' cells (G1, plus
     A_core LEAK on every port), every component clean (moves that would break a component are pruned = pruning lemma,
     counted), every observed component traversal p->q (s->s') is a transition of the raw component system, every
     observed tile traversal is a transition of the tile's postselected system (SCD: A2 §5b flat raw network
     restricted to clean) and keeps a nonempty set of related ideal states, and every external traversal is A1->B1,
     A2->B2 or a bounce, with the projected ideal state vector a reachable state of the ideal network.
Writes build/xover/routes.json (cells of the realised A1->B1 / A2->B2 walks, for X_render.py).
Usage: python X_verify.py [--moves N] [--seed S] [--ext-only]  (--ext-only: random episodes start only at external
ports, so the strict external-reachability check of the projected ideal vector applies to every external return)
"""
import json, os, random, sys, time
from collections import deque

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
import A_core as K
import A_check as AC
import A2_scd as S2
import A2_xover as X
import X_build as XB

OUT = os.path.join(ROOT, 'build', 'xover')
BUDGET = float(sys.argv[sys.argv.index('--budget') + 1]) if '--budget' in sys.argv else 1200
EXT = ['A1', 'A2', 'B1', 'B2']
P = lambda c: tuple(c)


def key(s):
    return tuple(map(int, s.split(',')))


# ============================================================ 0. symmetry invariance of the model
def sym_rows(rows, t):
    H, W = len(rows), max(map(len, rows))
    g = [r.ljust(W, '#') for r in rows]
    W2, H2 = XB.sym_size(t, W, H)
    out = [['#'] * W2 for _ in range(H2)]
    for y in range(H):
        for x in range(W):
            x2, y2 = XB.sym(t, x, y, W, H)
            out[y2][x2] = g[y][x]
    return [''.join(r) for r in out], (W, H)


def check_symmetry():
    ok = True
    for name, rows in (('proto-precursor', S2.PROTO_PRECURSOR), ('protodiode', S2.PROTODIODE)):
        b0 = K.Board(rows)
        C0 = K.explore(b0)
        for t in range(8):
            r2, (W, H) = sym_rows(rows, t)
            b1 = K.Board(r2)
            C1 = K.explore(b1)
            cm = {i: b1.idx[XB.sym(t, x, y, W, H)] for i, (x, y) in enumerate(b0.cells)}
            f = lambda B: sum(1 << cm[i] for i in range(len(b0.cells)) if B >> i & 1)
            same = (sorted(map(f, C0.states)) == sorted(C1.states) and f(C0.init) == C1.init and
                    all({(q, f(s2)) for q, s2 in C0.T[(s, p)]} == C1.T[(f(s), p)] for s in C0.states for p in C0.ports))
            ok &= same
        print(f'  {name}: all 8 grid symmetries give an isomorphic system ({len(C0.states)} states): {ok}')
    return ok


# ============================================================ map loading
class Map:
    def __init__(self):
        self.rows = open(os.path.join(OUT, 'crossover.txt')).read().split()
        self.J = json.load(open(os.path.join(OUT, 'crossover.json')))
        self.bd = XB.network()
        J = self.J
        self.tiles = {n: dict(cells=[P(c) for c in T['cells']],
                              ports={p: dict(cell=P(Q['cell']), zone=[P(z) for z in Q['zone']]) for p, Q in T['ports'].items()})
                      for n, T in J['tiles'].items()}
        self.ext = {e: P(c) for e, c in J['ext'].items()}


# ============================================================ a + b. abstract network from the map
def map_network(M):
    wiring, extk, comp, ncomp = XB.check_map(M.rows, M.tiles, M.ext, M.bd)
    node = {k: f'c{k}' for k in range(ncomp)}
    for e, k in extk.items():
        node[k] = e
    g = {}
    for n, (sysm, pm) in M.bd.g.items():
        ideal = AC.T_diode() if 'O' not in pm else X.scd_button('c')
        g[n] = (ideal, {p: node[wiring[n][p]] for p in pm})
    return g, wiring, extk, comp


def part_ab(M):
    ok = True
    g, wiring, extk, comp = map_network(M)
    print(f'  map re-checked: planar layout assertions hold; {len(set(comp.values()))} corridors')
    NW = S2.Net2(g, {e: e for e in EXT})
    N = NW.explore()
    s, c, _, _ = K.check(N, X.I_xover())
    print(f'  (a) map-derived network ({len(g)} gadgets) vs directed crossover: {len(N.states)} reachable states, '
          f'SOUND {s} COMPLETE {c}')
    ok &= s and c
    u = K.abstract(EXT, 'x', {'x': {'A1': [('B1', 'x')], 'A2': [('B2', 'x')], 'B1': [('A1', 'x')], 'B2': [('A2', 'x')]}})
    leak = K.abstract(EXT, 'x', {'x': {'A1': [('B1', 'x'), ('B2', 'x')], 'A2': [('B2', 'x')]}})
    cu = K.check(N, u)[1]
    cl = K.check(N, leak)[1]
    print(f'      negative controls: vs undirected COMPLETE {cu}, vs leaky A1->B2 COMPLETE {cl} (both expected False)')
    ok &= not cu and not cl
    # same wiring as A2's verified network, gadget by gadget (renaming only)
    bdn = X.Build()
    X.xover(bdn, 'A1', 'B1', 'A2', 'B2', 3)
    N2 = S2.Net2(bdn.g, {e: e for e in EXT}).explore()
    print(f'      A2 reference network: {len(N2.states)} reachable states (same count: {len(N2.states) == len(N.states)})')
    # (b) exact port relation in every reachable state
    rel = set()
    for st in N.states:
        for p in EXT:
            for q, _ in N.T[(st, p)]:
                rel.add((p, q))
    nonb = sorted((p, q) for p, q in rel if p != q)
    print(f'  (b) exact port relation over all {len(N.states)} reachable network states: {nonb} (bounces aside)')
    ok &= set(nonb) == {('A1', 'B1'), ('A2', 'B2')}
    # every state: both crossings available (unbounded reuse)
    both = all(any(q == 'B1' for q, _ in N.T[(st, 'A1')]) and any(q == 'B2' for q, _ in N.T[(st, 'A2')]) for st in N.states)
    print(f'      A1->B1 and A2->B2 both available in every reachable state: {both}')
    ok &= both
    return ok, N, NW


# ============================================================ d. split check legs on every placed tile (review 5 repair 1)
def part_d(M):
    """From the saved map + json only: for every tile copy, (i) its hero regions (component interiors removed) join
    exactly the intended ports; (ii) with all component-level Wb (resp. Wt) delimiter slots walled, every component
    port (incl. hidden pockets D, G) is alone in its region, i.e. every check location has its own delimited leg;
    (iii) tile-level legs (SCD O, I, J) delimit the tile ports. Same contract as X_build.check_tile_legs on the
    canonical tile, re-checked after symmetry + compaction."""
    canon_v = {('scd', k): XB.scd_tile(k) for k in XB.SCD_VARIANTS}
    canon_v[('dio', None)] = XB.diode_tile()
    floor = {(x, y) for y, r in enumerate(M.rows) for x, ch in enumerate(r) if ch != '#'}
    nlegs = nchk = 0
    for n, T in M.J['tiles'].items():
        cells = {P(c) for c in T['cells']}
        comps = [(C['name'], C['kind'], {key(lc): P(gc) for lc, gc in C['cells'].items()}) for C in T['comps']]
        owner, cport = XB.comp_owner(cells, comps)
        legs = {l: dict(gside=P(Lg['gside']), cells=[P(c) for c in Lg['cells']], Wb=P(Lg['Wb']), Wt=P(Lg['Wt']))
                for l, Lg in T['legs'].items()}
        tports = {p: P(Q['cell']) for p, Q in T['ports'].items()}
        ct = canon_v[(T['kind'], T.get('variant'))]
        assert set(legs) == set(ct.legs), ('leg set differs from canonical tile', n)
        XB.check_tile_legs(ct, cells=cells, owner=owner, cport=cport, legs=legs, tports=tports,
                           corner_floor=lambda c: c in floor)
        nlegs += len(legs)
        nchk += len(T['checks'])
    print(f'  (d) {len(M.J["tiles"])} placed tiles: every check location on its own delimited leg (Wb / Wt cut => '
          f'all component ports separated), intended joins only; {nlegs} legs, {nchk} check locations')
    return True


# ============================================================ tile systems (concrete, postselected) + ideal relations
def tile_systems():
    bp = K.Board(S2.PROTO_PRECURSOR)
    Cp = K.explore(bp)
    pclean, _, _, Pp = S2.postselect_L(Cp, S2.PP_CHECKS, S2.PP_L)
    bdd = K.Board(S2.PROTODIODE)
    Cd = K.explore(bdd)
    dclean, _, _, Pd = S2.postselect_L(Cd, S2.PD_CHECKS, ['A', 'B', 'C', 'D'])
    S1 = S2.pp_state(bp, (4, 6)) if hasattr(S2, 'pp_state') else sum(1 << bp.idx[(x, 2)] for x in (4, 6))
    Sc = sum(1 << bp.idx[(x, 2)] for x in (3, 5))

    def scd_net(Pprec, Ptog, Pdio, extra):
        pm_prec = {'A': 'T', 'B': 'T', 'C': 'T', 'E': 'X', 'F': 'Y'}
        pm_tog = {'A': 'tT', 'B': 'tT', 'C': 'tT', 'E': 'O', 'F': 'T'}
        if extra:
            pm_prec.update(D='pD', G='pG')
            pm_tog.update(D='tD', G='tG')
        return S2.Net2({'prec': (S2.with_init(Pprec, Sc), pm_prec), 'tog': (S2.with_init(Ptog, S1), pm_tog),
                        'd1': (Pdio, {'A': 'I', 'B': 'X', 'C': 'd1cd', 'D': 'd1cd'}),
                        'd2': (Pdio, {'A': 'Y', 'B': 'J', 'C': 'd2cd', 'D': 'd2cd'})}, {'O': 'O', 'I': 'I', 'J': 'J'})
    t0 = time.time()
    N5a = scd_net(Pp, Pp, Pd, False).explore()
    sclean, _, _ = K.postselect(N5a, [('O', 'O'), ('I', 'J')])
    NW5b = scd_net(Cp, Cp, Cd, True)
    N5b = NW5b.explore()
    names = NW5b.names
    okc = {'prec': pclean, 'tog': pclean, 'd1': dclean, 'd2': dclean}
    cl = {st for st in N5b.states if all(x in okc[n] for n, x in zip(names, st)) and st in sclean}
    T = {(st, p): {(q, s2) for q, s2 in N5b.T[(st, p)] if s2 in cl} for st in cl for p in N5b.ports}
    Pscd = K.System(N5b.ports, N5b.init, T, sorted(cl))
    ideal_scd = X.scd_button('c')
    s, c, Rs, Rc = K.check(Pscd, ideal_scd)
    print(f'  SCD tile system (A2 §5b, closed init): raw {len(N5b.states)} states, {len(cl)} clean; vs ideal SOUND {s} '
          f'COMPLETE {c} ({time.time() - t0:.0f}s)')
    Nd = S2.Net2({'d': (Cd, {'A': 'A', 'B': 'B', 'C': 'cd', 'D': 'cd'})}, {'A': 'A', 'B': 'B'}).explore()
    dcl = {st for st in Nd.states if st[0] in dclean}
    Td = {(st, p): {(q, s2) for q, s2 in Nd.T[(st, p)] if s2 in dcl} for st in dcl for p in Nd.ports}
    Pdio = K.System(Nd.ports, Nd.init, Td, sorted(dcl))
    sd, cd_, Rsd, Rcd = K.check(Pdio, AC.T_diode())
    print(f'  diode tile system: {len(dcl)} clean states; vs ideal SOUND {sd} COMPLETE {cd_}')
    return dict(bp=bp, bdd=bdd, Cp=Cp, Cd=Cd, pclean=pclean, dclean=dclean,
                scd=dict(sys=Pscd, names=names, ideal=ideal_scd, Rs=Rs, Rc=Rc, raw=set(N5b.states)),
                dio=dict(sys=Pdio, names=['d'], ideal=AC.T_diode(), Rs=Rsd, Rc=Rcd, raw=set(Nd.states)), ok=s and c and sd and cd_)


# ============================================================ c. concrete board + tracker
class Doom(Exception):
    pass


class Concrete:
    def __init__(self, M, TS, NWideal, Nideal):
        self.M, self.TS = M, TS
        rows = M.rows
        self.board = K.Board(rows)
        bd = self.board
        self.B0 = bd.b0
        J = M.J
        self.comp_of = {}          # global cell -> (tile, comp name)
        self.cport = {}            # global cell -> (tile, comp name, port letter)
        self.ctrack = {}           # (tile, comp) -> set of global cells
        self.cloc = {}             # (tile, comp) -> {global cell: local cell}
        self.ckind = {}
        for n, T in J['tiles'].items():
            for C in T['comps']:
                kb = TS['bp'] if C['kind'] == 'pp' else TS['bdd']
                rows_l = S2.PROTO_PRECURSOR if C['kind'] == 'pp' else S2.PROTODIODE
                kk = (n, C['name'])
                self.ckind[kk] = C['kind']
                self.cloc[kk] = {}
                for lc, gc in C['cells'].items():
                    lx, ly = key(lc)
                    gc = P(gc)
                    self.cloc[kk][gc] = (lx, ly)
                    ch = rows_l[ly][lx]
                    if ch.isupper():
                        self.cport[gc] = (n, C['name'], ch)
                    else:
                        self.comp_of[gc] = kk
                self.ctrack[kk] = set(self.cloc[kk])
        # every tile copy == its canonical tile under the recorded symmetry (cell by cell, boulders included)
        canon = {('scd', k): XB.scd_tile(k) for k in XB.SCD_VARIANTS}
        canon[('dio', None)] = XB.diode_tile()
        for n, T in J['tiles'].items():
            tl = canon[(T['kind'], T.get('variant'))]
            assert len(T['local']) == len(tl.cells) == len(T['cells'])
            for lc, gc in T['local'].items():
                x, y = P(gc)
                assert rows[y][x] == tl.cells[key(lc)], ('tile copy differs from canonical tile', n, lc)
                assert XB.sym(T['sym'], *key(lc), T['W'], T['H']) is not None
            for p, lc in T['local_ports'].items():
                assert P(T['local'][f'{lc[0]},{lc[1]}']) == M.tiles[n]['ports'][p]['cell']
        pm = 0
        for c in list(self.cport) + list(M.ext.values()):
            pm |= 1 << bd.idx[c]
        bd.portmask = pm                         # A_core raises LeakError on any push onto a port cell
        self.tile_of = {}
        self.zone = {}                           # global cell -> (tile, tile-port)
        for n, T in M.tiles.items():
            for c in T['cells']:
                self.tile_of[c] = n
            for p, Q in T['ports'].items():
                for z in Q['zone']:
                    self.zone[z] = (n, p)
        self.kind = {n: T['kind'] for n, T in J['tiles'].items()}
        self.extcell = {c: e for e, c in M.ext.items()}
        self.corr = [c for c in bd.cells if c not in self.tile_of]
        self.gnames = NWideal.names
        self.reach_ideal = set(Nideal.states)
        # random-walk episodes may start at an internal corridor cell, i.e. DROP the hero at an internal junction,
        # which the external-port network model does not allow. reach_any = closure of the initial ideal vector under
        # single gadget traversals from ANY node (superset of every walk with drops). The external-reachability check
        # is enforced until the first drop; afterwards the vector must lie in reach_any (2026-10-30, v2 rerun).
        reach_any = set(Nideal.states)
        todo = list(reach_any)
        while todo:
            St = todo.pop()
            for gi, g in enumerate(NWideal.names):
                sysm, pm = NWideal.g[g]
                for p in pm:
                    for _, s2 in sysm.T.get((St[gi], p), ()):
                        S2_ = St[:gi] + (s2,) + St[gi + 1:]
                        if S2_ not in reach_any:
                            reach_any.add(S2_)
                            todo.append(S2_)
        self.reach_any = reach_any
        self.dropped = False
        self.stats = dict(moves=0, pruned=0, ctrav=0, ttrav=0, etrav=0, doom=0, vec_drop_only=0)
        self.reset_tracking()
        # ideal state sets per tile
        self.iset = {n: {'c'} if self.kind[n] == 'scd' else {'d'} for n in M.tiles}

    def reset_tracking(self):
        self.last_cport = None       # (cell, comp key, port, comp state)
        self.inside_c = set()
        self.last_tport = None       # (tile, port, tile state)
        self.inside_t = set()
        self.last_ext = None
        self.left_ext = False

    # ---- projections
    def cstate(self, kk, B):
        kb = self.TS['bp'] if self.ckind[kk] == 'pp' else self.TS['bdd']
        bd = self.board
        return sum(1 << kb.idx[l] for g, l in self.cloc[kk].items() if B >> bd.idx[g] & 1)

    def tstate(self, n, B):
        names = self.TS[self.kind[n]]['names']
        if self.kind[n] == 'dio':
            return (self.cstate((n, 'd'), B),)
        return tuple(self.cstate((n, c), B) for c in names)

    def cclean(self, kk, s):
        return s in (self.TS['pclean'] if self.ckind[kk] == 'pp' else self.TS['dclean'])

    # ---- one move
    def legal(self, h, B, count=True):
        """legal moves, minus moves that would break a component (pruned = pruning lemma, counted)"""
        out = []
        for h2, B2 in self.board.moves(h, B):
            if B2 != B:
                kk = self.comp_of[self.board.cells[h2]]          # a boulder only ever sits on interior cells
                if not self.cclean(kk, self.cstate(kk, B2)):
                    if count:
                        self.stats['pruned'] += 1
                    continue
            out.append((h2, B2))
        return out

    def step(self, h, B, h2, B2):
        """apply + check one move"""
        assert (h2, B2) in set(self.board.moves(h, B)), 'illegal move'
        self.stats['moves'] += 1
        bd = self.board
        c = bd.cells[h2]
        if B2 != B:
            pushed_to = bd.cells[(B2 & ~B).bit_length() - 1]
            kk = self.comp_of[c]
            assert pushed_to in self.ctrack[kk] and pushed_to not in self.cport, ('boulder left its component', kk)
            assert self.cclean(kk, self.cstate(kk, B2)), 'component broken'
        # component level
        if c in self.comp_of:
            self.inside_c.add(self.comp_of[c])
        elif c in self.cport:
            n, cn, q = self.cport[c]
            kk = (n, cn)
            s2 = self.cstate(kk, B2)
            if self.last_cport is not None:
                (c0, kk0, p0, s0) = self.last_cport
                assert len(self.inside_c) <= 1, ('walk crossed two components without a port', self.inside_c)
                if self.inside_c:
                    (ki,) = self.inside_c
                    assert ki == kk0 == kk, ('traversal changed component', ki, kk0, kk)
                    C = self.TS['Cp'] if self.ckind[kk] == 'pp' else self.TS['Cd']
                    assert (q, s2) in C.T[(s0, p0)] or (q == p0 and s2 == s0), ('component traversal not in system', kk, p0, q)
                    self.stats['ctrav'] += 1
            self.last_cport = (c, kk, q, s2)
            self.inside_c = set()
        else:
            assert not self.inside_c, 'left a component interior without a port'
        # tile level
        if c in self.zone:
            n, q = self.zone[c]
            s2 = self.tstate(n, B2)
            if self.last_tport is not None:
                n0, p0, s0 = self.last_tport
                if self.inside_t:
                    assert self.inside_t == {n} and n0 == n, ('tile traversal mixes tiles', self.inside_t, n0, n)
                    TSk = self.TS[self.kind[n]]
                    Ssys = TSk['sys']
                    assert s0 in Ssys.states, ('tile traversal started outside the clean set', n)
                    if s2 not in Ssys.states:
                        assert s2 in TSk['raw'], ('tile state unknown to the raw system', n)
                        raise Doom(n, p0, q)          # breaking tile traversal: Doom (pruning lemma)
                    assert (q, s2) in Ssys.T[(s0, p0)] or (q == p0 and s2 == s0), ('tile traversal not in system', n, p0, q)
                    I, Rs = TSk['ideal'], TSk['Rs']
                    new = {a2 for a in self.iset[n] for q2, a2 in I.T.get((a, p0), ()) if q2 == q and (s2, a2) in Rs}
                    if q == p0:
                        new |= {a for a in self.iset[n] if (s2, a) in Rs}
                    assert new, ('no related ideal state', n)
                    self.iset[n] = new
                    self.stats['ttrav'] += 1
            self.last_tport = (n, q, s2)
            self.inside_t = set()
        elif c in self.tile_of:
            self.inside_t.add(self.tile_of[c])
        # external level
        if c in self.extcell:
            e = self.extcell[c]
            if self.last_ext is not None and self.left_ext:
                assert e == self.last_ext or (self.last_ext, e) in (('A1', 'B1'), ('A2', 'B2')), \
                    ('illegal external traversal', self.last_ext, e)
                inn = lambda st: all(st[i] in self.iset[g] for i, g in enumerate(self.gnames))
                if not any(inn(st) for st in self.reach_ideal):
                    assert self.dropped, 'projected ideal vector not reachable from the external ports (no drop yet)'
                    assert any(inn(st) for st in self.reach_any), 'projected ideal vector not reachable even with drops'
                    self.stats['vec_drop_only'] += 1
                self.stats['etrav'] += 1
            self.last_ext = e
            self.left_ext = False
        else:
            self.left_ext = True
        return h2, B2


# ---------------- scripted crossings
def plan(NW, S, src, dst):
    """BFS over (node, ideal state vector) from external src to dst, never through another external node."""
    start = (src, S)
    prev = {start: None}
    dq = deque([start])
    while dq:
        node, St = dq.popleft()
        if node == dst:
            out = []
            cur = (node, St)
            while prev[cur] is not None:
                out.append(prev[cur][1])
                cur = prev[cur][0]
            return out[::-1], St
        if node in NW.extnode and node != src:
            continue
        for gi, port in NW.at.get(node, []):
            sysm, pm = NW.g[NW.names[gi]]
            for q, s2 in sysm.T[(St[gi], port)]:
                S2_ = St[:gi] + (s2,) + St[gi + 1:]
                nxt = (pm[q], S2_)
                if nxt not in prev:
                    prev[nxt] = ((node, St), (NW.names[gi], port, q, St[gi], s2))
                    dq.append(nxt)
    raise AssertionError('no plan')


def corridor_walk(CC, h, B, target_cell):
    bd = CC.board
    tgt = bd.idx[target_cell]
    allowed = lambda i: bd.cells[i] not in CC.tile_of or bd.cells[i] in CC.zone or i == tgt
    prev = {h: None}
    dq = deque([h])
    while dq:
        x = dq.popleft()
        if x == tgt:
            break
        for y, B2 in bd.moves(x, B):
            if B2 == B and y not in prev and allowed(y):
                prev[y] = x
                dq.append(y)
    assert tgt in prev, 'corridor walk failed'
    path = [tgt]
    while prev[path[-1]] is not None:
        path.append(prev[path[-1]])
    return path[::-1]


def tile_walk(CC, n, h, B, q, goal_ideal):
    """BFS inside tile n from port cell h to a cell of port q's zone, tile ending in a clean state related to
    goal_ideal by the COMPLETE relation (ts realises everything goal_ideal can). State (hero, boulders, been-inside flag); entering any zone of n after being inside ends the walk."""
    bd = CC.board
    TSk = CC.TS[CC.kind[n]]
    tiles = set(CC.M.tiles[n]['cells'])
    zones = {z for Q in CC.M.tiles[n]['ports'].values() for z in Q['zone']}
    zq = set(CC.M.tiles[n]['ports'][q]['zone'])
    start = (h, B, 0)
    prev = {start: None}
    dq = deque([start])
    hit = None
    while dq:
        st = dq.popleft()
        hh, BB, f = st
        cc = bd.cells[hh]
        if f and cc in zones:
            if cc in zq:
                ts = CC.tstate(n, BB)
                if ts in TSk['sys'].states and (goal_ideal, ts) in TSk['Rc']:   # ts can do all goal can
                    hit = st
                    break
            continue
        for h2, B2 in CC.legal(hh, BB, count=False):
            c2 = bd.cells[h2]
            if c2 not in tiles:
                continue
            nxt = (h2, B2, f or (c2 not in zones))
            if nxt not in prev:
                prev[nxt] = st
                dq.append(nxt)
        if len(prev) > 3_000_000:
            raise RuntimeError('tile walk too big')
    assert hit, ('tile walk failed', n, q, goal_ideal)
    path = [hit]
    while prev[path[-1]] is not None:
        path.append(prev[path[-1]])
    return [(a, b) for a, b, _ in path[::-1]]


def scripted(CC, NWi, rounds):
    bd = CC.board
    B = CC.B0
    S = tuple(NWi.g[n][0].init for n in NWi.names)
    cells = {'A1B1': set(), 'A2B2': set()}
    seq = []
    for r in range(rounds):
        seq += [('A1', 'B1'), ('A2', 'B2')]
    seq += [('A1', 'B1'), ('A1', 'B1'), ('A2', 'B2'), ('A2', 'B2')]
    lengths = []
    for src, dst in seq:
        steps, S_end = plan(NWi, S, src, dst)
        h = bd.idx[CC.M.ext[src]]
        CC.reset_tracking()
        CC.last_ext, CC.left_ext = src, False
        nm = 0
        for (gname, p, q, a0, a1) in steps:
            pc = CC.M.tiles[gname]['ports'][p]['cell']
            path = corridor_walk(CC, h, B, pc)
            for x in path[1:]:
                h, B = CC.step(h, B, x, B)
                cells[src + dst].add(bd.cells[h])
                nm += 1
            tw = tile_walk(CC, gname, h, B, q, a1)
            for (h2, B2) in tw[1:]:
                h, B = CC.step(h, B, h2, B2)
                cells[src + dst].add(bd.cells[h])
                nm += 1
        path = corridor_walk(CC, h, B, CC.M.ext[dst])
        for x in path[1:]:
            h, B = CC.step(h, B, x, B)
            cells[src + dst].add(bd.cells[h])
            nm += 1
        assert bd.cells[h] == CC.M.ext[dst]
        S = S_end
        lengths.append((src, dst, len(steps), nm))
    return B, cells, lengths


def random_walk(CC, B, nmoves, rng, ep_len=1500):
    """uniform random legal (non-component-breaking) moves. A tile traversal that ends tile-broken (e.g. the SCD's
    O->J leak) is Doom: it is undone back to the last corridor snapshot and counted (= deleting that hero edge)."""
    import copy
    bd = CC.board
    exts = list(CC.M.ext.values())
    done = 0
    episodes = 0
    track = ('last_cport', 'inside_c', 'last_tport', 'inside_t', 'last_ext', 'left_ext', 'iset')
    t0 = time.time()
    nxt = 10000
    base = CC.stats['moves']
    CC.stats.setdefault('stuck', 0)
    while done < nmoves:
        if time.time() - t0 > BUDGET:
            print(f'  (time budget {BUDGET}s reached)', flush=True)
            break
        episodes += 1
        h = bd.idx[rng.choice(exts)] if ('--ext-only' in sys.argv or rng.random() < 0.3) else bd.idx[rng.choice(CC.corr)]
        if bd.cells[h] not in CC.extcell:
            CC.dropped = True
        CC.reset_tracking()
        if bd.cells[h] in CC.extcell:
            CC.last_ext = CC.extcell[bd.cells[h]]
        snap = (h, B, copy.deepcopy({a: getattr(CC, a) for a in track}), dict(CC.stats))
        k = 0
        since = 0
        while True:
            mv = CC.legal(h, B)
            h2, B2 = rng.choice(mv)
            undo = None
            try:
                h, B = CC.step(h, B, h2, B2)
                k += 1
                since += 1
                if since > 5000:
                    undo = 'stuck'          # trapped inside a tile (e.g. sealed in by its own pushes): abandon branch
            except Doom:
                undo = 'doom'
            if undo:
                h, B, saved, st0 = snap
                for a, v in copy.deepcopy(saved).items():
                    setattr(CC, a, v)
                for kk in ('moves', 'ctrav', 'ttrav', 'etrav'):
                    CC.stats[kk] = st0[kk]          # undone moves are not counted
                CC.stats[undo] += 1
                done = CC.stats['moves'] - base
                since = 0
                if time.time() - t0 > BUDGET:
                    break
                continue
            done = CC.stats['moves'] - base
            if done >= nxt:
                print(f'    {done} committed moves, {time.time() - t0:.0f}s, stats {CC.stats}', flush=True)
                nxt += 10000
            if time.time() - t0 > BUDGET:
                break
            if bd.cells[h] not in CC.tile_of:
                snap = (h, B, copy.deepcopy({a: getattr(CC, a) for a in track}), dict(CC.stats))
                since = 0
                if k >= ep_len or done >= nmoves:
                    break
    return B, episodes


# ============================================================ main
def main():
    nmoves = int(sys.argv[sys.argv.index('--moves') + 1]) if '--moves' in sys.argv else 120000
    seed = int(sys.argv[sys.argv.index('--seed') + 1]) if '--seed' in sys.argv else 7
    t0 = time.time()
    ok = True
    print('== 0. grid symmetries (rotated / reflected tile copies)')
    ok &= check_symmetry()
    M = Map()
    nb = sum(r.count('0') for r in M.rows)
    print(f'== map {M.J["W"]} x {M.J["H"]}, {nb} boulders, {len(M.tiles)} tiles')
    print('== a/b. abstract network read off the map')
    okab, Ni, NWi = part_ab(M)
    ok &= okab
    print('== d. split check legs (tile v2)')
    ok &= part_d(M)
    print('== c. concrete play on the full map')
    TS = tile_systems()
    ok &= TS['ok']
    CC = Concrete(M, TS, NWi, Ni)
    B, cells, lengths = scripted(CC, NWi, rounds=2)
    for src, dst, ng, nm in lengths:
        print(f'  c1 scripted {src}->{dst}: {ng} gadget traversals, {nm} hero moves, reached {dst}')
    st1 = dict(CC.stats)
    print(f'  c1 totals: {st1}')
    rng = random.Random(seed)
    B, eps = random_walk(CC, B, nmoves, rng)
    st2 = {k: CC.stats[k] - st1.get(k, 0) for k in CC.stats}
    print(f'  c2 random walk: {eps} episodes, {st2["moves"]} moves, {st2["ctrav"]} component traversals, '
          f'{st2["ttrav"]} tile traversals, {st2["etrav"]} external returns checked ({st2["vec_drop_only"]} explained only with drops; {len(CC.reach_any)} drop-closure states), {st2["pruned"]} component-breaking moves pruned, {st2["doom"]} tile-breaking traversals undone, {CC.stats.get("stuck", 0)} trapped excursions abandoned; '
          f'no assertion failed')
    json.dump({k: sorted(v) for k, v in cells.items()}, open(os.path.join(OUT, 'routes.json'), 'w'))
    print(f'wrote build/xover/routes.json ({time.time() - t0:.0f}s)')
    print('ALL AS EXPECTED' if ok else 'SOME UNEXPECTED RESULT')
    return ok


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
