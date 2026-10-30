#!/usr/bin/env python3
"""review5_t1.py -- adversarial review 5, item 2: exhaustive test of B-reduction.md Theorem T1 on small G6 instances.

Builds the abstract game G_F of B §3 (literal doors MSCD(2,2), write paths, hub, P, checker, nature tree with context
doors K_u and ONE coin) and solves it exactly (attractor: hero = existential, coin = universal, infinite = loss).
Compares with G6 solved directly (positions (alpha, player); I wins iff F true at some position, initial included).
Two door realizations:
  'mscd' : ideal multi-tunnel doors (one bit, tunnels share it), O open-optional, S forced close;
  'ts'   : every multi-user tunnel kind replaced by Lemma TS (one SCD + context SCDs + merge/split), plain SCDs only.
Every edge is directed (diodes implicit). Also a deliberately wrong variant ('noforce': write path skips the forced
closes of false literals) as a negative control: it must disagree on some instance.
Usage: python review5_t1.py [trials] [seed]
"""
import itertools, random, sys
from collections import deque


class Arena:
    def __init__(self):
        self.edges = {}          # node -> list of (kind, target, door)
        self.ndoor = 0
        self.k = 0
        self.coin = None         # (T, [A, B])

    def node(self, tag):
        self.k += 1
        return f'{tag}#{self.k}'

    def door(self):
        self.ndoor += 1
        return self.ndoor - 1

    def e(self, u, v, kind='plain', d=None):
        self.edges.setdefault(u, []).append((kind, v, d))
        self.edges.setdefault(v, [])

    def solve(self, start, goal, init_open, cap=3_000_000):
        bits0 = 0
        for d in init_open:
            bits0 |= 1 << d
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
        add((start, bits0))
        T = self.coin[0] if self.coin else None
        while dq:
            i = dq.popleft()
            u, b = key[i]
            out = []
            if u != goal:
                if u == T:
                    out = [add((o, b)) for o in self.coin[1]]
                else:
                    for kind, v, d in self.edges.get(u, []):
                        if kind == 'plain':
                            out.append(add((v, b)))
                        elif kind == 'O':
                            out.append(add((v, b)))
                            out.append(add((v, b | (1 << d))))
                        elif kind == 'S':
                            if b >> d & 1:
                                out.append(add((v, b & ~(1 << d))))
            succ[i] = sorted(set(out))
            if len(key) > cap:
                raise RuntimeError('cap')
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
                if key[i][0] == T:
                    cnt[i] -= 1
                    if cnt[i] == 0:
                        win[i] = True
                        q.append(i)
                else:
                    win[i] = True
                    q.append(i)
        return win[0], n


def build(F, X, Y, alpha0, mode, first='I'):
    """F: list of clauses, clause = list of (var, sign) (sign 1 = positive literal). alpha0: dict var -> 0/1."""
    A = Arena()
    occ = [(v, s, j) for j, C in enumerate(F) for (v, s) in C]          # occurrence k = (var, sign, clause)
    D = {k: A.door() for k in range(len(occ))}
    init_open = [D[k] for k, (v, s, j) in enumerate(occ) if alpha0[v] == s]
    users = {k: {'O': [], 'S': []} for k in D}          # tunnel uses (u, v) collected per occurrence door
    K_users = {}

    def lit_true(v, s, b):
        return s == b

    def write(v, b, entry, exit_):
        cur = entry
        if mode != 'noforce':
            for k, (vv, s, j) in enumerate(occ):
                if vv == v and not lit_true(vv, s, b):
                    a = A.node('o2')
                    users[k]['O'].append((cur, a))
                    c2 = A.node('s1')
                    users[k]['S'].append((a, c2))
                    cur = c2
        for k, (vv, s, j) in enumerate(occ):
            if vv == v and lit_true(vv, s, b):
                a = A.node('o1')
                users[k]['O'].append((cur, a))
                cur = a
        A.e(cur, exit_)

    h, P, g = A.node('h'), A.node('P'), A.node('g')
    for x in X:
        for b in (0, 1):
            w = A.node(f'W{x}{b}')
            A.e(h, w)
            write(x, b, w, P)
    A.e(h, P)                                           # pass corridor
    c = [A.node(f'c{j}') for j in range(len(F) + 1)]
    A.e(P, c[0])
    Nin = A.node('Nin')
    A.e(P, Nin)
    for k, (v, s, j) in enumerate(occ):
        users[k]['S'].append((c[j], c[j + 1]))
    A.e(c[-1], g)
    # nature module
    menu = ['pass'] + [(y, b) for y in Y for b in (0, 1)]
    d = 0
    while (1 << d) < len(menu):
        d += 1
    if d == 0:
        A.e(Nin, h)
    else:
        EC, T, Aa, Bb = A.node('EC'), A.node('T'), A.node('A'), A.node('B')
        A.coin = (T, [Aa, Bb])
        A.e(EC, T)
        HA, HB = A.node('HA'), A.node('HB')
        A.e(Aa, HA)
        A.e(Bb, HB)
        # tree nodes: heap indexing 1.., internal 1..2^d-1, leaves 2^d..2^{d+1}-1
        arrive = {u: A.node(f'arr{u}') for u in range(1, 1 << (d + 1))}
        Kd = {u: A.door() for u in range(1, 1 << d)}
        for u in Kd:
            K_users[u] = {'O': [(arrive[u], EC)], 'S': [(HA, arrive[2 * u]), (HB, arrive[2 * u + 1])]}
        A.e(Nin, arrive[1])
        for i, leaf in enumerate(range(1 << d, 1 << (d + 1))):
            lab = menu[i] if i < len(menu) else 'pass'
            if lab == 'pass':
                A.e(arrive[leaf], h)
            else:
                write(lab[0], lab[1], arrive[leaf], h)
    # realize doors
    def realize(door, us):
        for kind in ('O', 'S'):
            lst = us[kind]
            if mode != 'ts' or len(lst) <= 1:
                for (u, v) in lst:
                    A.e(u, v, kind, door)
                continue
            m, m2 = A.node('m'), A.node("m'")
            ctx = []
            for (u, v) in lst:
                kp = A.door()                       # context SCD, initially closed
                x = A.node('x')
                A.e(u, x, 'O', kp)
                A.e(x, m)
                ctx.append((kp, v))
            A.e(m, m2, kind, door)
            for kp, v in ctx:
                A.e(m2, v, 'S', kp)
    for k in D:
        realize(D[k], users[k])
    if d:
        for u in Kd:
            realize(Kd[u], K_users[u])
    start = h if first == 'I' else Nin
    return A.solve(start, g, init_open)


