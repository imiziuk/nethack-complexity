#!/usr/bin/env python3
"""M_verify.py -- machine checks of the concrete machinery boards built by M_build.py (workstream M).

  0. model symmetry: all 8 grid symmetries of the Fig. 32 boards WMC / NR / WO give isomorphic A_core systems, and
     every base-board copy on a map equals its canonical board under its symmetry, cell by cell (walls too);
  w. M_build.SPEC == the wiring B2_ani's sd_from / so_from / msc_from / sx_from / wcx_from actually build (recorded by
     calling them with a capturing `net`), so the boards realize exactly the networks B2 verified;
  a. per board, from the saved map + json only: X_build.check_map with every base-board copy as a tile (copies pairwise
     not 8-adjacent, one corridor per flat node, corridors touch copies only at their port cells, frame closed except
     the external ports) and flat wiring == the flattened composition network up to node renaming; every boulder of
     the map belongs to a copy; exact boulder reach of every copy (union over its reachable states) stays inside the
     copy and off its port cells; the same check for all 8 symmetric images of the board (orientations);
  b. exact port behaviour, bottom-up: base systems (A_core.explore), then for each level the Net2 network (A2_scd) of
     the children's bisimulation quotients, its own bisimulation quotient, and SOUND + COMPLETE vs the ideal Fig. 19
     automaton (B2_ani.I_SD / I_SO / I_MSC / I_SX / I_WCX); plus for MSC the flat network (5 base boards) == nested
     (bisimilar) as a check of the hierarchy step; optional (--flat-sd) direct A_core.explore of the whole SD map;
  c1. scripted play: every ideal transition sequence below realized move by move on the full board (one A_core board,
     all boulders), planned top-down through the levels (BFS over child quotient states, base traversals by BFS
     inside the copy), every move checked by the tracker;
  c2. random play: uniform random legal moves on the full board from the initial position (episodes restart from
     scratch), every move checked by the tracker.
  Tracker (c1, c2): A_core moves on the whole map; a push onto ANY port cell (base ports, external ports) raises
  LeakError; every base-copy traversal (port -> interior -> port) is a transition of the canonical board's system;
  at every port arrival every instance at every level projects to an explored state of its level system; every
  instance traversal at every level (between visits of its external nodes) is a transition of its level system;
  every return to an external port of the board keeps a non-empty set of SOUND-related ideal states.
Usage: python M_verify.py [G ...] [--moves N] [--seed S] [--flat-sd]
"""
import json, os, pickle, random, sys, time
from collections import deque

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
import A_core as K
import A2_scd as A2
import B2_ani as BA
import X_build as XB
import M_build as MB

OUT = MB.OUT
def I_HK():
    """HK has no Fig. 19 automaton: its spec is B2_e2e.gprime's check unit, i.e. the same wiring of ideal SX, SO, SD"""
    sp = MB.SPEC['HK']
    ideal = {'SX': BA.I_SX(), 'SO': BA.I_SO(), 'SD': BA.I_SD()}
    # external ports = frame cells, as for the concrete 'top' system: the external nodes get a free hallway each
    hall = K.abstract(['P', 'Q'], 'h', {'h': {'P': [('Q', 'h')], 'Q': [('P', 'h')]}})
    g = {n: (ideal[k], {p: (v + '~' if v in sp['sides'] else v) for p, v in pm.items()}) for n, (k, pm) in sp['parts'].items()}
    g.update({'hall:' + e: (hall, {'P': e, 'Q': e + '~'}) for e in sp['sides']})
    return A2.Net2(g, {e: e for e in sp['sides']}).explore()


IDEAL = {'SD': BA.I_SD, 'SO': BA.I_SO, 'MSC': BA.I_MSC, 'SX': BA.I_SX, 'WCX': BA.I_WCX, 'HK': I_HK}
SCRIPTS = {      # ideal traversal sequences realized move by move (each list from a fresh board)
    'SD': [[('X', 'Y')]],
    'SO': [[('Op', 'Op'), ('In', 'Out')]],
    'MSC': [[('L', 'R'), ('R', 'L'), ('L', 'R'), ('T', 'R')]],
    'SX': [[('L', 'R'), ('Tp', 'Bt')]],
    'WCX': [[('L', 'R'), ('R', 'L'), ('L', 'R'), ('R', 'L'), ('Bt', 'Tp')],
            [('R', 'L'), ('Bt', 'R'), ('R', 'L'), ('L', 'Tp')],
            [('Bt', 'L'), ('L', 'R'), ('R', 'Tp')]],
    'HK': [[('wi', 'wo'), ('op', 'op'), ('op', 'a'), ('b', 'out')]],
}


