#!/usr/bin/env python3
"""animate_gadgets.py -- animated walk-throughs of every gadget we have, drawn with NetHack's own tiles.

Every hero move is computed, never hand-written: shortest walks found by BFS over (hero cell, boulder set, hole set)
with the exact movement model of tools/exptime/A_core.py (Sokoban rules, heavy hero, corner rule). For the boulder-only
gadgets every step of every walk is re-checked against A_core.Board.moves itself. The two NP-proof gadgets with holes
(G_X) use the same rules plus hu-on-lower F1/F4 (a boulder pushed onto a hole plugs it; stepping into a hole = loss),
exactly as tools/gen_on_instance.py's Sim. The teleport coin is the only non-push event (nature's move), drawn as one
frame per outcome.

Each animation asserts that its final state is the intended one (boulder positions, hero port) and, where a gadget
system exists (A_core.explore / A2_scd networks), that the realised traversal is a transition of that system.

Outputs: media/exptime/anim/<id>.gif (+ contact_sheet.png) and site/paper/engine/anims_exptime.json (the same frames,
for the page's Text/Tiles grid player in exptime.js).
Usage: python tools/visual/animate_gadgets.py [--only id,id] [--no-gif]
"""
import heapq, json, os, sys
from collections import deque

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools', 'exptime'))
import A_core as K
import A_library as LIB
import A2_scd as S2
from tiles import load_all
from PIL import Image, ImageDraw, ImageFont

DIRN = {(1, 0): 'east', (-1, 0): 'west', (0, -1): 'north', (0, 1): 'south',
        (1, -1): 'NE', (-1, -1): 'NW', (1, 1): 'SE', (-1, 1): 'SW'}
GREEK = 'αβγδεζηθ'
MOVE_MS, PUSH_MS, HEAD_MS, NOPE_MS, END_MS = 220, 300, 1500, 1500, 2600


# ====================================================================== gadget + exact movement model
class Gadget:
    """rows: '#' wall, '.' floor, '0' boulder, '^' hole, 'A'-'Z' port, 'a'-'z' named floor.
    labels: extra display labels {(x,y): text}; tele: cells drawn as a teleportation trap (floor for movement)."""

    def __init__(self, rows, labels=None, tele=(), names=None):
        self.rows = rows
        self.board = K.Board([r.replace('^', '.') for r in rows])
        bd = self.board
        self.holes0 = 0
        for y, r in enumerate(rows):
            for x, ch in enumerate(r):
                if ch == '^':
                    self.holes0 |= 1 << bd.idx[(x, y)]
        self.has_holes = bool(self.holes0)
        self.labels = dict(labels or {})
        self.tele = set(tele)
        self.H, self.W = bd.H, bd.W
        # boulder names by initial cell
        cells0 = [bd.cells[i] for i in range(len(bd.cells)) if bd.b0 >> i & 1]
        self.names0 = dict(names) if names else {c: GREEK[k] for k, c in enumerate(cells0)}
        assert set(self.names0) == set(cells0), (self.names0, cells0)

    def cell(self, i):
        return self.board.cells[i]

    def port(self, p):
        return self.board.ports[p]

    def bset(self, B):
        return {self.board.cells[i] for i in range(len(self.board.cells)) if B >> i & 1}

    def mask(self, cells):
        return sum(1 << self.board.idx[c] for c in cells)

    def moves(self, h, B, H):
        """same rules as A_core.Board.moves (no LEAK check: NP gadgets may push into their ports) + holes."""
        bd = self.board
        for t, b in bd.orth[h]:
            if B >> t & 1:
                if b < 0 or B >> b & 1:
                    continue
                if H >> b & 1:                         # F1: boulder plugs the hole, both vanish
                    yield t, B & ~(1 << t), H & ~(1 << b)
                else:
                    yield t, (B & ~(1 << t)) | (1 << b), H
            elif H >> t & 1:                           # F4: entering a hole = loss (never taken)
                continue
            else:
                yield t, B, H
        for t, cm in bd.diag[h]:
            if B >> t & 1 or H >> t & 1:
                continue
            if cm & ~B:                                # a hole is not bad rock (F3)
                yield t, B, H

    def check_core(self, s0, s1):
        """re-check one step against A_core.Board.moves (boulder-only gadgets)."""
        if self.has_holes or s0[2] or s1[2]:
            return
        try:
            legal = set(self.board.moves(s0[0], s0[1]))
        except K.LeakError:
            return                                   # NP gadget whose port could take a boulder elsewhere
        assert (s1[0], s1[1]) in legal, ('step not legal in A_core', self.board.show(s0[1], s0[0]))

    # ---------------- searches
    def walk(self, start, goal, through=(), ok=None, limit=3_000_000):
        """shortest walk start -> state with goal(state); never enters a port cell except through-ports or the goal."""
        bd = self.board
        through = {bd.ports[p] for p in through}
        prev = {start: None}
        dq = deque([start])
        while dq:
            s = dq.popleft()
            if s != start and goal(s):
                path = [s]
                while prev[path[-1]] is not None:
                    path.append(prev[path[-1]])
                path.reverse()
                for a, b in zip(path, path[1:]):
                    self.check_core(a, b)
                return path
            if s != start and bd.portmask >> s[0] & 1 and s[0] not in through:
                continue                              # standing on a port ends the traversal
            for t in self.moves(*s):
                if t in prev:
                    continue
                if bd.portmask >> t[0] & 1 and t[0] not in through and not goal(t):
                    continue
                if ok and not ok(t):
                    continue
                prev[t] = s
                dq.append(t)
                if len(prev) > limit:
                    raise RuntimeError('walk: search too big')
        raise AssertionError('walk: goal unreachable')

    def reach(self, start, ok=None):
        bd = self.board
        seen = {start: None}
        dq = deque([start])
        entered = set()
        while dq:
            s = dq.popleft()
            for t in self.moves(*s):
                if bd.portmask >> t[0] & 1:
                    entered.add(bd.portname[t[0]])
                    continue
                if t in seen or (ok and not ok(t)):
                    continue
                seen[t] = s
                dq.append(t)
        return seen, entered

    def empty_dist(self, q):
        """8-neighbour distance to port q over non-wall cells, ignoring boulders and holes."""
        bd = self.board
        dist = {bd.ports[q]: 0}
        dq = deque([bd.ports[q]])
        while dq:
            a = dq.popleft()
            for t, _ in bd.orth[a] + bd.diag[a]:
                if t not in dist:
                    dist[t] = dist[a] + 1
                    dq.append(t)
        return dist

    def why_not(self, s, d, names):
        """caption for an illegal move from state s in direction d, or None if the move is legal."""
        h, B, H = s
        x, y = self.cell(h)
        tx, ty = x + d[0], y + d[1]
        bd = self.board
        t = bd.idx.get((tx, ty))
        dn = DIRN[d]

        def what(c):
            i = bd.idx.get(c)
            if i is None:
                return 'wall'
            if B >> i & 1:
                return 'boulder ' + names.get(c, '?')
            return 'free'
        if t is None:
            return f'step {dn}: wall'
        if d[0] and d[1]:
            if B >> t & 1:
                return f'diagonal step {dn} into {names.get((tx, ty), "a boulder")}: no diagonal pushes, blocked'
            if H >> t & 1:
                return f'diagonal step {dn} onto the hole: falling = loss, refused'
            c1, c2 = what((tx, y)), what((x, ty))
            if c1 != 'free' and c2 != 'free':
                return f'diagonal {dn}: blocked, Sokoban level, no squeeze between {c1} + {c2}'
            return None
        if B >> t & 1:
            b = bd.idx.get((tx + d[0], ty + d[1]))
            n = names.get((tx, ty), '?')
            if b is None:
                return f'push {n} {dn}: blocked (wall behind)'
            if B >> b & 1:
                return f'push {n} {dn}: blocked (boulder {names.get((tx + d[0], ty + d[1]), "?")} behind)'
            return None
        if H >> t & 1:
            return f'step {dn} onto the hole: falling = loss, refused'
        return None