def g6(F, X, Y, alpha0, first='I'):
    V = X + Y

    def sat(a):
        return all(any(a[v] == s for v, s in C) for C in F)
    pos = list(itertools.product((0, 1), repeat=len(V)))
    win = {}
    for a in pos:
        for p in ('I', 'II'):
            win[(a, p)] = sat(dict(zip(V, a)))
    changed = True
    while changed:
        changed = False
        for a in pos:
            for p in ('I', 'II'):
                if win[(a, p)]:
                    continue
                own = X if p == 'I' else Y
                succ = [a]
                for v in own:
                    i = V.index(v)
                    for b in (0, 1):
                        succ.append(a[:i] + (b,) + a[i + 1:])
                nxt = 'II' if p == 'I' else 'I'
                vals = [win[(s, nxt)] for s in succ]
                if (p == 'I' and any(vals)) or (p == 'II' and all(vals)):
                    win[(a, p)] = True
                    changed = True
    return win[(tuple(alpha0[v] for v in V), first)]


def main():
    trials = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    rng = random.Random(int(sys.argv[2]) if len(sys.argv) > 2 else 5)
    stats = {'mscd': [0, 0], 'ts': [0, 0], 'noforce': [0, 0]}
    yes = 0
    maxpos = 0
    for t in range(trials):
        nx, ny = rng.choice([(1, 1), (1, 2), (2, 1), (2, 2), (0, 1), (1, 0)])
        X = [f'x{i}' for i in range(nx)]
        Y = [f'y{i}' for i in range(ny)]
        V = X + Y
        m = rng.randint(1, 3)
        F = []
        for _ in range(m):
            w = rng.randint(1, min(3, len(V)))
            F.append([(v, rng.randint(0, 1)) for v in rng.sample(V, w)])
        a0 = {v: rng.randint(0, 1) for v in V}
        first = rng.choice(['I', 'II'])
        if first == 'II' and all(any(a0[v] == s for v, s in C) for C in F):
            first = 'I'       # B pre-processing answers this case directly (fixed YES instance)
        truth = g6(F, X, Y, a0, first)
        yes += truth
        for mode in ('mscd', 'ts', 'noforce'):
            if mode == 'ts' and len(V) > 3:
                pass
            try:
                w, n = build(F, X, Y, a0, mode, first)
            except RuntimeError:
                continue
            maxpos = max(maxpos, n)
            stats[mode][0] += 1
            if w != truth:
                stats[mode][1] += 1
                if mode != 'noforce' and stats[mode][1] <= 3:
                    print('MISMATCH', mode, 'F=', F, 'a0=', a0, 'first=', first, 'G6:', truth, 'game:', w)
    print(f'{trials} random instances ({yes} YES); max positions {maxpos}')
    for mode, (n, bad) in stats.items():
        print(f'  {mode:8s}: {n} solved, {bad} mismatches with G6')
    ok = stats['mscd'][1] == 0 and stats['ts'][1] == 0 and stats['noforce'][1] > 0
    print('T1 HOLDS ON ALL TESTED INSTANCES (negative control caught)' if ok else 'UNEXPECTED')


if __name__ == '__main__':
    main()
