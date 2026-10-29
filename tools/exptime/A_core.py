#!/usr/bin/env python3
"""A_core.py -- exact local model of reusable boulder gadgets (EXPTIME workstream A) + simulation checks.

Movement model (= hu-off §B.4 M1-M3, hu-on-lower §2 F1-F3, Lean NetHackPush; Sokoban rules, heavy hero, no pits):
  * hero moves to one of 8 neighbours;
  * orthogonal step onto floor without boulder: step;
  * orthogonal step into a boulder: push iff the cell beyond is floor without boulder (no squeeze: heavy hero);
  * diagonal step: target must be floor without boulder, and at least one of the two corner cells must be floor
    without boulder (corner rule: walls and boulders are both 'bad rock' under Sokoban); no diagonal push.
Map chars: '#' or ' ' wall/stone, '.' floor, '0' boulder (on floor), 'A'-'Z' port cells (floor, never a boulder),
'a'-'z' named floor cells (documentation only).

Gadget semantics. A local state is the boulder set. A *traversal* from port p in state B is a hero walk that starts on
p and ends the first time the hero stands on a port cell again (any port, p included) -- continuing from there is a new
traversal. T(B, p) = {(q, B')}. If a boulder could ever be pushed onto a port cell the gadget is rejected (LEAK): this
is how "boulders never leave the gadget" is enforced (a boulder that reaches a port could be pushed into the corridor).

Game-safety check (two simulations; the hero is the only agent inside a gadget, nature acts only at the coin, which is
outside every gadget, so two one-player simulations give strategy transfer in both directions -- see A-gadgets.md §1):
  sound:     concrete <= abstract   every concrete traversal p->q (B->B') is matched by an abstract traversal p->q
             (a->a') with B' <= a', or q = p and B' <= a ("the hero only looked in": abstract does nothing);
  complete:  abstract <= concrete   every abstract traversal is realised by a concrete one with related successors.
"""
from collections import deque

D4 = [(1, 0), (-1, 0), (0, 1), (0, -1)]
DG = [(1, 1), (1, -1), (-1, 1), (-1, -1)]


class LeakError(Exception):
    pass


class Board:
    def __init__(self, rows):
        rows = [r.rstrip('\n') for r in rows]
        self.rows = rows
        self.H = len(rows)
        self.W = max(len(r) for r in rows)
        g = [r.ljust(self.W) for r in rows]
        self.cells = []
        self.idx = {}
        b0 = 0
        self.ports = {}
        for y in range(self.H):
            for x in range(self.W):
                ch = g[y][x]
                if ch in '# ':
                    continue
                i = len(self.cells)
                self.idx[(x, y)] = i
                self.cells.append((x, y))
                if ch == '0':
                    b0 |= 1 << i
                elif ch.isupper():
                    self.ports[ch] = i
        self.b0 = b0
        self.portmask = sum(1 << i for i in self.ports.values())
        self.portname = {i: n for n, i in self.ports.items()}
        n = len(self.cells)
        self.orth = [[] for _ in range(n)]   # (target, beyond or -1)
        self.diag = [[] for _ in range(n)]   # (target, corner mask)
        for i, (x, y) in enumerate(self.cells):
            for dx, dy in D4:
                t = self.idx.get((x + dx, y + dy))
                if t is None:
                    continue
                b = self.idx.get((x + 2 * dx, y + 2 * dy), -1)
                self.orth[i].append((t, b))
            for dx, dy in DG:
                t = self.idx.get((x + dx, y + dy))
                if t is None:
                    continue
                cm = 0
                for c in ((x + dx, y), (x, y + dy)):
                    if c in self.idx:
                        cm |= 1 << self.idx[c]
                if cm:
                    self.diag[i].append((t, cm))

    def moves(self, h, B):
        """yield (h', B') for every legal hero move from h with boulders B."""
        for t, b in self.orth[h]:
            if B >> t & 1:
                if b < 0 or B >> b & 1:
                    continue
                if self.portmask >> b & 1:
                    raise LeakError((self.cells[t], self.cells[b]))
                yield t, (B & ~(1 << t)) | (1 << b)
            else:
                yield t, B
        for t, cm in self.diag[h]:
            if B >> t & 1:
                continue
            if cm & ~B:           # some corner is floor without boulder
                yield t, B

    def traversals(self, B, p):
        start = (self.ports[p], B)
        seen = {start}
        dq = deque([start])
        out = set()
        while dq:
            h, Bc = dq.popleft()
            for s in self.moves(h, Bc):
                if s in seen:
                    continue
                seen.add(s)
                if self.portmask >> s[0] & 1:
                    out.add((self.portname[s[0]], s[1]))
                else:
                    dq.append(s)
        return out

    def show(self, B, hero=None):
        g = [list(r.ljust(self.W)) for r in self.rows]
        for i, (x, y) in enumerate(self.cells):
            if g[y][x] == '0':
                g[y][x] = '.'
            if B >> i & 1:
                g[y][x] = '0'
        if hero is not None:
            x, y = self.cells[hero]
            g[y][x] = '@'
        return '\n'.join(''.join(r) for r in g)


class System:
    """finite gadget system: states, ports, T[(s, p)] = set of (q, s')"""
    def __init__(self, ports, init, T, states):
        self.ports, self.init, self.T, self.states = ports, init, T, states


def explore(board, max_states=200000):
    """all local states reachable from the initial one by traversals; returns a System (raises LeakError)."""
    ports = sorted(board.ports)
    T = {}
    seen = {board.b0}
    dq = deque([board.b0])
    while dq:
        B = dq.popleft()
        for p in ports:
            tr = board.traversals(B, p)
            T[(B, p)] = tr
            for _, B2 in tr:
                if B2 not in seen:
                    if len(seen) >= max_states:
                        raise RuntimeError('too many states')
                    seen.add(B2)
                    dq.append(B2)
    return System(ports, board.b0, T, sorted(seen))