# ====================================================================== story (frames)
class Story:
    def __init__(self, aid, title, g, sub=''):
        self.id, self.title, self.g, self.sub = aid, title, g, sub
        self.frames = []
        self.state = None
        self.names = dict(g.names0)
        self.phase = ''
        self.result = {}

    def _f(self, cap, dur, nope=None, flash=None):
        h, B, H = self.state
        self.frames.append(dict(h=h, B=B, H=H, cap=cap, dur=dur, phase=self.phase, nope=nope, flash=flash,
                                names=dict(self.names)))

    def set(self, state, names=None):
        self.state = state
        if names is not None:
            self.names = dict(names)
        else:
            assert self.g.bset(state[1]) == set(self.names), 'boulder names out of sync'

    def head(self, phase, cap, dur=HEAD_MS):
        self.phase = phase
        self._f(cap, dur)

    def note(self, cap, dur=HEAD_MS, flash=None):
        self._f(cap, dur, flash=flash)

    def play(self, path, last=None):
        assert path[0] == self.state
        for a, b in zip(path, path[1:]):
            cap, push = self.describe(a, b)
            self.state = b
            if b is path[-1] and last:
                cap = cap + '. ' + last
            self._f(cap, PUSH_MS if push else MOVE_MS)

    def describe(self, a, b):
        g = self.g
        (x0, y0), (x1, y1) = g.cell(a[0]), g.cell(b[0])
        d = (x1 - x0, y1 - y0)
        dn = DIRN[d]
        if a[1] != b[1]:
            n = self.names.pop((x1, y1))
            if a[2] != b[2]:
                return f'push {n} {dn} into the hole: the hole is plugged', True
            self.names[(x1 + d[0], y1 + d[1])] = n
            return f'push {n} {dn}', True
        port = g.board.portname.get(b[0])
        lab = g.labels.get((x1, y1))
        to = f' onto {port}' if port else (f' to {lab}' if lab else '')
        return (f'diagonal step {dn}' if d[0] and d[1] else f'step {dn}') + to, False

    def refuse(self, q, ok=None, intro=None, maxn=3):
        """the hero tries to reach port q from the current state and cannot: walk to the closest reachable spot,
        then show every illegal move there that would head for q. Asserts q is unreachable."""
        g = self.g
        seen, entered = g.reach(self.state, ok)
        assert q not in entered, f'refused traversal to {q} is actually possible'
        dist = g.empty_dist(q)
        best = min(seen, key=lambda s: (dist.get(s[0], 999), self._steps(seen, s)))
        path = [best]
        while seen[path[-1]] is not None:
            path.append(seen[path[-1]])
        path.reverse()
        for a, b in zip(path, path[1:]):
            g.check_core(a, b)
        if intro:
            self.note(intro, 1000)
        self.play(path)
        h = best[0]
        x, y = g.cell(h)
        dh = dist.get(h, 999)
        cands = []
        for d in DIRN:
            t = g.board.idx.get((x + d[0], y + d[1]))
            if t is None or dist.get(t, 999) > dh + 1:
                continue
            why = g.why_not(best, d, self.names)
            if why:
                cands.append((dist[t], why, (x + d[0], y + d[1])))
        cands.sort()
        assert cands, 'refusal: no blocked move to show'
        for _, why, c in cands[:maxn]:
            self._f(why, NOPE_MS, nope=c)
        self._f(f'No way through to {q}: refused.', NOPE_MS)

    @staticmethod
    def _steps(seen, s):
        n = 0
        while seen[s] is not None:
            s = seen[s]
            n += 1
        return n

    def jump(self, port, cap):
        h = self.g.port(port)
        self.state = (h, self.state[1], self.state[2])
        self._f(cap, 1100)

    def end(self, cap):
        self.phase = 'Result'
        self._f(cap, END_MS)


def st(g, port, B=None, H=None):
    return (g.port(port), g.board.b0 if B is None else B, g.holes0 if H is None else H)


def at_port(g, p, pred=None):
    i = g.port(p)
    return lambda s: s[0] == i and (pred is None or pred(s))


# ====================================================================== the animations
def anim_gd():
    g = Gadget(LIB.GD_ROWS, names={(3, 1): 'κ'})
    S = Story('np_gd', 'G_D one-way door (NP proof, single use)', g, 'hu-on-lower §3.3, Lemma 3.3')
    C = K.explore(g.board)
    S.set(st(g, 'Q'))
    S.head('Closed, from the exit side', 'Door boulder κ sits between e and the exit q. Hero enters at Q.')
    S.refuse('E', intro='Try to get from Q back to E.')
    S.jump('E', 'Hero goes round to the entry E.')
    S.head('Open it from E', 'From e, push κ east into the dead-end pocket.')
    p = g.walk(S.state, at_port(g, 'Q'))
    S.play(p, 'Open: κ is stuck in the pocket for good')
    B1 = S.state[1]
    assert g.bset(B1) == {(4, 1)}, 'G_D: κ must end in the pocket'
    assert ('Q', B1) in C.T[(g.board.b0, 'E')]
    S.head('Open for good', 'Now walk back from Q to E: nothing stops the hero.')
    p = g.walk(S.state, at_port(g, 'E', lambda s: s[1] == B1))
    S.play(p)
    assert ('E', B1) in C.T[(B1, 'Q')]
    S.end('Works once, then it is open both ways: fine for NP (each door used once), useless for EXPTIME.')
    return S


