#!/usr/bin/env python3
"""D_game.py -- exact two-player (hero vs nature) reachability checker for small NetHack boulder levels with the
restricted teleport coin (proofs/exptime-feasibility.md §3, workstream D; usage in proofs/exptime/D-checker.md).

Movement model = tools/check_small.py (hu-on-lower §2) plus teleport traps:
  * hero steps to an 8-neighbour: target floor, no boulder, not an unplugged hole (holes are never entered);
    a diagonal step is refused iff both corner cells are bad (not floor, or boulder) [Sokoban corner rule];
  * orthogonal step into a boulder pushes it iff the cell beyond is floor without boulder (heavy hero, no squeeze);
    a boulder pushed onto a hole plugs it (both vanish, cell becomes floor); no diagonal pushes;
  * stepping onto a teleport trap T (same step rules; T is floor for corners) -> NATURE picks the landing cell among
    T's landing set minus cells holding a boulder or an unplugged hole (NetHack: teleok = goodpos & no trap); the
    hero is never left on T. Empty free landing set = DESIGN VIOLATION (counted as a hero loss).
  * a push of a boulder onto a trap cell = DESIGN VIOLATION (NetHack relocates it level-wide, rloco): the move is
    removed from the game and every reachable occurrence is reported.
Game: player node = (boulder set, unplugged holes, hero region); nature node = (boulder set, holes, trap).
Hero region = free component of non-trap cells (traps are left out of the flood, so the region is exact: every cell
of a region has the same successors and nature acts only on trap entry). Win: goal cell in the hero's region
(optionally also boulders/holes == a named state). Infinite plays lose (least fixed point = attractor).
"""
import argparse, json, os, subprocess, sys, time
from collections import deque

D4 = [(1, 0), (-1, 0), (0, 1), (0, -1)]
D8 = D4 + [(1, 1), (1, -1), (-1, 1), (-1, -1)]
DNAME = {(1, 0): 'E', (-1, 0): 'W', (0, 1): 'S', (0, -1): 'N'}
FLOOR_CH = set('.@Gg0B^T') | set('abcdefhijklmnopqrstuvwxyz')


# ----------------------------------------------------------------------------------------------- level format
class Level:
    """ASCII level. Grid chars: '.' floor, '0'/'B' boulder, '^' hole, '@' start, 'G'/'g' goal, 'T' teleport trap,
    lowercase letter (not g) = floor cell that is also a port named by the letter; anything else = wall/stone.
    Directive lines (start with ':'), anywhere:
      :zone x0 y0 x1 y1            every T in the rectangle lands on its free non-trap floor cells (NetHack rule)
      :trap x y land x1 y1 x2 y2 .. explicit landing cells of the trap at (x,y)
      :port NAME x y               named cell (start/goal of a traversal query)
      :state NAME x y x y ...      named boulder set (holes = all grid holes unplugged); 'init' = grid boulders
    Lines starting with '//' are comments. Coordinates: x = column, y = grid row, 0-based."""

    def __init__(self, text):
        rows, dirs = [], []
        for ln in text.splitlines():
            if ln.startswith('//'):
                continue
            (dirs if ln.startswith(':') else rows).append(ln.rstrip('\n'))
        while rows and not rows[-1].strip():
            rows.pop()
        while rows and not rows[0].strip():
            rows.pop(0)
        self.rows = rows
        self.H, self.W = len(rows), max((len(r) for r in rows), default=0)
        self.floor, self.boulders, self.holes, self.traps = set(), set(), set(), set()
        self.start = self.goal = None
        self.ports = {}
        for y, r in enumerate(rows):
            for x, ch in enumerate(r):
                if ch not in FLOOR_CH:
                    continue
                c = (x, y)
                self.floor.add(c)
                if ch in '0B':
                    self.boulders.add(c)
                elif ch == '^':
                    self.holes.add(c)
                elif ch == 'T':
                    self.traps.add(c)
                elif ch == '@':
                    self.start = c
                elif ch in 'Gg':
                    self.goal = c
                elif ch.islower():
                    self.ports[ch] = c
        self.landing = {}
        self.states = {}
        for d in dirs:
            t = d[1:].split()
            if not t:
                continue
            if t[0] == 'zone':
                x0, y0, x1, y1 = map(int, t[1:5])
                cells = [(x, y) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)]
                land = [c for c in cells if c in self.floor and c not in self.traps]
                for c in cells:
                    if c in self.traps:
                        self.landing[c] = land
            elif t[0] == 'trap':
                c = (int(t[1]), int(t[2]))
                assert t[3] == 'land', d
                v = list(map(int, t[4:]))
                self.landing[c] = [(v[i], v[i + 1]) for i in range(0, len(v), 2)]
            elif t[0] == 'port':
                self.ports[t[1]] = (int(t[2]), int(t[3]))
            elif t[0] == 'state':
                v = list(map(int, t[2:]))
                self.states[t[1]] = {(v[i], v[i + 1]) for i in range(0, len(v), 2)}
            else:
                raise ValueError('unknown directive ' + d)
        self.states.setdefault('init', set(self.boulders))
        for c in self.traps:
            assert c in self.landing, ('trap without landing set', c)
            for l in self.landing[c]:
                assert l in self.floor and l not in self.traps, ('bad landing cell', c, l)
        for nm, s in self.states.items():
            assert s <= self.floor and not (s & self.traps), ('bad state', nm)
        assert self.goal is None or self.goal not in self.traps | self.holes

    def cell_of(self, name, default=None):
        if name is None:
            return default
        if name in ('@', 'start'):
            return self.start
        if name in ('G', 'g', 'goal'):
            return self.goal
        if name in self.ports:
            return self.ports[name]
        x, y = name.split(',')
        return (int(x), int(y))