# ============================================================ helpers
def bisim(S):
    """coarsest strong bisimulation of a System (labels (p, q), bounces included). Returns (cls dict, quotient)."""
    st = list(S.states)
    idx = {s: i for i, s in enumerate(st)}
    succ = [[(p, q, idx[s2]) for p in S.ports for q, s2 in S.T[(s, p)]] for s in st]
    blk = [0] * len(st)
    nblk = 1
    while True:
        sig = {}
        nb = [sig.setdefault((blk[i], frozenset((p, q, blk[j]) for p, q, j in succ[i])), len(sig))
              for i in range(len(st))]
        if len(sig) == nblk:
            break
        blk, nblk = nb, len(sig)
    cls = {s: blk[i] for i, s in enumerate(st)}
    T = {}
    for i, s in enumerate(st):
        for p in S.ports:
            T.setdefault((blk[i], p), {(q, blk[j]) for q, j in ((q, idx[s2]) for q, s2 in S.T[(s, p)])})
    return cls, K.System(S.ports, cls[S.init], T, sorted(set(blk)))


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


class LBoard(K.Board):
    """A_core.Board whose LEAK mask (pushes onto these cells raise) is separate from the traversal port mask."""
    def __init__(self, rows, leak=()):
        super().__init__(rows)
        self.leak = sum(1 << self.idx[c] for c in leak)

    def moves(self, h, B):
        for t, b in self.orth[h]:
            if B >> t & 1:
                if b < 0 or B >> b & 1:
                    continue
                if (self.portmask | self.leak) >> b & 1:
                    raise K.LeakError((self.cells[t], self.cells[b]))
                yield t, (B & ~(1 << t)) | (1 << b)
            else:
                yield t, B
        for t, cm in self.diag[h]:
            if B >> t & 1:
                continue
            if cm & ~B:
                yield t, B


# ============================================================ 0. symmetry
def check_symmetry(base):
    ok = True
    for name, rows in MB.BASE.items():
        b0 = K.Board(rows)
        C0 = base[name]
        good = True
        for t in range(8):
            r2, (W, H) = sym_rows(rows, t)
            b1 = K.Board(r2)
            C1 = K.explore(b1)
            cm = {i: b1.idx[XB.sym(t, x, y, W, H)] for i, (x, y) in enumerate(b0.cells)}
            f = lambda B: sum(1 << cm[i] for i in range(len(b0.cells)) if B >> i & 1)
            good &= (sorted(map(f, C0.states)) == sorted(C1.states) and f(C0.init) == C1.init and
                     all({(q, f(s2)) for q, s2 in C0.T[(s, p)]} == C1.T[(f(s), p)] for s in C0.states for p in C0.ports))
        print(f'  {name}: {len(C0.states)} states; all 8 grid symmetries isomorphic: {good}')
        ok &= good
    return ok


# ============================================================ w. SPEC == B2_ani wiring
def check_spec():
    cap = []
    real = BA.net
    BA.net = lambda gadgets, ext: cap.append((gadgets, ext)) or None
    try:
        D = BA.I_SD()
        BA.sd_from(D, D, D); BA.so_from(D, D); BA.msc_from(D, D); BA.sx_from(D, D); BA.wcx_from(D, D, D)
    finally:
        BA.net = real
    names = ['SD', 'SO', 'MSC', 'SX', 'WCX']
    ok = True
    for nm, (g, ext) in zip(names, cap):
        want = {n: pm for n, (s, pm) in g.items()}
        if nm == 'WCX':                       # the free hallway L-a is one corridor in the drawing: a := L
            assert want.pop('hall') == {'P': 'L', 'Q': 'a'}
            want = {n: {p: ('L' if v == 'a' else v) for p, v in pm.items()} for n, pm in want.items()}
        got = {n: pm for n, (k, pm) in MB.SPEC[nm]['parts'].items()}
        same = got == want and sorted(ext) == sorted(MB.SPEC[nm]['sides'])
        print(f'  {nm}: M_build.SPEC == B2_ani wiring: {same}')
        ok &= same
    return ok