def anim_gc():
    rows = ["##P#R#",
            "##t#.#",
            "##0..#",
            "K.q###",
            "##.###",
            "##c..F",
            "######"]
    g = Gadget(rows, labels={(2, 1): 'T', (2, 2): 'N', (2, 3): 'Q', (2, 5): 'C'}, names={(2, 2): 'W'})
    S = Story('np_gc', 'G_C forced closing site (NP proof)', g, 'hu-on-lower §3.2, Lemma 3.2')
    S.set(st(g, 'K'))
    S.head('σ open: the clause path passes', 'Clause path σ enters at K (back segment) and leaves at F. W waits on N.')
    p = g.walk(S.state, at_port(g, 'F', lambda s: s[1] == g.board.b0))
    S.play(p, 'σ is passable')
    S.jump('P', 'Now the variable branch: the hero walks the P lane from P.')
    S.head('The P branch must close σ', 'The only way from P to R: push W south from T into Q.')
    p = g.walk(S.state, at_port(g, 'R'))
    S.play(p, 'σ closed')
    B1 = S.state[1]
    assert g.bset(B1) == {(2, 3)}, 'G_C: W must end on Q'
    # forced: R is unreachable from P without moving W into Q
    seen, entered = g.reach(st(g, 'P'), ok=lambda s: s[1] == g.board.b0)
    assert 'R' not in entered, 'G_C: P->R possible without the closing push'
    S.jump('K', 'Back on the clause path at K.')
    S.head('σ closed: the clause path is blocked', 'W on Q blocks the turn at Q (Lemma 2.2).')
    S.refuse('F')
    S.end('Walking a branch closes every clause path of the opposite literal. Closed stays closed.')
    return S


def anim_gx():
    rows = ["#######",
            "K..0p##",
            "###0###",
            "W..s..E",
            "###^###",
            "###.###",
            "###L###"]
    g = Gadget(rows, labels={(4, 1): 'p', (3, 3): 'S'}, names={(3, 1): 'δ', (3, 2): 'τ'})
    S = Story('np_gx', 'G_X crossover, K over P (NP proof, single use)', g, 'hu-on-lower §3.5, Lemma 3.5')
    S.set(st(g, 'W'))
    S.head('P passes, any number of times', 'The P lane runs W to E through S; boulder τ and the hole guard the K line.')
    p = g.walk(S.state, at_port(g, 'E', lambda s: s[1] == g.board.b0))
    S.play(p)
    S.jump('W', 'Again from W: can P slip into the K line?')
    S.head('P cannot enter K', 'Above S: τ with δ behind it. Below S: the hole.')
    S.refuse('L')
    S.jump('K', 'The clause path K arrives from the left.')
    S.head('K passes once', 'Push δ into the pocket p, then push the token τ down into the hole.')
    p = g.walk(S.state, at_port(g, 'L'))
    S.play(p, 'K crossed P')
    assert g.bset(S.state[1]) == {(4, 1)} and S.state[2] == 0, 'G_X: δ in pocket, τ used up, hole plugged'
    S.end('One token per crossover: K crosses once, P crosses forever. Single use, so not for EXPTIME.')
    return S


def diode_display():
    rows = ["#A#B##",
            "#.0..#",
            "##c#d#",
            "##...#",
            "######"]
    return Gadget(rows, labels={(2, 2): 'C', (4, 2): 'D'}, names={(2, 1): 'X'})


def anim_diode_use():
    g = diode_display()
    raw = K.Board(LIB.PROTODIODE)
    C = K.explore(raw)
    S = Story('diode_use', 'Checkable diode: intended use A→B', g, 'Ani et al. protodiode; A-gadgets §3')
    S.set(st(g, 'A'))
    S.head('A to B', 'X on m1. C and D are joined by a free corridor (drawn here).')
    p = g.walk(S.state, at_port(g, 'B', lambda s: s[1] == g.board.b0))
    S.play(p, 'X is back on m1: same state, reusable')
    # the two legs are A->C and D->B of the raw protodiode
    mid = [s for s in p if g.cell(s[0]) == (2, 2)]
    assert mid, 'diode walk must pass C'
    Bm = mid[0][1]
    m2 = 1 << raw.idx[(3, 1)]
    assert g.bset(Bm) == {(3, 1)}
    assert ('C', m2) in C.T[(raw.b0, 'A')] and ('B', raw.b0) in C.T[(m2, 'D')]
    S.end('Checks A→C then D→B pass: the diode is clean. B→A never works from a clean state.')
    return S


def leak_search(g, src, dst, ok=None, jump_cost=3):
    """shortest play (moves; port-to-port jumps outside the gadget cost jump_cost) that ends with a traversal
    src -> dst starting at src. Returns list of (state, kind) with kind in {'start','move','jump','leak'}."""
    bd = g.board
    ports = list(bd.ports.values())
    start = [((bd.ports[p], bd.b0, g.holes0), 0) for p in bd.ports]
    dist, prev = {}, {}
    pq = []
    for s, m in start:
        dist[(s, m)] = 0
        prev[(s, m)] = None
        heapq.heappush(pq, (0, s, m))
    srci, dsti = bd.ports[src], bd.ports[dst]
    while pq:
        dcur, s, m = heapq.heappop(pq)
        if dist.get((s, m)) != dcur:
            continue
        if m == 1 and s[0] == dsti:
            out = []
            k = (s, m)
            while k is not None:
                pk = prev[k]
                kind = 'start' if pk is None else pk[1]
                out.append((k, kind))
                k = pk[0] if pk else None
            out.reverse()
            return [(k[0], k[1], kind) for k, kind in out]
        nxt = []
        if m == 0 and s[0] == srci:
            nxt.append(((s, 1), 0, 'leak'))
        if m == 0 and bd.portmask >> s[0] & 1:
            for q in ports:
                if q != s[0]:
                    nxt.append((((q, s[1], s[2]), 0), jump_cost, 'jump'))
        for t in g.moves(*s):
            if m == 1 and bd.portmask >> t[0] & 1 and t[0] != dsti:
                continue
            if ok and not ok(t):
                continue
            nxt.append(((t, m), 1, 'move'))
        for key, c, kind in nxt:
            nd = dcur + c
            if nd < dist.get(key, 1 << 30):
                dist[key] = nd
                prev[key] = ((s, m), kind)
                heapq.heappush(pq, (nd, key[0], key[1]))
    raise AssertionError('no leak found')