def level_from_layout(lay):
    """Convert a gen_on_instance.Layout (check_small's levels) into a Level (no traps)."""
    g = [row[:] for row in lay.grid]
    for (x, y) in lay.boulders:
        g[y][x] = '0'
    g[lay.start[1]][lay.start[0]] = '@'
    g[lay.goal[1]][lay.goal[0]] = 'G'
    return Level('\n'.join(''.join(ch if ch in '.0^@G' else '#' for ch in r) for r in g))


# ----------------------------------------------------------------------------------------------- compressed model
class Model:
    """Nodes: [0, ns) static components (floor that never holds a boulder, not hole, not trap; merged over moves
    legal in every state), [ns, ns+D) dynamic cells (boulder-reachable cells + holes), [ns+D, N) trap cells."""

    def __init__(self, L):
        self.L = L
        floor, traps = L.floor, L.traps
        # boulder closure; plugged holes become floor a boulder can rest on, so holes seed the closure too
        dyn = set(L.boulders) | set().union(*L.states.values()) | set(L.holes)
        stack = list(dyn)
        while stack:
            b = stack.pop()
            for dx, dy in D4:
                h, t = (b[0] - dx, b[1] - dy), (b[0] + dx, b[1] + dy)
                if h in floor and h not in traps and t in floor:
                    if t in traps:
                        continue
                    if t not in dyn:
                        dyn.add(t)
                        stack.append(t)
        dyn |= L.holes
        self.dynl = sorted(dyn)
        static = floor - dyn - traps
        par = {c: c for c in static}

        def find(c):
            while par[c] != c:
                par[c] = par[par[c]]
                c = par[c]
            return c

        def corners(a, d):
            return [(a[0] + d[0], a[1]), (a[0], a[1] + d[1])]

        def good_always(k):     # floor that can never hold a boulder (static floor, trap, ...)
            return k in floor and k not in dyn
        for a in static:
            for d in D8:
                b = (a[0] + d[0], a[1] + d[1])
                if b in static and (not (d[0] and d[1]) or any(good_always(k) for k in corners(a, d))):
                    ra, rb = find(a), find(b)
                    if ra != rb:
                        par[ra] = rb
        roots = sorted({find(c) for c in static}, key=lambda r: min(c for c in static if find(c) == r))
        rid = {r: i for i, r in enumerate(roots)}
        ns, D = len(roots), len(self.dynl)
        self.ns, self.D = ns, D
        node = {c: rid[find(c)] for c in static}
        node.update({c: ns + i for i, c in enumerate(self.dynl)})
        self.trapl = sorted(traps)
        node.update({c: ns + D + i for i, c in enumerate(self.trapl)})
        self.node = node
        self.N = ns + D + len(self.trapl)
        self.cells = [[] for _ in range(self.N)]
        for c, n in node.items():
            self.cells[n].append(c)
        for lst in self.cells:
            lst.sort()
        dbit = lambda c: 1 << (node[c] - ns)
        # walking edges between non-trap nodes and trap-entry edges; cond None = always, else list of corner masks
        # (edge usable iff for some mask not all its dyn corners hold boulders)
        adj = [dict() for _ in range(self.N)]
        tent = [dict() for _ in range(self.N)]
        self.tent_cell = {}     # (u, trap node) -> (hero cell, trap cell) witness for output
        for a in floor:
            if a in traps:
                continue
            for d in D8:
                b = (a[0] + d[0], a[1] + d[1])
                if b not in floor:
                    continue
                na, nb = node[a], node[b]
                if na == nb:
                    continue
                cond = None
                if d[0] and d[1]:
                    ks = [k for k in corners(a, d) if k in floor]
                    if not ks:
                        continue
                    if not any(good_always(k) for k in ks):
                        cond = sum(dbit(k) for k in ks)
                tgt = tent if b in traps else adj
                if b in traps:
                    self.tent_cell.setdefault((na, nb), (a, b))
                old = tgt[na].get(nb, 0)
                if old is None:
                    continue
                tgt[na][nb] = None if cond is None else (old if isinstance(old, list) else []) + [cond]
        self.un_mask = [sum(1 << v for v, c in a.items() if c is None) for a in adj]
        self.co = [[(v, c) for v, c in a.items() if c is not None] for a in adj]
        self.tent = [list(a.items()) for a in tent]
        self.corner_mask = 0
        for lst in self.co:
            for _, cond in lst:
                for c in cond:
                    self.corner_mask |= c
        self.static_all = (1 << ns) - 1
        self.dyn_all = (1 << D) - 1
        self._cache = {}
        # pushes: per dyn index: (hero node, target bit, boulder cell, dir) ; violations: (hero node, trap cell, ...)
        self.pushes, self.vpush = [], []
        for c in self.dynl:
            lst, vl = [], []
            for d in D4:
                h, t = (c[0] - d[0], c[1] - d[1]), (c[0] + d[0], c[1] + d[1])
                if h not in floor or h in traps or t not in floor:
                    continue
                if t in traps:
                    vl.append((node[h], t, d))
                else:
                    lst.append((node[h], dbit(t), d))
            self.pushes.append(lst)
            self.vpush.append(vl)
        self.hole_bits = sum(dbit(c) for c in L.holes)
        # landing: per trap node: list of (node, dyn bit or 0, cell)
        self.land = {}
        for t in self.trapl:
            self.land[node[t]] = [(node[l], dbit(l) if node[l] >= ns and node[l] < ns + D else 0, l)
                                  for l in L.landing[t]]
        self.landing_dyn = 0
        for lst in self.land.values():
            for _, b, _ in lst:
                self.landing_dyn |= b

    def bmask(self, cells):
        return sum(1 << (self.node[c] - self.ns) for c in cells)

    def region(self, s, bm, hm):
        ns = self.ns
        passable = self.static_all | ((~(bm | hm) & self.dyn_all) << ns)
        ck = bm & self.corner_mask
        adjc = self._cache.get(ck)
        if adjc is None:
            adjc = list(self.un_mask)
            for u, lst in enumerate(self.co):
                for v, conds in lst:
                    if any((bm & c) != c for c in conds):
                        adjc[u] |= 1 << v
            if len(self._cache) > 4000:
                self._cache.clear()
            self._cache[ck] = adjc
        frontier = seen = 1 << s
        while frontier:
            acc, f = 0, frontier
            while f:
                low = f & -f
                acc |= adjc[low.bit_length() - 1]
                f ^= low
            frontier = acc & passable & ~seen
            seen |= frontier
        return seen

    def free(self, n, bm, hm):
        return n < self.ns or n >= self.ns + self.D or not ((bm | hm) >> (n - self.ns)) & 1

    def cellset(self, mask):
        return sorted(self.dynl[i] for i in range(mask.bit_length()) if (mask >> i) & 1)