# ============================================================ a. map checks
class Map:
    def __init__(self, kind, t=0):
        self.kind = kind
        rows = open(os.path.join(OUT, kind + '.txt')).read().split()
        J = json.load(open(os.path.join(OUT, kind + '.json')))
        H, W = len(rows), len(rows[0])
        if t:
            rows, _ = sym_rows(rows, t)
        f = (lambda c: XB.sym(t, c[0], c[1], W, H)) if t else (lambda c: tuple(c))
        self.rows, self.J, self.H, self.W = rows, J, len(rows), len(rows[0])
        self.ext = {e: f(c) for e, c in J['ext'].items()}
        self.parts = []                  # (path, kind, {canonical cell: global cell})
        for P in J['parts']:
            self.parts.append((P['path'], P['kind'], {(a, b): f((c, d)) for a, b, c, d in P['sym_cells']}))
        self.net = {N['path']: (N['kind'], N['ports']) for N in J['net']}


def check_map(M):
    """returns (wiring, comp, ncomp) and asserts everything in part a"""
    rows = M.rows
    tiles, seen = {}, {}
    for path, kind, cm in M.parts:
        canon = MB.BASE[kind]
        Hc, Wc = len(canon), max(map(len, canon))
        # every canonical floor cell is mapped; mapped cells equal the canonical board (walls included)
        for y in range(Hc):
            for x in range(Wc):
                ch = canon[y][x] if x < len(canon[y]) else '#'
                if (x, y) not in cm:
                    assert ch == '#', ('canonical floor cell missing from the copy', path, (x, y))
                    continue
                gx, gy = cm[(x, y)]
                want = '.' if ch.isupper() else ch
                assert rows[gy][gx] == want, ('copy differs from the canonical board', path, (x, y), rows[gy][gx], ch)
                if ch != '#':
                    assert (gx, gy) not in seen, ('copies overlap', path, seen.get((gx, gy)))
                    seen[(gx, gy)] = path
        # the map is the canonical board under ONE grid symmetry + translation
        pts = sorted(cm)
        (x0, y0), g0 = pts[0], cm[pts[0]]
        okt = False
        for t in range(8):
            W2, H2 = XB.sym_size(t, Wc, Hc)
            s0 = XB.sym(t, x0, y0, Wc, Hc)
            dx, dy = g0[0] - s0[0], g0[1] - s0[1]
            if all(XB.sym(t, a, b, Wc, Hc) == (c[0] - dx, c[1] - dy) for (a, b), c in cm.items()):
                okt = True
                break
        assert okt, ('copy is not a symmetric image of the canonical board', path)
        cells = [cm[(x, y)] for y in range(Hc) for x in range(len(canon[y])) if canon[y][x] != '#']
        ports = {canon[y][x]: dict(cell=cm[(x, y)], zone=[cm[(x, y)]])
                 for y in range(Hc) for x in range(len(canon[y])) if canon[y][x].isupper()}
        tiles[path] = dict(cells=cells, ports=ports)
    nb = sum(r.count('0') for r in rows)
    nb_copies = sum(1 for _, k, cm in M.parts for (x, y), c in cm.items()
                    if x < len(MB.BASE[k][y]) and MB.BASE[k][y][x] == '0')
    assert nb == nb_copies, ('stray boulders outside the copies', nb, nb_copies)
    bd = MB._BD({p: (None, pm) for p, (k, pm) in M.net.items()})
    assert set(bd.g) == set(tiles), 'copies != flat network gadgets'
    wiring, extk, comp, ncomp = XB.check_map(rows, tiles, M.ext, bd)
    return wiring, extk, comp, ncomp, tiles


def boulder_reach(M, base, tiles):
    """exact boulder reach of every copy: union of boulder cells over all states of its canonical system"""
    reach_c = {}
    for k, S in base.items():
        b = K.Board(MB.BASE[k])
        acc = 0
        for s in S.states:
            acc |= s
        reach_c[k] = {b.cells[i] for i in range(len(b.cells)) if acc >> i & 1}
    tot = 0
    for path, kind, cm in M.parts:
        R = {cm[c] for c in reach_c[kind]}
        T = tiles[path]
        assert R <= set(T['cells']), ('boulder reach leaves the copy', path)
        assert not R & {P['cell'] for P in T['ports'].values()}, ('boulder reach meets a port cell', path)
        tot += len(R)
    return tot