def play_leak(S, seq, setup_cap):
    g = S.g
    S.set(seq[0][0])
    S.head('Set-up', setup_cap)
    i = 1
    while i < len(seq):
        s, m, kind = seq[i]
        if kind == 'jump':
            port = g.board.portname[s[0]]
            S.jump(port, f'(outside the gadget) the hero walks round to {port}.')
        elif kind == 'leak':
            S.head('The leak', f'Now enter at the exit {g.board.portname[s[0]]} and walk backwards.')
        else:
            path = [S.state]
            while i < len(seq) and seq[i][2] == 'move':
                path.append(seq[i][0])
                i += 1
            for a, b in zip(path, path[1:]):
                g.check_core(a, b)
            S.play(path)
            continue
        i += 1


def anim_diode_break():
    g = diode_display()
    S = Story('diode_break', 'Checkable diode: how it breaks (overshoot)', g, 'A-gadgets §3, overshoot lemma §4')
    seq = leak_search(g, 'B', 'A')
    play_leak(S, seq, 'X on m1. Find the shortest way to make B→A possible.')
    Bf = S.state[1]
    assert g.bset(Bf) == {(4, 1)}, 'diode break: X must end on e2 (overshoot)'
    assert S.state[0] == g.port('A')
    raw = K.Board(LIB.PROTODIODE)
    C = K.explore(raw)
    e2 = 1 << raw.idx[(4, 1)]
    assert ('A', e2) in C.T[(e2, 'B')]
    S.end('Overshoot: X stuck on e2 for good, B→A open. Broken is absorbing; the final check path catches it.')
    return S


def anim_negative(key, rows, title, intended=True):
    g = Gadget(rows)
    C = K.explore(g.board)
    S = Story(key + '_break', title, g, 'A_library NEGATIVE; A-gadgets §4')
    if intended:
        S.set(st(g, 'A'))
        S.head('Intended use', 'Go A→B and put the boulder back.')
        try:
            p = g.walk(S.state, at_port(g, 'B', lambda s: s[1] == g.board.b0))
            S.play(p, 'back to the start state')
        except AssertionError:
            p = g.walk(S.state, at_port(g, 'B'))
            S.play(p, 'A→B works')
        S.note('Reset to the start position.', 900)
    seq = leak_search(g, 'B', 'A')
    S.set(seq[0][0], names=g.names0)
    play_leak(S, seq[0:], 'Start position. Find the shortest play that opens B→A.')
    assert S.state[0] == g.port('A')
    # the leak state is reachable in A_core's gadget system and allows B->A there
    lk = [k for k, (s, m, kind) in enumerate(seq) if kind == 'leak'][0]
    Bl = seq[lk][0][1]
    assert Bl in C.states and any(q == 'A' for q, _ in C.T[(Bl, 'B')]), 'leak not confirmed by A_core'
    S.end('Unsound: a diode must never allow B→A. This is the counterexample.')
    return S


# ---------------- A2 pieces
PP_ROWS = S2.PROTO_PRECURSOR


def pp_clean():
    bp = K.Board(PP_ROWS)
    Cp = K.explore(bp)
    clean, _, _, Pp = S2.postselect_L(Cp, S2.PP_CHECKS, S2.PP_L)
    return bp, Cp, clean, Pp


def track_x(g, B, y):
    return tuple(sorted(x for (x, yy) in g.bset(B) if yy == y))


def anim_proto_precursor():
    g = Gadget(PP_ROWS, names={(4, 2): 'α', (6, 2): 'β'})
    bp, Cp, clean, Pp = pp_clean()
    S = Story('pp_checks', 'Proto-precursor (Ani et al. Fig. 36a): the four checks', g, 'A2-scd §1-2')
    S.set(st(g, 'A'))
    S.head('Checks A→D, C→G, B→A, B→C', 'Blocks α, β on the track. A clean state passes all four checks in order.')
    B = g.board.b0
    checks = S2.PP_CHECKS
    for k, (p, q) in enumerate(checks):
        if g.port(p) != S.state[0]:
            S.jump(p, f'(outside) to {p} for check {k + 1}.')
        rest = checks[k + 1:]
        S.head(f'Check {k + 1}: {p}→{q}', f'Traverse from {p} to {q}.', 900)
        path = g.walk(S.state, at_port(g, q, lambda s, rest=rest: K.check_legal(Cp, s[1], rest)))
        S.play(path, f'check {p}→{q} passed')
        assert (q, S.state[1]) in Cp.T[(B, p)]
        B = S.state[1]
    assert Cp.init in clean
    S.end('All four checks legal: the start state is clean. Broken states fail some check and stay broken.')
    return S


JOINED = ["####T#####",
          "##......##",
          "##a#b##c##",
          "##.#..#.##",
          "#...0.0..#",
          "#.#.##.#.#",
          "#d#E##F#g#"]
JLAB = {(2, 2): 'A', (4, 2): 'B', (7, 2): 'C', (1, 6): 'D', (8, 6): 'G'}


def blocks_of(g, B, y=4):
    return track_x(g, B, y)


def mk_blocks(g, xs, y=4):
    return g.mask([(x, y) for x in xs])


def pp_state(bp, xs):
    return sum(1 << bp.idx[(x, 2)] for x in xs)