def coin_lint(L):
    """Static design checks from C-audit.md (INTERFACE.md, C -> A, B):
    Z1: R_B (closure of boulder cells under orthogonal pushes, hero cell floor non-trap, holes counted as floor)
        must avoid Z u N8(Z) for every coin (Z = trap + its landing cells; N8(Z) contains the entry cell E).
    Z2: each trap has exactly one floor 8-neighbour (E); trap and landing cells pairwise non-adjacent."""
    floor, traps = L.floor, L.traps
    rb = set(L.boulders) | set().union(*L.states.values())
    stack = list(rb)
    while stack:
        b = stack.pop()
        for dx, dy in D4:
            h, t = (b[0] - dx, b[1] - dy), (b[0] + dx, b[1] + dy)
            if h in floor and h not in traps and t in floor and t not in rb:
                rb.add(t)
                if t not in traps:
                    stack.append(t)
    n8 = lambda c: {(c[0] + dx, c[1] + dy) for dx, dy in D8}
    out = {}
    for t in sorted(traps):
        Z = {t} | set(L.landing[t])
        danger = Z | set().union(*(n8(c) for c in Z))
        hit = sorted(rb & danger & floor)
        nb = sorted(c for c in n8(t) if c in floor)
        adj = sorted((a, b) for a in Z for b in Z if a < b and b in n8(a))
        out[t] = dict(Z1_ok=not hit, Z1_boulder_reach=hit, Z2_ok=len(nb) == 1 and not adj,
                      trap_floor_neighbours=nb, adjacent_pairs=adj)
    return out