# ============================================================ b. exact behaviour
def level_systems(base, log=print, want=None):
    """bottom-up: raw systems, bisim classes, quotients per kind (composites: Net2 of the children's quotients)"""
    L = {}
    for k, S in base.items():
        cls, Q = bisim(S)
        L[k] = dict(raw=S, cls=cls, Q=Q)
        log(f'  {k}: {len(S.states)} states, {len(Q.states)} bisimulation classes')
    for kind in MB.ORDER:
        if want and MB.ORDER.index(kind) > max(MB.ORDER.index(w) for w in want):
            break
        t0 = time.time()
        sp = MB.SPEC[kind]
        g = {n: (L[k]['Q'], pm) for n, (k, pm) in sp['parts'].items()}
        net = A2.Net2(g, {e: e for e in sp['sides']})
        # cache of the explored level system, keyed by the exact children quotients + wiring (SD takes ~9 min)
        import hashlib
        key = hashlib.sha256(repr((kind, sorted((n, sorted(pm.items()), sorted((k2, sorted(v)) for k2, v in Qc.T.items()),
                                                  Qc.init) for n, (Qc, pm) in g.items()))).encode()).hexdigest()[:16]
        cfile = os.path.join(OUT, f'level_{kind}_{key}.pkl')
        if os.path.exists(cfile):
            S = pickle.load(open(cfile, 'rb'))
            cached = ' (cached)'
        else:
            S = net.explore()
            pickle.dump(S, open(cfile, 'wb'))
            cached = ''
        cls, Q = bisim(S)
        I = IDEAL[kind]()
        s0, c0, _, _ = K.check(Q, I)
        # 'core' = the level with its external ports equal to the external CORRIDORS (a traversal ends as soon as
        # the hero is anywhere on an external corridor): right for a child inside a larger board, whose parent goes
        # on from that node. 'top' = the board as a gadget of the level: its external ports are the FRAME cells at
        # the end of the external stubs, i.e. core + a free hallway (B2_ani's 'hall') from each frame cell to its
        # corridor; a walk may pass through an external corridor without ending. The ideal comparison is on 'top'.
        hall = K.abstract(['P', 'Q'], 'h', {'h': {'P': [('Q', 'h')], 'Q': [('P', 'h')]}})
        tg = {'core': (Q, {e: e + '~' for e in sp['sides']})}
        tg.update({'hall:' + e: (hall, {'P': e, 'Q': e + '~'}) for e in sp['sides']})
        tnet = A2.Net2(tg, {e: e for e in sp['sides']})
        TS = tnet.explore()
        tcls, TQ = bisim(TS)
        s, c, Rs, Rc = K.check(TQ, I)
        L[kind] = dict(raw=S, cls=cls, Q=Q, net=net, I=I, Rs=Rs, Rc=Rc, sound=s, complete=c,
                       core_sound=s0, core_complete=c0, top=dict(net=tnet, raw=TS, cls=tcls, Q=TQ))
        log(f'  {kind}: Net2 of {len(g)} children (quotients) -> {len(S.states)} states, {len(Q.states)} bisimulation '
            f'classes ({time.time() - t0:.0f}s{cached}); ports = external corridors: SOUND {s0} COMPLETE {c0}; '
            f'ports = frame cells (board as a gadget): {len(TQ.states)} classes, vs ideal {kind}: SOUND {s} COMPLETE {c}')
    return L


def flat_vs_nested_msc(base, L):
    """MSC flat (WMC + SD's 4 base boards, raw systems) vs nested (Net2 of SD quotient + WMC): bisimilar"""
    fn = MB.flat_net('MSC')
    g = {'/'.join(p): (L[k]['Q'], pm) for p, k, pm in fn}
    S = A2.Net2(g, {e: e for e in MB.SPEC['MSC']['sides']}).explore()
    # bisimilarity of two systems = same class of the inits in the disjoint union
    U_states = [('f', s) for s in S.states] + [('n', s) for s in L['MSC']['raw'].states]
    T = {}
    for s in S.states:
        for p in S.ports:
            T[(('f', s), p)] = {(q, ('f', s2)) for q, s2 in S.T[(s, p)]}
    N = L['MSC']['raw']
    for s in N.states:
        for p in N.ports:
            T[(('n', s), p)] = {(q, ('n', s2)) for q, s2 in N.T[(s, p)]}
    U = K.System(S.ports, ('f', S.init), T, U_states)
    cls, _ = bisim(U)
    same = cls[('f', S.init)] == cls[('n', N.init)]
    print(f'  MSC flat (5 base boards, {len(S.states)} states) bisimilar to nested (SD quotient + WMC): {same}')
    return same