def anim_precursor():
    g = Gadget(JOINED, labels=JLAB, names={(4, 4): 'α', (6, 4): 'β'})
    bp, Cp, clean, Pp = pp_clean()
    okx = {S2.track(bp, s, 2) for s in clean}
    ok = lambda s: blocks_of(g, s[1]) in okx
    N = S2.net({'p': (S2.with_init(Pp, pp_state(bp, (4, 6))), {'A': 'T', 'B': 'T', 'C': 'T', 'E': 'E', 'F': 'F'})},
               ['T', 'E', 'F']).explore()
    S = Story('precursor', 'Precursor (Fig. 36c/d): A, B, C joined to T', g, 'A2-scd §2')
    S.set(st(g, 'T'))
    S.head('State 1 (α on 4, β on 6)', 'T↔E is free. Going T→F switches to state 2.')
    p = g.walk(S.state, at_port(g, 'F', lambda s: blocks_of(g, s[1]) == (3, 5)), through=['T'], ok=ok)
    S.play(p, 'state 2 (α on 3, β on 5)')
    assert ('F', (pp_state(bp, (3, 5)),)) in S2.closure_rel(N, (pp_state(bp, (4, 6)),), 'T')
    S.jump('T', '(outside) back to T.')
    S.head('State 2', 'Now T↔F is free and T→E switches back to state 1.')
    p = g.walk(S.state, at_port(g, 'E', lambda s: blocks_of(g, s[1]) == (4, 6)), through=['T'], ok=ok)
    S.play(p, 'state 1 again')
    assert ('E', (pp_state(bp, (4, 6)),)) in S2.closure_rel(N, (pp_state(bp, (3, 5)),), 'T')
    S.end('A switch: which side of T is open flips each time you go to the closed side. Verified sound + complete.')
    return S


def anim_toggle():
    rows = ["#" * 10] + JOINED[1:]
    g = Gadget(rows, labels=JLAB, names={(4, 4): 'α', (6, 4): 'β'})
    bp, Cp, clean, Pp = pp_clean()
    okx = {S2.track(bp, s, 2) for s in clean}
    ok = lambda s: blocks_of(g, s[1]) in okx
    N = S2.net({'p': (S2.with_init(Pp, pp_state(bp, (4, 6))), {'A': 'tT', 'B': 'tT', 'C': 'tT', 'E': 'E', 'F': 'F'})},
               ['E', 'F']).explore()
    S = Story('toggle', '1-toggle = precursor with T closed', g, 'A2-scd §2-3')
    S.set(st(g, 'E'))
    S.head('State r: E→F', 'The top junction is closed off; only E and F lead outside.')
    p = g.walk(S.state, at_port(g, 'F', lambda s: blocks_of(g, s[1]) == (3, 5)), ok=ok)
    S.play(p, 'now state l')
    sr, sl = (pp_state(bp, (4, 6)),), (pp_state(bp, (3, 5)),)
    assert ('F', sl) in N.T[(sr, 'E')]
    S.jump('E', '(outside) back to E.')
    S.head('State l: E→F again?', 'The toggle points the other way now.')
    S.refuse('F', ok=ok)
    S.jump('F', '(outside) round to F.')
    S.head('State l: F→E', 'Going back flips it to r.')
    p = g.walk(S.state, at_port(g, 'E', lambda s: blocks_of(g, s[1]) == (4, 6)), ok=ok)
    S.play(p, 'state r again')
    assert ('E', sr) in N.T[(sl, 'F')]
    assert not any(q == 'F' for q, _ in N.T[(sl, 'E')])
    S.end('A 1-toggle: one pass each way, alternately. Verified sound + complete.')
    return S


# ---------------- flat self-closing door (Fig. 37 = precursor + 1-toggle + 2 diodes, 6 boulders)
PP_LOCAL = ["##a#b##c##", "##.#..#.##", "#...0.0..#", "#.#.##.#.#", "#d#e##f#g#"]
PD_LOCAL = ["#a#b##", "#.0..#", "##c#d#"]
SCD_W, SCD_H = 17, 20
SCD_PARTS = {'tog': (PP_LOCAL, 0, 1), 'prec': (PP_LOCAL, 5, 8), 'd1': (PD_LOCAL, 5, 15), 'd2': (PD_LOCAL, 10, 15)}
SCD_CORR = {   # corridor -> (cells, component port cells it must touch)
    'tT': ([(x, 0) for x in range(2, 8)], {('tog', 'a'), ('tog', 'b'), ('tog', 'c')}),
    'T': ([(6, 6)] + [(x, 7) for x in range(6, 13)], {('tog', 'f'), ('prec', 'a'), ('prec', 'b'), ('prec', 'c')}),
    'O': ([(3, 6), (3, 7)], {('tog', 'e')}),
    'X': ([(8, 13), (8, 14)], {('prec', 'e'), ('d1', 'b')}),
    'Y': ([(11, 13), (11, 14)], {('prec', 'f'), ('d2', 'a')}),
    'I': ([(4, 14), (5, 14), (6, 14)], {('d1', 'a')}),
    'J': ([(13, 14), (14, 14), (15, 14)], {('d2', 'b')}),
    'cd1': ([(7, 18), (8, 18), (9, 18)], {('d1', 'c'), ('d1', 'd')}),
    'cd2': ([(12, 18), (13, 18), (14, 18)], {('d2', 'c'), ('d2', 'd')}),
}
SCD_PORTS = {'O': (3, 7), 'I': (4, 14), 'J': (15, 14)}


def scd_build():
    grid = [['#'] * SCD_W for _ in range(SCD_H)]
    owner, portcell = {}, {}
    for name, (loc, ox, oy) in SCD_PARTS.items():
        for y, r in enumerate(loc):
            for x, ch in enumerate(r):
                if ch == '#':
                    continue
                c = (ox + x, oy + y)
                assert c not in owner, ('overlap', c)
                owner[c] = name
                grid[c[1]][c[0]] = '0' if ch == '0' else '.'
                if ch.isalpha():
                    portcell[c] = (name, ch)
    for cname, (cells, _) in SCD_CORR.items():
        for c in cells:
            assert c not in owner, ('overlap', c)
            owner[c] = 'corr:' + cname
            grid[c[1]][c[0]] = '.'
    for p, (x, y) in SCD_PORTS.items():
        grid[y][x] = p
    rows = [''.join(r) for r in grid]
    # adjacency check: different components never 8-touch; each corridor touches exactly its designated port cells
    touch = {}
    for (x, y), o in owner.items():
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                c2 = (x + dx, y + dy)
                if (dx or dy) and c2 in owner and owner[c2] != o:
                    a, b = o, owner[c2]
                    assert a.startswith('corr:') or b.startswith('corr:'), ('components touch', (x, y), c2)
                    if a.startswith('corr:') and not b.startswith('corr:'):
                        touch.setdefault(a[5:], set()).add(portcell.get(c2, (b, 'interior')))
                    assert not (a.startswith('corr:') and b.startswith('corr:')), ('corridors touch', (x, y), c2)
    for cname, (_, want) in SCD_CORR.items():
        assert touch.get(cname, set()) == want, ('corridor attaches wrongly', cname, touch.get(cname), want)
    return rows, owner