def abstract(ports, init, trans):
    """trans: dict state -> dict port -> list of (q, state')"""
    T = {}
    for s, d in trans.items():
        for p in ports:
            T[(s, p)] = set(d.get(p, []))
    return System(ports, init, T, sorted(trans))


def sim_sound(C, A):
    """greatest R with (c,a) in R => every C-traversal matched by A (or a bounce q=p with c' R a)."""
    R = {(c, a) for c in C.states for a in A.states}
    changed = True
    while changed:
        changed = False
        for (c, a) in list(R):
            ok = True
            for p in C.ports:
                for q, c2 in C.T[(c, p)]:
                    if q == p and (c2, a) in R:
                        continue
                    if any(q2 == q and (c2, a2) in R for q2, a2 in A.T.get((a, p), ())):
                        continue
                    ok = False
                    break
                if not ok:
                    break
            if not ok:
                R.discard((c, a))
                changed = True
    return R


def sim_complete(A, C):
    """greatest R with (a,c) in R => every A-traversal realised by C with related successors."""
    R = {(a, c) for a in A.states for c in C.states}
    changed = True
    while changed:
        changed = False
        for (a, c) in list(R):
            ok = True
            for p in A.ports:
                for q, a2 in A.T.get((a, p), ()):
                    if not any(q2 == q and (a2, c2) in R for q2, c2 in C.T[(c, p)]):
                        ok = False
                        break
                if not ok:
                    break
            if not ok:
                R.discard((a, c))
                changed = True
    return R


def check(C, A):
    """returns (sound, complete, Rs, Rc)"""
    Rs = sim_sound(C, A)
    Rc = sim_complete(A, C)
    return (C.init, A.init) in Rs, (A.init, C.init) in Rc, Rs, Rc


def relation_table(C):
    """port-to-port relation per concrete state, ignoring bounces with no state change."""
    out = {}
    for c in C.states:
        out[c] = sorted({(p, q) for p in C.ports for q, _ in C.T[(c, p)] if not (q == p)})
    return out


# ---------- abstract gadget networks (gadgets wired by free corridors) ----------
class Network:
    """gadgets: name -> (System, {port: node}); external: {extname: node}. Hero moves between nodes by traversing
    gadgets; nodes are free junctions. A network traversal starts on an external node and ends the first time the
    hero stands on an external node again."""
    def __init__(self, gadgets, external):
        self.g = gadgets
        self.names = sorted(gadgets)
        self.ext = external
        self.extnode = {v: k for k, v in external.items()}
        self.at = {}
        for gi, n in enumerate(self.names):
            sysm, pm = gadgets[n]
            for p, node in pm.items():
                self.at.setdefault(node, []).append((gi, p))

    def traversals(self, S, p):
        start = (self.ext[p], S)
        seen = {start}
        dq = deque([start])
        out = set()
        while dq:
            node, St = dq.popleft()
            for gi, port in self.at.get(node, []):
                sysm, pm = self.g[self.names[gi]]
                for q, s2 in sysm.T[(St[gi], port)]:
                    S2 = St[:gi] + (s2,) + St[gi + 1:]
                    st = (pm[q], S2)
                    if st in seen:
                        continue
                    seen.add(st)
                    if pm[q] in self.extnode:
                        out.add((self.extnode[pm[q]], S2))
                    else:
                        dq.append(st)
        return out

    def explore(self):
        ports = sorted(self.ext)
        init = tuple(self.g[n][0].init for n in self.names)
        T = {}
        seen = {init}
        dq = deque([init])
        while dq:
            S = dq.popleft()
            for p in ports:
                tr = self.traversals(S, p)
                T[(S, p)] = tr
                for _, S2 in tr:
                    if S2 not in seen:
                        seen.add(S2)
                        dq.append(S2)
        return System(ports, init, T, sorted(seen))


# ---------- checkable gadgets (Ani et al. postselection, lifted to games in A-gadgets.md §2) ----------
def check_legal(C, c, checks):
    """is the checking sequence [(p1,q1),(p2,q2),...] legal from local state c (some choice of intermediate states)?"""
    frontier = {c}
    for p, q in checks:
        frontier = {c2 for c1 in frontier for (q2, c2) in C.T[(c1, p)] if q2 == q}
        if not frontier:
            return False
    return True


def postselect(C, checks, ports=None):
    """clean = states where the check sequence is legal. Returns (clean, absorbing, restricted System).
    absorbing: no traversal (from ANY port of C) leads from a broken state to a clean one (B's G3).
    restricted System: only clean states, only `ports` (L'), only transitions that end clean."""
    clean = {c for c in C.states if check_legal(C, c, checks)}
    absorbing = all(c2 not in clean for c in C.states if c not in clean
                    for p in C.ports for _, c2 in C.T[(c, p)])
    ports = ports or C.ports
    T = {}
    for c in clean:
        for p in ports:
            T[(c, p)] = {(q, c2) for (q, c2) in C.T[(c, p)] if c2 in clean and q in ports}
    return clean, absorbing, System(sorted(ports), C.init, T, sorted(clean))


def wire(sysm, joins, ext):
    """close a gadget's ports into a network: joins = list of port groups that share one free node;
    ext = ports that stay external. Returns the network System."""
    pm = {}
    for k, grp in enumerate(joins):
        for p in grp:
            pm[p] = ('j', k)
    for p in ext:
        pm[p] = ('e', p)
    net = Network({'g': (sysm, pm)}, {p: ('e', p) for p in ext})
    return net.explore()