def flat_sd_direct():
    """A_core.explore of the whole drawn SD map (ext cells as ports X, Y; all base port cells LEAK)"""
    M = Map('SD')
    rows = [list(r) for r in M.rows]
    for e, (x, y) in M.ext.items():
        rows[y][x] = e
    leak = [P for _, k, cm in M.parts for (x, y), P in cm.items() if x < len(MB.BASE[k][y]) and MB.BASE[k][y][x].isupper()]
    b = LBoard([''.join(r) for r in rows], leak)
    t0 = time.time()
    C = K.explore(b, max_states=2000000)
    s, c, _, _ = K.check(C, BA.I_SD())
    cls, Q = bisim(C)
    print(f'  SD map explored directly (one A_core board, {len(b.cells)} cells, 14 boulders): {len(C.states)} states, '
          f'{len(Q.states)} bisimulation classes; vs ideal SD: SOUND {s} COMPLETE {c} ({time.time() - t0:.0f}s)')
    return s and c


# ============================================================ c. concrete play
class Play:
    """the full board + tracker"""
    def __init__(self, M, L, base, wiring, comp):
        self.M, self.L = M, L
        self.kind = M.kind
        leak = []
        self.copy_of = {}           # interior global cell -> path
        self.port_of = {}           # base port global cell -> (path, letter)
        self.loc = {}               # path -> {global cell: canonical cell}
        self.kb = {k: K.Board(MB.BASE[k]) for k in MB.BASE}
        self.pkind = {}
        for path, k, cm in M.parts:
            self.pkind[path] = k
            self.loc[path] = {}
            for (x, y), gc in cm.items():
                ch = MB.BASE[k][y][x] if x < len(MB.BASE[k][y]) else '#'
                if ch == '#':
                    continue
                self.loc[path][gc] = (x, y)
                if ch.isupper():
                    self.port_of[gc] = (path, ch)
                    leak.append(gc)
                else:
                    self.copy_of[gc] = path
        leak += list(M.ext.values())
        self.board = LBoard(M.rows, leak)
        self.B0 = self.board.b0
        self.extcell = {c: e for e, c in M.ext.items()}
        # flat node of every corridor component / base port cell
        node_of_comp = {}
        for path, (k, pm) in M.net.items():
            for p, v in pm.items():
                node_of_comp[wiring[path][p]] = v
        self.node_at = {c: node_of_comp[k] for c, k in comp.items()}
        for c, (path, p) in self.port_of.items():
            self.node_at[c] = M.net[path][1][p]
        # instance tree: path tuple -> kind; children; flat external node of each instance port
        self.inst = {(): self.kind}
        self.extnode = {(): {e: e for e in MB.SPEC[self.kind]['sides']}}
        todo = [()]
        while todo:
            ip = todo.pop()
            k = self.inst[ip]
            if k in MB.BASE:
                continue
            sp = MB.SPEC[k]
            for n, (ck, pm) in sp['parts'].items():
                cp = ip + (n,)
                self.inst[cp] = ck
                self.extnode[cp] = {p: (self.extnode[ip][v] if v in sp['sides'] else '/'.join(ip + (v,)))
                                    for p, v in pm.items()}
                todo.append(cp)
        # instances having flat node v as an external node
        self.ext_inst = {}
        for ip, d in self.extnode.items():
            if self.inst[ip] in MB.BASE or ip == ():
                continue
            for p, v in d.items():
                self.ext_inst.setdefault(v, []).append((ip, p))
        self.stats = dict(moves=0, base_trav=0, inst_trav=0, ext_ret=0, leaks=0)
        self.reset()

    def reset(self):
        self.B = self.B0
        self.h = None
        self.last_port = None        # (path, letter, local state) of the base traversal start
        self.inside = None
        self.pending = {}            # instance -> (port, projected state) at its last external visit
        self.touched = set()         # instances with a base traversal since their pending start
        self.iset = {self.L[self.kind]['I'].init}
        self.cur_node, self.dirty = None, False

    # ---- projections
    def lstate(self, path, B=None):
        B = self.B if B is None else B
        kb = self.kb[self.pkind[path]]
        bd = self.board
        return sum(1 << kb.idx[l] for g, l in self.loc[path].items() if B >> bd.idx[g] & 1)

    def proj(self, ip):
        """(raw level state, class) of instance ip in the current configuration"""
        k = self.inst[ip]
        if k in MB.BASE:
            s = self.lstate('/'.join(ip))
            return s, self.L[k]['cls'][s]
        sp = MB.SPEC[k]
        vec = tuple(self.proj(ip + (n,))[1] for n in sorted(sp['parts']))
        return vec, self.L[k]['cls'][vec]     # KeyError = a configuration outside the explored level system

    # ---- one move
    def place(self, cell):
        self.reset()
        self.h = self.board.idx[cell]
        self.at_node(cell)

    def jump(self, cell):
        """the hero leaves the board at an external port and re-enters at another one (the walk outside the board,
        in the rest of the level, is not part of this board): no reset of boulders, ideal states or pending
        instance traversals"""
        self.h = self.board.idx[cell]
        self.inside, self.last_port, self.cur_node = None, None, None
        self.at_node(cell)

    def step(self, h2, B2):
        assert (h2, B2) in set(self.board.moves(self.h, self.B)), 'illegal move'
        self.stats['moves'] += 1
        c = self.board.cells[h2]
        self.h, self.B = h2, B2
        if c in self.copy_of:
            assert self.inside in (None, self.copy_of[c]), 'walked between two copies without a port'
            assert self.last_port is not None and self.last_port[0] == self.copy_of[c], 'entered a copy not via a port'
            self.inside = self.copy_of[c]
            return
        if c in self.port_of:
            path, q = self.port_of[c]
            s2 = self.lstate(path)
            if self.inside is not None:
                assert self.inside == path, 'left a copy through a foreign port'
                p0, path0, s0 = self.last_port[1], self.last_port[0], self.last_port[2]
                S = self.L[self.pkind[path]]['raw']
                assert (q, s2) in S.T[(s0, p0)] or (q == p0 and s2 == s0), ('base traversal not in system', path, p0, q)
                self.stats['base_trav'] += 1
                self.dirty = True
                ipath = tuple(path.split('/'))
                for i in range(len(ipath)):
                    self.touched.add(ipath[:i])
            self.inside = None
            self.last_port = (path, q, s2)
        else:
            assert self.inside is None, 'left a copy interior without a port'
            self.last_port = None
        self.at_node(c)

    def at_node(self, c):
        """the hero stands on a cell of flat node v: every instance with v as an external node ends / starts a
        traversal there (checked against its level system; the board itself also against the ideal gadget)"""
        v = self.node_at.get(c)
        if v is None or (v == self.cur_node and not self.dirty and c not in self.extcell):
            return
        self.cur_node, self.dirty = v, False
        for ip, p in self.ext_inst.get(v, ()):
            st, cl = self.proj(ip)
            if ip in self.pending and ip in self.touched:
                p0, st0 = self.pending[ip]
                S = self.L[self.inst[ip]]['raw']
                assert (p, st) in S.T[(st0, p0)] or (p == p0 and st == st0),                     ('instance traversal not in its level system', ip, p0, p)
                self.stats['inst_trav'] += 1
            self.pending[ip] = (p, st)
            self.touched.discard(ip)
        if c in self.extcell:              # the board's own external port (frame cell): top-level traversal
            e = self.extcell[c]
            st, cl = self.proj_top()
            if 'top' in self.pending and () in self.touched:
                p0, st0 = self.pending['top']
                TS = self.L[self.kind]['top']['raw']
                assert (e, st) in TS.T[(st0, p0)] or (e == p0 and st == st0), ('board traversal not in its system', p0, e)
                I, Rs = self.L[self.kind]['I'], self.L[self.kind]['Rs']
                new = {a2 for a in self.iset for q2, a2 in I.T.get((a, p0), ()) if q2 == e and (cl, a2) in Rs}
                if e == p0:
                    new |= {a for a in self.iset if (cl, a) in Rs}
                assert new, ('external traversal with no SOUND-related ideal state', p0, e, self.iset)
                self.iset = new
                self.stats['ext_ret'] += 1
            self.pending['top'] = (e, st)
            self.touched.discard(())

    def proj_top(self):
        top = self.L[self.kind]['top']
        _, ccl = self.proj(())
        vec = tuple(ccl if n == 'core' else 'h' for n in top['net'].names)
        return vec, top['cls'][vec]

    # ---- walking helpers
    def corridor_walk(self, target):
        """BFS over non-interior cells (no pushes) from the hero to target cell"""
        bd = self.board
        start, goal = self.h, bd.idx[target]
        prev = {start: None}
        dq = deque([start])
        while dq:
            h = dq.popleft()
            if h == goal:
                break
            for h2, B2 in bd.moves(h, self.B):
                if B2 != self.B or h2 in prev or bd.cells[h2] in self.copy_of:
                    continue
                prev[h2] = h
                dq.append(h2)
        assert goal in prev, ('corridor walk: target not reachable', target)
        seq = []
        h = goal
        while h != start:
            seq.append(h)
            h = prev[h]
        for h2 in reversed(seq):
            self.step(h2, self.B)

    def base_trav(self, path, p, q, want_cls):
        """walk to the copy's port p, then a BFS inside the copy (canonical board) to port q ending in a class of
        want_cls; executed move by move on the full board"""
        k = self.pkind[path]
        kb = self.kb[k]
        inv = {l: g for g, l in self.loc[path].items()}
        self.corridor_walk(inv[kb.cells[kb.ports[p]]])
        s0 = self.lstate(path)
        start = (kb.ports[p], s0)
        prev = {start: None}
        dq = deque([start])
        hit = None
        cls = self.L[k]['cls']
        while dq:
            h, B = dq.popleft()
            for h2, B2 in kb.moves(h, B):
                st = (h2, B2)
                if st in prev:
                    continue
                prev[st] = (h, B)
                if kb.portmask >> h2 & 1:
                    if kb.portname[h2] == q and cls.get(B2) in want_cls:
                        hit = st
                        dq.clear()
                        break
                    continue
                dq.append(st)
        assert hit is not None, ('base traversal not realizable', path, p, q)
        seq = []
        st = hit
        while st != start:
            seq.append(st)
            st = prev[st]
        bd = self.board
        for h, B in reversed(seq):
            gB = self.B
            for i, (x, y) in enumerate(kb.cells):
                gi = bd.idx[inv[(x, y)]]
                gB = (gB | (1 << gi)) if B >> i & 1 else (gB & ~(1 << gi))
            self.step(bd.idx[inv[kb.cells[h]]], gB)

    def realize(self, ip, p, q, want_cls):
        """realize a traversal p -> q of instance ip ending in a class of want_cls (top-down planning)"""
        k = self.inst[ip]
        if k in MB.BASE:
            return self.base_trav('/'.join(ip), p, q, want_cls)
        lv = self.L[k]
        net = lv['net']
        names = net.names
        vec0, _ = self.proj(ip)
        start = (net.ext[p], vec0)
        goal = net.ext[q]
        prev, seen = {}, {start}
        dq = deque([start])
        hit = None
        while dq and hit is None:
            node, St = dq.popleft()
            for gi, port in net.at.get(node, []):
                sysm, pm = net.g[names[gi]]
                for q2, s2 in sysm.T[(St[gi], port)]:
                    S2 = St[:gi] + (s2,) + St[gi + 1:]
                    st = (pm[q2], S2)
                    act = (names[gi], port, q2, s2)
                    if pm[q2] == goal and lv['cls'][S2] in want_cls:
                        hit = ((node, St), act)
                        break
                    if st in seen:
                        continue
                    seen.add(st)
                    prev[st] = ((node, St), act)
                    if pm[q2] not in net.extnode:
                        dq.append(st)
                if hit is not None:
                    break
        assert hit is not None, ('level traversal not realizable', ip, p, q)
        cur, act = hit
        steps = [act]
        while cur != start:
            cur, act = prev[cur]
            steps.append(act)
        for child, cp, cq, cs2 in reversed(steps):
            self.realize(ip + (child,), cp, cq, {cs2})

    def ideal_step(self, p, q):
        """realize the ideal traversal p -> q from the current related state (COMPLETE relation on 'top')"""
        lv = self.L[self.kind]
        I, Rc, top = lv['I'], lv['Rc'], lv['top']
        _, cl = self.proj_top()
        for a in sorted(self.iset, key=str):
            for q2, a2 in I.T.get((a, p), ()):
                if q2 != q or (a, cl) not in Rc:
                    continue
                want = {c2 for q3, c2 in top['Q'].T[(cl, p)] if q3 == q and (a2, c2) in Rc}
                if want:
                    self.realize_top(p, q, want)
                    return a2
        raise AssertionError(('ideal step not available', p, q, self.iset))

    def realize_top(self, p, q, want_cls):
        """BFS in the top network (core + halls), then the core steps; hall steps are corridor walking"""
        top = self.L[self.kind]['top']
        net, names = top['net'], top['net'].names
        start = (net.ext[p], self.proj_top()[0])
        goal = net.ext[q]
        prev, seen = {}, {start}
        dq = deque([start])
        hit = None
        while dq and hit is None:
            node, St = dq.popleft()
            for gi, port in net.at.get(node, []):
                sysm, pm = net.g[names[gi]]
                for q2, s2 in sysm.T[(St[gi], port)]:
                    S2 = St[:gi] + (s2,) + St[gi + 1:]
                    st = (pm[q2], S2)
                    act = (names[gi], port, q2, s2)
                    if pm[q2] == goal and top['cls'][S2] in want_cls:
                        hit = ((node, St), act)
                        break
                    if st in seen:
                        continue
                    seen.add(st)
                    prev[st] = ((node, St), act)
                    if pm[q2] not in net.extnode:
                        dq.append(st)
                if hit is not None:
                    break
        assert hit is not None, ('board traversal not realizable', p, q)
        cur, act = hit
        steps = [act]
        while cur != start:
            cur, act = prev[cur]
            steps.append(act)
        for child, cp, cq, cs2 in reversed(steps):
            if child == 'core':
                self.realize((), cp, cq, {cs2})
        self.corridor_walk(self.M.ext[q])