def scd_gadget():
    rows, owner = scd_build()
    labels = {(9, 7): 'T', (8, 12): 'E', (11, 12): 'F'}
    names = {(4, 3): 'α', (6, 3): 'β', (9, 10): 'γ', (11, 10): 'δ', (7, 16): 'X1', (12, 16): 'X2'}
    g = Gadget(rows, labels=labels, names=names)
    return g


def scd_comp(g, B):
    """flat boulder set -> local block positions per component (x offsets local)."""
    cs = g.bset(B)
    out = {}
    for name, (loc, ox, oy) in SCD_PARTS.items():
        ty = oy + (2 if name in ('tog', 'prec') else 1)
        out[name] = tuple(sorted(x - ox for (x, y) in cs if y == ty and ox <= x < ox + len(loc[0])))
    assert sum(len(v) for v in out.values()) == 6 == len(cs), ('boulder left its track', out)
    return out


def scd_tuple(g, B, bp, bd):
    c = scd_comp(g, B)
    dmask = lambda xs: sum(1 << bd.idx[(x, 1)] for x in xs)
    pmask = lambda xs: sum(1 << bp.idx[(x, 2)] for x in xs)
    return (dmask(c['d1']), dmask(c['d2']), pmask(c['prec']), pmask(c['tog']))   # Net2 names sorted: d1 d2 prec tog


def scd_setup():
    g = scd_gadget()
    bp, Cp, clean, Pp = pp_clean()
    bd = K.Board(S2.PROTODIODE)
    Cd = K.explore(bd)
    dclean, _, _, Pd = S2.postselect_L(Cd, S2.PD_CHECKS, ['A', 'B', 'C', 'D'])
    okp = {S2.track(bp, s, 2) for s in clean}
    okd = {S2.track(bd, s, 1) for s in dclean}

    def ok(s):
        c = scd_comp(g, s[1])
        return c['prec'] in okp and c['tog'] in okp and c['d1'] in okd and c['d2'] in okd

    S1 = pp_state(bp, (4, 6))

    def net(prec_init):
        return S2.Net2({'prec': (S2.with_init(Pp, prec_init), {'A': 'T', 'B': 'T', 'C': 'T', 'E': 'X', 'F': 'Y'}),
                        'tog': (S2.with_init(Pp, S1), {'A': 'tT', 'B': 'tT', 'C': 'tT', 'E': 'O', 'F': 'T'}),
                        'd1': (Pd, {'A': 'I', 'B': 'X', 'C': 'd1cd', 'D': 'd1cd'}),
                        'd2': (Pd, {'A': 'Y', 'B': 'J', 'C': 'd2cd', 'D': 'd2cd'})},
                       {'O': 'O', 'I': 'I', 'J': 'J'})
    return g, bp, bd, ok, net


def scd_with(g, prec_xs):
    """flat initial boulders with the precursor blocks at local x prec_xs (toggle r, diodes m1)."""
    cs = (g.bset(g.board.b0) - {(9, 10), (11, 10)}) | {(5 + x, 10) for x in prec_xs}
    return g.mask(cs)


def scd_names(prec_xs):
    n = {(4, 3): 'α', (6, 3): 'β', (7, 16): 'X1', (12, 16): 'X2'}
    n[(5 + prec_xs[0], 10)] = 'γ'
    n[(5 + prec_xs[1], 10)] = 'δ'
    return n


def anim_scd(kind):
    g, bp, bd, ok, net = scd_setup()
    closed, open_ = (3, 5), (4, 6)
    if kind == 'open':
        S = Story('scd_open', 'Self-closing door: opening it (visit O→O)', g, 'Ani et al. Fig. 37; A2-scd §2')
        B0 = scd_with(g, closed)
        S.set((g.port('O'), B0, 0), names=scd_names(closed))
        S.head('Closed door', 'Top: the 1-toggle (α β). Middle: the precursor (γ δ), its exit to E is shut. '
                              'Bottom: two diodes.')
        goal = lambda s: s[0] == g.port('O') and scd_comp(g, s[1]) == {'tog': (4, 6), 'prec': open_, 'd1': (2,), 'd2': (2,)}
        p = g.walk(S.state, goal, ok=ok)
        S.play(p, 'door OPEN')
        N = net(pp_state(bp, closed)).explore()
        assert ('O', scd_tuple(g, S.state[1], bp, bd)) in N.T[(scd_tuple(g, B0, bp, bd), 'O')]
        S.end('Visiting O flips the precursor to "open" (γ δ moved) and leaves the toggle as it was.')
    elif kind == 'pass':
        S = Story('scd_pass', 'Self-closing door: I→J closes it behind you', g, 'Ani et al. Fig. 37; A2-scd §2')
        B0 = scd_with(g, open_)
        S.set((g.port('I'), B0, 0), names=scd_names(open_))
        S.head('Open door', 'Enter at I: through diode 1, into the precursor at E, out at F, through diode 2 to J.')
        goal = lambda s: s[0] == g.port('J') and scd_comp(g, s[1]) == {'tog': (4, 6), 'prec': closed, 'd1': (2,), 'd2': (2,)}
        p = g.walk(S.state, goal, ok=ok)
        S.play(p, 'door CLOSED behind the hero')
        N = net(pp_state(bp, open_)).explore()
        assert ('J', scd_tuple(g, S.state[1], bp, bd)) in N.T[(scd_tuple(g, B0, bp, bd), 'I')]
        S.end('Passing switched the precursor back to "closed": the door shut itself.')
    else:
        S = Story('scd_refused', 'Self-closing door: closed, I→J refused', g, 'Ani et al. Fig. 37; A2-scd §2')
        B0 = scd_with(g, closed)
        S.set((g.port('I'), B0, 0), names=scd_names(closed))
        S.head('Closed door', 'Enter at I and try to reach J without visiting O first.')
        S.refuse('J', ok=ok)
        N = net(pp_state(bp, closed)).explore()
        assert not any(q == 'J' for q, _ in N.T[(scd_tuple(g, B0, bp, bd), 'I')])
        S.end('Closed means closed: the precursor blocks E. Only a visit to O opens it.')
    return S