# ----------------------------------------------------------------------------------------------- game graph
class Game:
    """Explicit reachable game graph from a list of start player positions (goal-independent)."""

    def __init__(self, M, starts, max_states=5_000_000):
        self.M = M
        self.key = []      # node id -> key: ('P', bm, hm, rmin) or ('N', bm, hm, trap)
        self.reg = []      # region mask (P) or None
        self.succ = []     # list of (succ id, action)
        self.idx = {}
        self.violations = []   # (kind, node id, detail)
        self.starts = []
        q = deque()
        for (bm, hm, s) in starts:
            i = self._add_p(bm, hm, M.region(s, bm, hm), q)
            self.starts.append(i)
        while q:
            i = q.popleft()
            k = self.key[i]
            out = []
            if k[0] == 'P':
                _, bm, hm, _ = k
                reg = self.reg[i]
                m = bm
                while m:
                    low = m & -m
                    bi = low.bit_length() - 1
                    m ^= low
                    for hn, tb, d in M.pushes[bi]:
                        if not (reg >> hn) & 1 or bm & tb:
                            continue
                        if hm & tb:
                            nb, nh = bm ^ low, hm ^ tb
                        else:
                            nb, nh = (bm ^ low) | tb, hm
                        j = self._add_p(nb, nh, M.region(M.ns + bi, nb, nh), q)
                        out.append((j, ('push', M.dynl[bi], d)))
                    for hn, tcell, d in M.vpush[bi]:
                        if (reg >> hn) & 1:
                            self.violations.append(('boulder-onto-trap', i, (M.dynl[bi], DNAME[d], tcell)))
                seen_t = set()
                f = reg
                while f:
                    low = f & -f
                    u = low.bit_length() - 1
                    f ^= low
                    for t, cond in M.tent[u]:
                        if t in seen_t:
                            continue
                        if cond is not None and not any((bm & c) != c for c in cond):
                            continue
                        seen_t.add(t)
                        j = self._add(('N', bm, hm, t), None, q)
                        out.append((j, ('enter', M.cells[t][0])))
            else:
                _, bm, hm, t = k
                seen_r = {}
                for ln, lb, lcell in M.land[t]:
                    if lb and (bm | hm) & lb:
                        continue
                    reg = M.region(ln, bm, hm)
                    j = self._add_p(bm, hm, reg, q)
                    if j in seen_r:
                        seen_r[j].append(lcell)
                        continue
                    seen_r[j] = [lcell]
                    out.append((j, ('land', seen_r[j])))
                if not out:
                    self.violations.append(('empty-landing-set', i, M.cells[t][0]))
            # dedupe successors (keep first action)
            ded, sj = [], set()
            for j, a in out:
                if j not in sj:
                    sj.add(j)
                    ded.append((j, a))
            self.succ[i] = ded
            if len(self.key) > max_states:
                raise RuntimeError('state cap %d' % max_states)
        self.landing_boulder = sum(1 for k in self.key if k[0] == 'P' and k[1] & M.landing_dyn)

    def _add_p(self, bm, hm, reg, q):
        return self._add(('P', bm, hm, (reg & -reg).bit_length() - 1), reg, q)

    def _add(self, k, reg, q):
        i = self.idx.get(k)
        if i is None:
            i = len(self.key)
            self.idx[k] = i
            self.key.append(k)
            self.reg.append(reg)
            self.succ.append(None)
            q.append(i)
        return i

    def attractor(self, goal_node, goal_state=None):
        """Least fixed point. Returns rank list (None = losing). goal_state = (bm, hm) or None."""
        n = len(self.key)
        pred = [[] for _ in range(n)]
        for i, s in enumerate(self.succ):
            for j, _ in s:
                pred[j].append(i)
        rank = [None] * n
        cnt = [len(s) for s in self.succ]
        q = deque()
        for i, k in enumerate(self.key):
            if k[0] == 'P' and (self.reg[i] >> goal_node) & 1 and (goal_state is None or k[1:3] == goal_state):
                rank[i] = 0
                q.append(i)
        while q:
            j = q.popleft()
            for i in pred[j]:
                if rank[i] is not None:
                    continue
                if self.key[i][0] == 'P':
                    rank[i] = rank[j] + 1
                    q.append(i)
                else:
                    cnt[i] -= 1
                    if cnt[i] == 0:
                        rank[i] = rank[j] + 1
                        q.append(i)
        return rank

    def coop_reach(self, start, rank):
        """R2 view: can the goal be reached if nature cooperates (any path to a rank-0 node)?"""
        seen, q = {start}, deque([start])
        while q:
            i = q.popleft()
            if rank[i] == 0:
                return True
            for j, _ in self.succ[i]:
                if j not in seen:
                    seen.add(j)
                    q.append(j)
        return False