def scripted(M, PL, log=print):
    ok = True
    for script in SCRIPTS[M.kind]:
        PL.place(M.ext[script[0][0]])
        m0 = PL.stats['moves']
        for p, q in script:
            if PL.node_at.get(PL.board.cells[PL.h]) != p:
                PL.jump(M.ext[p])
            PL.ideal_step(p, q)
        log(f'  c1 {M.kind} script {" ".join(f"{p}->{q}" for p, q in script)}: realized, {PL.stats["moves"] - m0} moves, '
            f'ideal states now {sorted(PL.iset)}')
    return ok


def random_play(M, PL, nmoves, rng, ep_len=4000, log=print):
    done = 0
    eps = 0
    exts = list(M.ext)
    while done < nmoves:
        PL.place(M.ext[rng.choice(exts)])
        eps += 1
        extc = set(M.ext.values())
        for _ in range(ep_len):
            if PL.board.cells[PL.h] in extc and rng.random() < 0.2:      # leave and re-enter elsewhere
                PL.jump(M.ext[rng.choice(exts)])
                PL.stats['jumps'] = PL.stats.get('jumps', 0) + 1
            mv = list(PL.board.moves(PL.h, PL.B))
            if not mv:
                break
            h2, B2 = rng.choice(mv)
            PL.step(h2, B2)
            done += 1
            if done >= nmoves:
                break
    log(f'  c2 {M.kind}: {done} random moves in {eps} episodes; tracker: {PL.stats}')
    return True