def anim_coin():
    rows = ["#X###Y#",
            "#.###.#",
            "#A#.#B#",
            "###E###"]
    g = Gadget(rows, labels={(3, 2): 'T'}, tele={(3, 2)})
    S = Story('coin', 'Teleport coin tile [A wall T wall B]', g, 'C-audit rule Z2; B-reduction §6.2')
    bd = g.board
    T = bd.idx[(3, 2)]
    # Z2: T's only 8-neighbour is E; A's only one is X (= X_A), B's only one is Y (= X_B); T, A, B pairwise apart
    nb = lambda i: {t for t, _ in bd.orth[i] + bd.diag[i]}
    assert nb(T) == {g.port('E')} and nb(g.port('A')) == {bd.idx[(1, 1)]} and nb(g.port('B')) == {bd.idx[(5, 1)]}
    for land, ex in (('A', 'X'), ('B', 'Y')):
        S.set(st(g, 'E'), names={})
        S.head(f'Coin flip: {land}', 'The hero enters at E, below the teleportation trap T.')
        S.play([S.state, (T, 0, 0)])
        assert (T, 0, 0) in set(g.moves(*st(g, 'E')))
        S.note('Teleportation trap: nature picks the landing cell, A or B (nothing else is possible).', 1300,
               flash=(3, 2))
        S.state = (g.port(land), 0, 0)
        S.note(f'Nature chose {land}.', 1300, flash=g.cell(g.port(land)))
        p = g.walk(S.state, at_port(g, ex))
        S.play(p, f'leave through {"X_A" if land == "A" else "X_B"}')
        assert S.state[0] == g.port(ex)
    S.end('One random bit per use, forever. The hero cannot steer it; the dungeon (R3) picks the worst side.')
    return S


ANIMS = [
    ('np_gd', anim_gd), ('np_gc', anim_gc), ('np_gx', anim_gx),
    ('diode_use', anim_diode_use), ('diode_break', anim_diode_break),
    ('slot1_break', lambda: anim_negative('slot1', LIB.SLOT1, 'SLOT1: overshoot opens B→A')),
    ('uturn2_break', lambda: anim_negative('uturn2', LIB.UTURN2, 'UTURN2: complete, but the interlock leaks')),
    ('pp_checks', anim_proto_precursor), ('precursor', anim_precursor), ('toggle', anim_toggle),
    ('scd_open', lambda: anim_scd('open')), ('scd_pass', lambda: anim_scd('pass')),
    ('scd_refused', lambda: anim_scd('refused')), ('coin', anim_coin),
]


# ====================================================================== rendering
TILES = None
YEL, BLUE, RED, WHITE = (255, 210, 60), (150, 200, 255), (235, 64, 52), (255, 255, 255)