def fmt_action(a):
    if a[0] == 'push':
        return 'push boulder %s %s' % (a[1], DNAME[a[2]])
    if a[0] == 'enter':
        return 'step onto trap %s' % (a[1],)
    return 'nature lands hero on %s' % ' or '.join(map(str, a[1]))


def strategy_tree(G, start, rank, max_lines=60):
    """Hero strategy as an indented tree of macro-moves (walking inside a region is free and not printed)."""
    out, label = [], {}

    def go(i, ind):
        if len(out) >= max_lines:
            return
        if i in label:
            out.append(ind + '(same as [%d])' % label[i])
            return
        label[i] = len(label)
        k = G.key[i]
        if rank[i] == 0:
            out.append(ind + '[%d] goal reachable on foot' % label[i])
            return
        if k[0] == 'P':
            j, a = min(((j, a) for j, a in G.succ[i] if rank[j] is not None and rank[j] < rank[i]),
                       key=lambda t: rank[t[0]])
            out.append(ind + '[%d] %s' % (label[i], fmt_action(a)))
            go(j, ind)
        else:
            out.append(ind + '[%d] nature: %d choice(s)' % (label[i], len(G.succ[i])))
            for j, a in G.succ[i]:
                out.append(ind + '  - ' + fmt_action(a))
                go(j, ind + '    ')
    go(start, '')
    if len(out) >= max_lines:
        out.append('... (truncated at %d lines)' % max_lines)
    return out


def counter_strategy(G, start, rank, max_lines=40):
    """Nature's counter-strategy: at every losing nature node pick a losing landing; list the ones reachable from
    start when nature follows it and the hero plays anything."""
    M = G.M
    seen, q, out = {start}, deque([start]), []
    nat = 0
    while q:
        i = q.popleft()
        k = G.key[i]
        if k[0] == 'N':
            nat += 1
            j, a = next((j, a) for j, a in G.succ[i] if rank[j] is None) if G.succ[i] else (None, None)
            if len(out) < max_lines:
                alts = ' | '.join('/'.join(map(str, x[1][1])) for x in G.succ[i])
                out.append('boulders %s, trap %s: %s   (options: %s)' % (
                    M.cellset(k[1]), M.cells[k[3]][0], fmt_action(a) if a else 'EMPTY LANDING SET',
                    alts or '-'))
            succs = [j] if j is not None else []
        else:
            succs = [j for j, _ in G.succ[i]]
        for j in succs:
            if j not in seen:
                seen.add(j)
                q.append(j)
    return nat, len(seen), out


def all_ports(L):
    ports = dict(L.ports)
    if L.start:
        ports.setdefault('@', L.start)
    if L.goal:
        ports.setdefault('G', L.goal)
    return ports