def main():
    args = sys.argv[1:]
    want = [a for a in args if a in MB.SPEC] or MB.ORDER
    nmoves = int(args[args.index('--moves') + 1]) if '--moves' in args else 30000
    seed = int(args[args.index('--seed') + 1]) if '--seed' in args else 7
    ok = True
    t0 = time.time()
    print('== 0. base boards, model symmetry')
    base = {k: K.explore(K.Board(r)) for k, r in MB.BASE.items()}
    ok &= check_symmetry(base)
    print('== w. M_build.SPEC vs the wiring of B2_ani\'s composition functions')
    ok &= check_spec()
    print('== b. exact port behaviour (bottom-up, bisimulation quotients)')
    L = level_systems(base, want=want)
    for k in MB.ORDER:
        if k in L and 'sound' in L[k]:
            ok &= L[k]['sound'] and L[k]['complete']
    if 'MSC' in L:
        ok &= flat_vs_nested_msc(base, L)
    if '--flat-sd' in args:
        ok &= flat_sd_direct()
    rng = random.Random(seed)
    for kind in want:
        print(f'== a. {kind}: map checks')
        M = Map(kind)
        wiring, extk, comp, ncomp, tiles = check_map(M)
        reach = boulder_reach(M, base, tiles)
        print(f'  {kind}: {M.W} x {M.H}, {sum(r.count("0") for r in M.rows)} boulders, {len(M.parts)} base copies '
              f'{M.J["counts"]}; copies = canonical boards under one symmetry each; check_map ok ({ncomp} corridors, '
              f'flat wiring == flattened network); boulder reach {reach} cells, inside the copies, off all ports')
        for t in range(1, 8):
            Mt = Map(kind, t)
            check_map(Mt)
        print(f'  {kind}: all 7 other grid-symmetric images pass the same checks')
        PL = Play(M, L, base, wiring, comp)
        print(f'== c. {kind}: concrete play on the full board')
        ok &= scripted(M, PL)
        PL.stats = {k: 0 for k in PL.stats}
        ok &= random_play(M, PL, nmoves, rng)
        print(f'  ({time.time() - t0:.0f}s)')
    print('ALL AS EXPECTED' if ok else 'SOME UNEXPECTED RESULT')
    return ok


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