def font(n, bold=False):
    for f in (("C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf"),
              "C:/Windows/Fonts/arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(f, n)
        except OSError:
            pass
    return ImageFont.load_default()


def wall_tile(rows, x, y):
    """same wallification as tools/visual/render_gadgets.py"""
    H = len(rows)

    def solid(x, y):
        return not (0 <= y < H and 0 <= x < len(rows[y])) or rows[y][x] == '#'
    near = any(not solid(x + i, y + j) for i in (-1, 0, 1) for j in (-1, 0, 1) if i or j)
    if not near:
        return 'stone'
    horiz_floor = not solid(x - 1, y) or not solid(x + 1, y)
    vert_floor = not solid(x, y - 1) or not solid(x, y + 1)
    return 'main walls vertical' if horiz_floor and not vert_floor else 'main walls horizontal'


def tile(name, S, cache={}):
    k = (name, S)
    if k not in cache:
        cache[k] = TILES[name].resize((S, S), Image.NEAREST).convert('RGBA')
    return cache[k]


def base_rows(g):
    out = []
    for y in range(g.H):
        r = g.rows[y].ljust(g.W, '#')
        out.append(''.join('#' if ch in '# ' else ('.' if ch in '0^' else ch) for ch in r))
    return out


def render_board(g, fr, S):
    rows = base_rows(g)
    bd = g.board
    im = Image.new('RGBA', (g.W * S, g.H * S), (0, 0, 0, 255))
    d = ImageDraw.Draw(im)
    fl = font(max(11, S * 9 // 16), True)
    fs = font(max(9, S * 7 // 16), True)
    for y in range(g.H):
        for x in range(g.W):
            ch = rows[y][x]
            if ch == '#':
                im.paste(tile(wall_tile(rows, x, y), S), (x * S, y * S))
                continue
            im.paste(tile('floor of a room', S), (x * S, y * S))
            i = bd.idx[(x, y)]
            if fr['H'] >> i & 1:
                im.alpha_composite(tile('hole', S), (x * S, y * S))
            if (x, y) in g.tele:
                im.alpha_composite(tile('teleportation trap', S), (x * S, y * S))
            if fr['B'] >> i & 1:
                im.alpha_composite(tile('boulder', S), (x * S, y * S))
            if fr['h'] == i:
                im.alpha_composite(tile('valkyrie,female', S), (x * S, y * S))
    for y in range(g.H):
        for x in range(g.W):
            ch = rows[y][x]
            lab = g.labels.get((x, y))
            if ch.isupper():
                d.rectangle([x * S + 1, y * S + 1, x * S + S - 2, y * S + S - 2], outline=YEL, width=2)
                d.text((x * S + 3, y * S + 1), ch, fill=YEL, font=fl, stroke_width=2, stroke_fill=(0, 0, 0))
            elif lab:
                d.text((x * S + 3, y * S + 1), lab, fill=BLUE, font=fs, stroke_width=2, stroke_fill=(0, 0, 0))
    for (x, y), n in fr['names'].items():
        d.text((x * S + S - 2, y * S + S - 1), n, fill=WHITE, font=fs, anchor='rd', stroke_width=2,
               stroke_fill=(0, 0, 0))
    if fr['nope']:
        x, y = fr['nope']
        d.rectangle([x * S + 1, y * S + 1, x * S + S - 2, y * S + S - 2], outline=RED, width=3)
        d.line([x * S + 6, y * S + 6, x * S + S - 7, y * S + S - 7], fill=RED, width=3)
        d.line([x * S + S - 7, y * S + 6, x * S + 6, y * S + S - 7], fill=RED, width=3)
    if fr['flash']:
        x, y = fr['flash']
        d.rectangle([x * S - 2, y * S - 2, x * S + S + 1, y * S + S + 1], outline=(224, 112, 224), width=3)
    return im


def wrap(d, text, f, width):
    out, line = [], ''
    for w in text.split():
        t = (line + ' ' + w).strip()
        if d.textlength(t, font=f) > width and line:
            out.append(line)
            line = w
        else:
            line = t
    out.append(line)
    return out


def render_frames(S):
    g = S.g
    S_px = 32 if g.W * 32 <= 420 and g.H * 32 <= 420 else 22
    bw, bh = g.W * S_px, g.H * S_px
    W = max(bw + 32, 560)
    ft, fp, fc, fn = font(19, True), font(14, True), font(15), font(12)
    tmp = ImageDraw.Draw(Image.new('RGB', (10, 10)))
    caps = [wrap(tmp, fr['cap'], fc, W - 90) for fr in S.frames]
    ncap = max(len(c) for c in caps)
    top, bot = 62, 18 + 21 * ncap
    H = top + bh + bot + 8
    out = []
    nmove = sum(1 for fr in S.frames if fr['dur'] in (MOVE_MS, PUSH_MS))
    k = 0
    for fr, cap in zip(S.frames, caps):
        im = Image.new('RGB', (W, H), (18, 18, 24))
        d = ImageDraw.Draw(im)
        d.text((16, 10), S.title, fill=(236, 236, 236), font=ft)
        d.text((16, 38), fr['phase'], fill=YEL, font=fp)
        d.text((W - 14, 40), S.sub, fill=(150, 150, 165), font=fn, anchor='ra')
        board = render_board(g, fr, S_px)
        im.paste(board.convert('RGB'), ((W - bw) // 2, top))
        if fr['dur'] in (MOVE_MS, PUSH_MS):
            k += 1
        col = RED if fr['nope'] else (236, 236, 236)
        for j, line in enumerate(cap):
            d.text((16, top + bh + 10 + 21 * j), line, fill=col, font=fc)
        d.text((W - 14, top + bh + 12), f'{k}/{nmove}', fill=(150, 150, 165), font=fn, anchor='ra')
        out.append(im)
    return out


def save_gif(S, path):
    ims = render_frames(S)
    durs = [fr['dur'] for fr in S.frames]
    # one shared palette (tiles + text), no dithering: small deltas between frames
    strip = Image.new('RGB', (ims[0].width, ims[0].height * 3))
    for j, k in enumerate((0, len(ims) // 2, len(ims) - 1)):
        strip.paste(ims[k], (0, ims[0].height * j))
    pal = strip.quantize(colors=96, method=Image.Quantize.MEDIANCUT)
    q = [im.quantize(palette=pal, dither=Image.Dither.NONE) for im in ims]
    q[0].save(path, save_all=True, append_images=q[1:], duration=durs, loop=0, optimize=False, disposal=1)
    return ims


def to_json(S):
    g = S.g
    base = base_rows(g)
    base = [''.join('^' if (x, y) in g.tele else ch for x, ch in enumerate(r)) for y, r in enumerate(base)]
    lab = {f'{x},{y}': t for (x, y), t in g.labels.items()}
    frames = []
    for fr in S.frames:
        h = g.cell(fr['h']) if fr['h'] is not None else None
        frames.append({
            'h': list(h) if h else None,
            'b': [[x, y, fr['names'].get((x, y), '')] for (x, y) in sorted(g.bset(fr['B']))],
            'o': [list(g.cell(i)) for i in range(len(g.board.cells)) if fr['H'] >> i & 1],
            'c': fr['cap'], 'p': fr['phase'], 'd': fr['dur'],
            'n': list(fr['nope']) if fr['nope'] else None,
            'f': list(fr['flash']) if fr['flash'] else None,
        })
    return {'id': S.id, 'title': S.title, 'src': S.sub, 'rows': base, 'labels': lab, 'frames': frames}


def main():
    global TILES
    only = None
    if '--only' in sys.argv:
        only = set(sys.argv[sys.argv.index('--only') + 1].split(','))
    gif = '--no-gif' not in sys.argv
    TILES = load_all(os.path.join(ROOT, 'src', 'win', 'share'))
    outdir = os.path.join(ROOT, 'media', 'exptime', 'anim')
    os.makedirs(outdir, exist_ok=True)
    jpath = os.path.join(ROOT, 'site', 'paper', 'engine', 'anims_exptime.json')
    data = {}
    if only and os.path.exists(jpath):
        data = {a['id']: a for a in json.load(open(jpath, encoding='utf-8'))['anims']}
    firsts = []
    for aid, fn in ANIMS:
        if only and aid not in only:
            continue
        S = fn()
        assert S.id == aid, (S.id, aid)
        data[aid] = to_json(S)
        nm = sum(1 for f in S.frames if f['dur'] in (MOVE_MS, PUSH_MS))
        line = f'{aid:14s} {len(S.frames):4d} frames, {nm:3d} moves'
        if gif:
            p = os.path.join(outdir, aid + '.gif')
            ims = save_gif(S, p)
            sz = os.path.getsize(p)
            with Image.open(p) as chk:
                assert chk.n_frames == len(S.frames), (chk.n_frames, len(S.frames))
            assert sz < 1.5e6, f'{aid}.gif too big: {sz}'
            line += f', {sz / 1024:6.1f} KB'
            mv = [i for i, f in enumerate(S.frames) if f['dur'] in (MOVE_MS, PUSH_MS)]
            firsts.append((S.title, ims[mv[-1] if mv else 0]))
        print(line, flush=True)
    order = [a for a, _ in ANIMS if a in data]
    with open(jpath, 'w', encoding='utf-8') as f:
        json.dump({'generated_by': 'tools/visual/animate_gadgets.py', 'anims': [data[a] for a in order]}, f,
                  ensure_ascii=False, separators=(',', ':'))
    print('json', jpath, os.path.getsize(jpath))
    if gif and not only:
        cw = 300
        cells = []
        for title, im in firsts:
            sc = cw / im.width
            cells.append(im.resize((cw, int(im.height * sc)), Image.LANCZOS))
        cols = 5
        rows_n = (len(cells) + cols - 1) // cols
        rh = [max(c.height for c in cells[r * cols:(r + 1) * cols]) for r in range(rows_n)]
        sheet = Image.new('RGB', (cols * (cw + 8) + 8, sum(rh) + 8 * (rows_n + 1) + 40), (233, 237, 238))
        d = ImageDraw.Draw(sheet)
        d.text((10, 10), 'Gadget animations (last move of each), tools/visual/animate_gadgets.py', fill=(25, 34, 39),
               font=font(18, True))
        y = 44
        for r in range(rows_n):
            for c in range(cols):
                k = r * cols + c
                if k < len(cells):
                    sheet.paste(cells[k], (8 + c * (cw + 8), y))
            y += rh[r] + 8
        sp = os.path.join(outdir, 'contact_sheet.png')
        sheet.save(sp)
        print('sheet', sp, sheet.size)


if __name__ == '__main__':
    main()