# ----------------------------------------------------------------------------------------------- export for Rust
def export(M, path, starts_named=None):
    """Compressed model in the D-model v1 text format read by D_game.rs (see D-checker.md)."""
    L = M.L
    ns, D = M.ns, M.D
    bitnodes = lambda mask: [ns + i for i in range(mask.bit_length()) if (mask >> i) & 1]
    w = []
    w.append('DMODEL 1 %d %d %d %d' % (M.N, ns, D, len(M.trapl)))
    for n in range(M.N):
        x, y = M.cells[n][0]
        w.append('CELL %d %d %d %d' % (n, x, y, len(M.cells[n])))
    w.append('H ' + ' '.join(map(str, bitnodes(M.hole_bits))))
    for nm, s in sorted(L.states.items()):
        w.append('STATE %s %s' % (nm, ' '.join(map(str, bitnodes(M.bmask(s))))))
    for nm, c in sorted(all_ports(L).items()):
        w.append('PORT %s %d' % (nm, M.node[c]))
    for u in range(M.N):
        vs = [v for v in range(M.N) if (M.un_mask[u] >> v) & 1]
        if vs:
            w.append('U %d %s' % (u, ' '.join(map(str, vs))))
    for u, lst in enumerate(M.co):
        for v, conds in lst:
            for c in conds:
                w.append('C %d %d %s' % (u, v, ' '.join(map(str, bitnodes(c)))))
    for u, lst in enumerate(M.tent):
        for t, conds in lst:
            for c in ([None] if conds is None else conds):
                w.append('TE %d %d%s' % (u, t, '' if c is None else ' ' + ' '.join(map(str, bitnodes(c)))))
    for i, lst in enumerate(M.pushes):
        for hn, tb, d in lst:
            w.append('P %d %d %d %s' % (ns + i, hn, ns + tb.bit_length() - 1, DNAME[d]))
        for hn, tcell, d in M.vpush[i]:
            w.append('PV %d %d %d %s' % (ns + i, hn, M.node[tcell], DNAME[d]))
    for t in sorted(M.land):
        w.append('L %d %s' % (t, ' '.join('%d:%d,%d' % (n, c[0], c[1]) for n, _, c in M.land[t])))
    with open(path, 'w') as fh:
        fh.write('\n'.join(w) + '\n')


# ----------------------------------------------------------------------------------------------- front ends
def solve(L, start=None, goal=None, state='init', goal_state=None, max_states=5_000_000, tree_lines=60):
    M = Model(L)
    sc, gc = L.cell_of(start, L.start), L.cell_of(goal, L.goal)
    assert sc in M.node and sc not in L.traps, ('bad start', sc)
    bm, hm = M.bmask(L.states[state]), M.hole_bits
    assert M.free(M.node[sc], bm, hm), 'start cell blocked'
    t0 = time.time()
    G = Game(M, [(bm, hm, M.node[sc])], max_states)
    gs = None if goal_state is None else (M.bmask(L.states[goal_state]), M.hole_bits)
    rank = G.attractor(M.node[gc], gs)
    s = G.starts[0]
    res = dict(result='WIN' if rank[s] is not None else 'LOSE',
               player_nodes=sum(k[0] == 'P' for k in G.key), nature_nodes=sum(k[0] == 'N' for k in G.key),
               winning_nodes=sum(r is not None for r in rank), rank=rank[s], coop_reach=G.coop_reach(s, rank),
               violations=len(G.violations), landing_cell_blocked_states=G.landing_boulder,
               graph_nodes=M.N, dyn_cells=M.D, traps=len(M.trapl), secs=round(time.time() - t0, 3))
    vio = ['%s at node %d: %s' % (k, i, d) for k, i, d in G.violations[:10]]
    for t, r in coin_lint(L).items():
        if not (r['Z1_ok'] and r['Z2_ok']):
            vio.append('LINT trap %s: %s' % (t, {k: v for k, v in r.items() if v}))
    if rank[s] is not None:
        lines = strategy_tree(G, s, rank, tree_lines)
    else:
        nat, reach, lines = counter_strategy(G, s, rank)
        lines = ['nature nodes reachable under its counter-strategy: %d (positions %d)' % (nat, reach)] + lines
    return res, lines, vio


def relation(L, max_states=5_000_000):
    """Traversal relation of a gadget window: for every named start state s and ports p, q (p != q):
    WIN(s, p -> q) (any exit state) and, for each named state s', WIN(s, p -> q ending in s')."""
    M = Model(L)
    ports = all_ports(L)
    starts, labels = [], []
    for sn, sb in sorted(L.states.items()):
        bm = M.bmask(sb)
        for pn, pc in sorted(ports.items()):
            if pc in L.traps or not M.free(M.node[pc], bm, M.hole_bits):
                continue
            starts.append((bm, M.hole_bits, M.node[pc]))
            labels.append((sn, pn))
    G = Game(M, starts, max_states)
    rel = []
    for qn, qc in sorted(ports.items()):
        targets = [('*', None)] + [(sn, (M.bmask(sb), M.hole_bits)) for sn, sb in sorted(L.states.items())]
        for en, gs in targets:
            rank = G.attractor(M.node[qc], gs)
            for (sn, pn), si in zip(labels, G.starts):
                if pn != qn:
                    rel.append(dict(state=sn, frm=pn, to=qn, exit_state=en, win=rank[si] is not None,
                                    coop=G.coop_reach(si, rank)))
    return dict(positions=len(G.key), violations=[(k, d) for k, _, d in G.violations[:20]],
                n_violations=len(G.violations)), rel


RUST_SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'D_game.rs')
RUST_EXE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'target', 'D_game' + ('.exe' if os.name == 'nt' else ''))


def build_rust():
    if not os.path.exists(RUST_EXE) or os.path.getmtime(RUST_EXE) < os.path.getmtime(RUST_SRC):
        os.makedirs(os.path.dirname(RUST_EXE), exist_ok=True)
        subprocess.check_call(['rustc', '-C', 'opt-level=3', '-C', 'target-cpu=native', '--edition', '2021',
                               '-o', RUST_EXE, RUST_SRC])
    return RUST_EXE


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('level')
    ap.add_argument('--start', help="port name, '@', or 'x,y' (default '@')")
    ap.add_argument('--goal', help="port name, 'G', or 'x,y' (default 'G')")
    ap.add_argument('--state', default='init', help='named start boulder state')
    ap.add_argument('--goal-state', help='require this named boulder state at the goal')
    ap.add_argument('--relation', action='store_true', help='gadget traversal relation over all ports')
    ap.add_argument('--export', help='write the D-model v1 file for D_game.rs and exit')
    ap.add_argument('--rust', action='store_true', help='export to a temp model and solve with D_game.rs')
    ap.add_argument('--max-states', type=int, default=5_000_000)
    ap.add_argument('--tree', type=int, default=60, help='max lines of the strategy summary')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--lint', action='store_true', help='only the static coin checks Z1/Z2 (C-audit.md)')
    a = ap.parse_args()
    L = Level(open(a.level).read())
    if a.lint:
        for t, r in coin_lint(L).items():
            print('trap', t, r)
        return
    if a.export or a.rust:
        path = a.export or os.path.join(os.path.dirname(RUST_EXE), os.path.basename(a.level) + '.dmodel')
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        export(Model(L), path)
        if a.export:
            print('exported', path)
            return
        cmd = [build_rust(), path, '--max-states', str(a.max_states), '--tree', str(a.tree)]
        for f, v in (('--start', a.start), ('--goal', a.goal), ('--state', a.state), ('--goal-state', a.goal_state)):
            if v:
                cmd += [f, v]
        if a.relation:
            cmd.append('--relation')
        sys.exit(subprocess.call(cmd))
    if a.relation:
        info, rel = relation(L, a.max_states)
        if a.json:
            print(json.dumps(dict(info=info, relation=rel)))
            return
        print('positions %d, violations %d %s' % (info['positions'], info['n_violations'], info['violations'][:3]))
        for r in rel:
            print('%-6s %s -> %s exit=%-6s %s%s' % (r['state'], r['frm'], r['to'], r['exit_state'],
                                                   'WIN ' if r['win'] else 'lose', '' if r['win'] or not r['coop']
                                                   else '  (coop-reachable: nature blocks)'))
        return
    res, lines, vio = solve(L, a.start, a.goal, a.state, a.goal_state, a.max_states, a.tree)
    if a.json:
        print(json.dumps(dict(res, summary=lines, violation_examples=vio)))
        return
    print('RESULT', ' '.join('%s=%s' % kv for kv in res.items()))
    for v in vio:
        print(v if v.startswith('LINT') else 'VIOLATION ' + v)
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
