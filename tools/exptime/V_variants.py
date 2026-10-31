#!/usr/bin/env python3
"""V_variants.py -- G6 rule variants vs the EXPTIME reduction (proofs/exptime/V-variants.md).

The SC79 text of G6 is not available, so the rules are uncertain. This script fixes a variant
  v = (first, pas, check, init)
    first : 'I' | 'II'                    who moves first (SC79 positions carry tau = player to move)
    pas   : True | False                  passing allowed ("at most one") | forbidden ("exactly one" flip)
    check : 'every' | 'postI' | 'postII'  F checked after every move | only after I's moves | only after II's moves
    init  : True | False                  the initial position counts (F(alpha0) true => I wins at once)
  infinite play = non-win for I (Chung; the other reading makes every instance YES, see V-variants.md)
and compares, on random instances, the exact G6 value with
  BASE : the arena of B §3 exactly as review5_t1.build makes it (+ B's pre-processing: II first and F(alpha0)
         true => fixed YES), i.e. what the generator L_gen currently produces;
  ADAPT: the arena adapted to the variant (build_variant):
         - pas=False: per variable v two gate doors G_v^0, G_v^1 (exactly G_v^{alpha(v)} open); every write path is
           a FLIP: W(v: 1-b -> b) = S(G_v^{1-b}) (forced close; passable only if v = 1-b) -> forced closes of the
           false literals -> optional opens of the true literals -> O(G_v^b) -> exit. No pass corridor, no pass leaf;
           nature's menu = {flip y_j}, leaf route = fork into the two gated flips (only one is passable);
         - check: the dead-end checker c_0 is reachable from P (post-I vertex) iff check in {every, postI} and from
           a new post-II vertex Q (all leaf routes exit to Q, Q -> h) iff check in {every, postII};
         - init: start vertex s0 -> c_0 (iff init) and s0 -> h / N_in (first mover). This replaces B's
           pre-processing.
Realizations: 'mscd' (ideal multi-tunnel doors) and 'ts' (Lemma TS: plain SCDs only, = what L_gen consumes).
--s1 runs the ADAPT 'ts' arena through L_gen.netlist + solve_net (S1: netlist of diodes/SCDs/coin), and --s2 K also
through the bus layout and its re-read network (S2), for K instances per variant.

Usage:
  python V_variants.py [--trials N] [--seed S] [--s1] [--s2 K] [--sym | --asym | --pas pass|nopass|passI|passII]
                       [--only first,pas,check,init]
                       [--dnf]   (F read as DNF, checker = fork over terms: for Chung 2026 Thm 22, see V-variants.md)
  python V_variants.py --equiv   (which variants are the same G6 problem, on 1,500 random instances)
  (S1/S2 attractors over 8 M positions are skipped and counted as 'cap'.)
"""
import itertools, json, os, random, sys, time, zlib
from collections import deque

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import review5_t1 as R5

OTHER = {'I': 'II', 'II': 'I'}


# ============================================================ G6 solver, parameterized
def may_pass(pas, p):
    """pas: True (both may pass) | False (neither) | 'I' | 'II' (only that player may pass)."""
    return pas is True or pas == p


FORM = 'cnf'          # 'dnf': F is a list of TERMS (any term with all literals true); set by --dnf


def sat(F, a):
    if FORM == 'dnf':
        return any(all(a[v] == s for v, s in C) for C in F)
    return all(any(a[v] == s for v, s in C) for C in F)


def g6_variant(F, X, Y, alpha0, v):
    """exact value of G6 under variant v for Player I (reachability; infinite play = non-win)."""
    first, pas, check, init = v
    V = X + Y
    idx = {x: i for i, x in enumerate(V)}
    if init and sat(F, alpha0):
        return True
    pos = list(itertools.product((0, 1), repeat=len(V)))

    def checked(p):                      # p = player to move; the last mover was OTHER[p]
        last = OTHER[p]
        return check == 'every' or (check == 'postI' and last == 'I') or (check == 'postII' and last == 'II')

    def moves(a, p):
        own = X if p == 'I' else Y
        pp = may_pass(pas, p)
        out = [a] if pp else []
        for x in own:
            i = idx[x]
            if pp:
                for b in (0, 1):
                    out.append(a[:i] + (b,) + a[i + 1:])
            else:
                out.append(a[:i] + (1 - a[i],) + a[i + 1:])
        return out

    term = {}
    for a in pos:
        for p in ('I', 'II'):
            term[(a, p)] = checked(p) and sat(F, dict(zip(V, a)))
    win = dict(term)
    changed = True
    while changed:
        changed = False
        for a in pos:
            for p in ('I', 'II'):
                if win[(a, p)]:
                    continue
                vals = [win[(s, OTHER[p])] for s in moves(a, p)]
                if (p == 'I' and vals and any(vals)) or (p == 'II' and vals and all(vals)):
                    win[(a, p)] = True
                    changed = True
    a0 = tuple(alpha0[x] for x in V)
    p0 = first
    vals = [win[(s, OTHER[p0])] for s in moves(a0, p0)]
    return any(vals) if p0 == 'I' else (bool(vals) and all(vals))


# ============================================================ arena builder, parameterized
def build_variant(F, X, Y, alpha0, v, mode='mscd', ArenaCls=None, gates=True, qcheck=True, startfork=True):
    """B §3 arena adapted to variant v (see module doc). gates/qcheck/startfork switch the three adaptations off
    individually (negative controls). Returns ArenaCls.solve(...) (= (win, #positions) for R5.Arena)."""
    first, pas, check, init = v
    A = (ArenaCls or R5.Arena)()
    occ = [(x, s, j) for j, C in enumerate(F) for (x, s) in C]
    D = {k: A.door() for k in range(len(occ))}
    init_open = [D[k] for k, (x, s, j) in enumerate(occ) if alpha0[x] == s]
    users = {}                                       # door -> {'O': [(u, v)], 'S': [(u, v)]}

    def use(door, kind, u, w):
        users.setdefault(door, {'O': [], 'S': []})[kind].append((u, w))

    gate = {}
    pI, pII = may_pass(pas, 'I') or not gates, may_pass(pas, 'II') or not gates
    if gates:
        for x in (X if not pI else []) + (Y if not pII else []):
            gate[x] = {b: A.door() for b in (0, 1)}
            init_open.append(gate[x][alpha0[x]])

    def write(x, b, entry, exit_):
        cur = entry
        if x in gate:                                # flip only if x currently = 1-b
            a = A.node('g')
            use(gate[x][1 - b], 'S', cur, a)
            cur = a
        for k, (vv, s, j) in enumerate(occ):
            if vv == x and s != b:                   # literal false after the write: forced close
                a, c2 = A.node('o2'), A.node('s1')
                use(D[k], 'O', cur, a)
                use(D[k], 'S', a, c2)
                cur = c2
        for k, (vv, s, j) in enumerate(occ):
            if vv == x and s == b:                   # literal true after the write: optional open
                a = A.node('o1')
                use(D[k], 'O', cur, a)
                cur = a
        if x in gate:
            a = A.node('g')
            use(gate[x][b], 'O', cur, a)
            cur = a
        A.e(cur, exit_)

    h, P, g = A.node('h'), A.node('P'), A.node('g')
    for x in X:
        for b in (0, 1):
            w = A.node(f'W{x}{b}')
            A.e(h, w)
            write(x, b, w, P)
    if pI:
        A.e(h, P)                                    # pass corridor
    c = [A.node(f'c{j}') for j in range(len(F) + 1)]
    if FORM == 'dnf':                                # c_0 forks over the terms; term j = chain of S2 tunnels -> c_m
        for j, C in enumerate(F):
            cur = c[0]
            ks = [k for k, (x, s, jj) in enumerate(occ) if jj == j]
            for i, k in enumerate(ks):
                nxt = c[-1] if i == len(ks) - 1 else A.node('t')
                use(D[k], 'S', cur, nxt)
                cur = nxt
    else:
        for k, (x, s, j) in enumerate(occ):
            use(D[k], 'S', c[j], c[j + 1])
    A.e(c[-1], g)
    Nin = A.node('Nin')
    A.e(P, Nin)
    if check in ('every', 'postI') or not qcheck:
        A.e(P, c[0])
    Q = A.node('Q')
    if qcheck and check in ('every', 'postII'):
        A.e(Q, c[0])
    A.e(Q, h)
    # nature module
    if pII:
        menu = ['pass'] + [(y, b) for y in Y for b in (0, 1)]
    else:
        menu = [('flip', y) for y in Y]
    if not menu:                                     # no-pass and Y empty: II has no legal move (excluded)
        raise ValueError('II has no legal move')
    d = 0
    while (1 << d) < len(menu):
        d += 1

    def leaf_route(lab, entry):
        if lab == 'pass':
            A.e(entry, Q)
        elif lab[0] == 'flip':
            for b in (0, 1):
                w = A.node('Wf')
                A.e(entry, w)
                write(lab[1], b, w, Q)
        else:
            write(lab[0], lab[1], entry, Q)
    K_users = {}
    if d == 0:
        leaf_route(menu[0], Nin)
    else:
        EC, T, Aa, Bb = A.node('EC'), A.node('T'), A.node('A'), A.node('B')
        A.coin = (T, [Aa, Bb])
        A.e(EC, T)
        HA, HB = A.node('HA'), A.node('HB')
        A.e(Aa, HA)
        A.e(Bb, HB)
        arrive = {u: A.node(f'arr{u}') for u in range(1, 1 << (d + 1))}
        Kd = {u: A.door() for u in range(1, 1 << d)}
        for u in Kd:
            use(Kd[u], 'O', arrive[u], EC)
            use(Kd[u], 'S', HA, arrive[2 * u])
            use(Kd[u], 'S', HB, arrive[2 * u + 1])
        A.e(Nin, arrive[1])
        for i, leaf in enumerate(range(1 << d, 1 << (d + 1))):
            leaf_route(menu[i % len(menu)] if not pII else (menu[i] if i < len(menu) else 'pass'),
                       arrive[leaf])
    # realize doors (same code as review5_t1.build)
    for door, us in users.items():
        for kind in ('O', 'S'):
            lst = us[kind]
            if mode != 'ts' or len(lst) <= 1:
                for (u, w) in lst:
                    A.e(u, w, kind, door)
                continue
            m, m2 = A.node('m'), A.node("m'")
            ctx = []
            for (u, w) in lst:
                kp = A.door()
                x_ = A.node('x')
                A.e(u, x_, 'O', kp)
                A.e(x_, m)
                ctx.append((kp, w))
            A.e(m, m2, kind, door)
            for kp, w in ctx:
                A.e(m2, w, 'S', kp)
    entry = h if first == 'I' else Nin
    if startfork:
        s0 = A.node('s0')
        A.e(s0, entry)
        if init:
            A.e(s0, c[0])
        start = s0
    else:
        start = entry
    return A.solve(start, g, init_open)


def base_value(F, X, Y, alpha0, v, mode='mscd', pre=True):
    """the current generator's arena (review5_t1.build) + B's pre-processing (if pre), for the given first mover."""
    first = v[0]
    if pre and first == 'II' and sat(F, alpha0):
        return True                                  # B §1.1 pre-processing: fixed YES instance
    return R5.build(F, X, Y, alpha0, mode, first)[0]


# ============================================================ S1 / S2 through L_gen
CAP = 8_000_000


def s1s2(inst, v, do_s2=False):
    import L_gen as LG

    class Rec(R5.Arena):
        def solve(self, start, goal, init_open, cap=0):
            return self, start, goal, init_open

    def arena(_inst, mode='ts'):
        A, start, goal, init_open = build_variant(inst['F'], inst['X'], inst['Y'], inst['a0'], v, 'ts', Rec)
        return A, start, goal, set(init_open)
    saved = LG.arena
    LG.arena = arena
    try:
        N = LG.netlist(inst)
    finally:
        LG.arena = saved
    try:
        w1, n1 = LG.solve_net(N, cap=CAP)
    except RuntimeError:
        return 'cap', None
    if not do_s2:
        return w1, None
    LG.contract(N)
    B = LG.Bus(N)
    B.order()
    B.rows()
    Lv = LG.Level(B)
    Lv.blocks()
    Lv.check_static()
    paths = Lv.trace()
    Nn = Lv.network(paths)
    try:
        w2, n2 = LG.solve_net(Nn, cap=CAP)
    except RuntimeError:
        w2 = 'cap'
    return w1, w2


# ============================================================ instances and driver
def random_instance(rng, pas):
    """review5_t1's distribution; with passing forbidden both variable sets are nonempty (else a player has no
    legal move: SC79/Chung avoid this, Chung Lemma 3 adds a fresh variable per player)."""
    shapes = [(1, 1), (1, 2), (2, 1), (2, 2), (0, 1), (1, 0)]
    shapes = [(a, b) for a, b in shapes if (a or may_pass(pas, 'I')) and (b or may_pass(pas, 'II'))]
    nx, ny = rng.choice(shapes)
    X = [f'x{i}' for i in range(nx)]
    Y = [f'y{i}' for i in range(ny)]
    V = X + Y
    m = rng.randint(1, 3)
    F = []
    for _ in range(m):
        w = rng.randint(1, min(3, len(V)))
        F.append([(x, rng.randint(0, 1)) for x in rng.sample(V, w)])
    a0 = {x: rng.randint(0, 1) for x in V}
    return F, X, Y, a0


VARIANTS = [(f, p, c, i) for p in (True, False, 'I', 'II') for c in ('every', 'postI', 'postII') for i in (True, False)
            for f in ('I', 'II')]


def vname(v):
    f, p, c, i = v
    return f"{f}-first/{ {True: 'pass', False: 'nopass', 'I': 'passI', 'II': 'passII'}[p]}/{c}/{'init' if i else 'noinit'}"


def equiv(n=1500, seed=42):
    """group all 48 variants by their G6 values on n random instances (|X|, |Y| <= 3, <= 4 clauses)."""
    rng = random.Random(seed)
    vals = {v: [] for v in VARIANTS}
    for t in range(n):
        nx, ny = rng.choice([(1, 1), (1, 2), (2, 1), (2, 2), (2, 3), (3, 2)])
        X = [f'x{i}' for i in range(nx)]
        Y = [f'y{i}' for i in range(ny)]
        V = X + Y
        F = []
        for _ in range(rng.randint(1, 4)):
            w = rng.randint(1, min(3, len(V)))
            F.append([(x, rng.randint(0, 1)) for x in rng.sample(V, w)])
        a0 = {x: rng.randint(0, 1) for x in V}
        for v in VARIANTS:
            vals[v].append(g6_variant(F, X, Y, a0, v))
    classes = []
    for v in VARIANTS:
        for c in classes:
            if vals[c[0]] == vals[v]:
                c.append(v)
                break
        else:
            classes.append([v])
    for c in classes:
        print(f'{sum(vals[c[0]]):5d} YES | ' + ' = '.join(vname(v) for v in c))


def main():
    a = sys.argv[1:]
    if '--equiv' in a:
        return equiv()
    trials = int(a[a.index('--trials') + 1]) if '--trials' in a else 300
    seed = int(a[a.index('--seed') + 1]) if '--seed' in a else 1
    do_s1 = '--s1' in a
    global FORM
    if '--dnf' in a:
        FORM = 'dnf'
    k_s2 = int(a[a.index('--s2') + 1]) if '--s2' in a else 0
    variants = VARIANTS
    if '--asym' in a:
        variants = [v for v in VARIANTS if v[1] in ('I', 'II')]
    elif '--sym' in a:
        variants = [v for v in VARIANTS if v[1] in (True, False)]
    if '--pas' in a:
        want = {'pass': True, 'nopass': False, 'passI': 'I', 'passII': 'II'}[a[a.index('--pas') + 1]]
        variants = [v for v in variants if v[1] == want]
    if '--only' in a:
        f, p, c, i = a[a.index('--only') + 1].split(',')
        variants = [(f, {'pass': True, 'nopass': False, 'passI': 'I', 'passII': 'II'}[p], c, i == 'init')]
    report = []
    t0 = time.time()
    for v in variants:
        rng = random.Random(zlib.crc32(vname(v).encode()) + seed * 7919)
        st = dict(variant=vname(v), n=0, yes=0, base_bad=0, raw_bad=0, mscd_bad=0, ts_bad=0, s1=0, s1_bad=0, s2=0, s2_bad=0,
                  nc_bad={}, maxpos=0, examples=[])
        ncs = []
        if v[1] is not True:
            ncs.append('gates')
        if v[2] != 'postI':
            ncs.append('qcheck')
        if v[3] or v[0] == 'II':
            ncs.append('startfork')
        for t in range(trials):
            F, X, Y, a0 = random_instance(rng, v[1])
            truth = g6_variant(F, X, Y, a0, v)
            st['n'] += 1
            st['yes'] += truth
            b = base_value(F, X, Y, a0, v)
            if b != truth:
                st['base_bad'] += 1
                if len(st['examples']) < 2:
                    st['examples'].append(dict(F=F, X=X, Y=Y, a0=a0, g6=truth, base=b))
            st['raw_bad'] += (base_value(F, X, Y, a0, v, pre=False) != truth)
            w, n = build_variant(F, X, Y, a0, v, 'mscd')
            st['maxpos'] = max(st['maxpos'], n)
            st['mscd_bad'] += (w != truth)
            w, n = build_variant(F, X, Y, a0, v, 'ts')
            st['maxpos'] = max(st['maxpos'], n)
            st['ts_bad'] += (w != truth)
            for nc in ncs:
                kw = {nc: False}
                wn = build_variant(F, X, Y, a0, v, 'mscd', **kw)[0]
                st['nc_bad'][nc] = st['nc_bad'].get(nc, 0) + (wn != truth)
            if do_s1 or t < k_s2:
                inst = dict(F=F, X=X, Y=Y, a0=a0, first=v[0])
                w1, w2 = s1s2(inst, v, do_s2=t < k_s2)
                if w1 == 'cap':
                    st['s1_cap'] = st.get('s1_cap', 0) + 1
                else:
                    st['s1'] += 1
                    st['s1_bad'] += (w1 != truth)
                if w2 == 'cap':
                    st['s2_cap'] = st.get('s2_cap', 0) + 1
                elif w2 is not None:
                    st['s2'] += 1
                    st['s2_bad'] += (w2 != truth)
        report.append(st)
        print(f"{st['variant']:32s} n={st['n']} yes={st['yes']} BASE pre/raw bad={st['base_bad']}/{st['raw_bad']} ADAPT mscd bad="
              f"{st['mscd_bad']} ts bad={st['ts_bad']} S1 {st['s1_bad']}/{st['s1']} S2 {st['s2_bad']}/{st['s2']} "
              f"NC {st['nc_bad']} cap {st.get('s1_cap', 0)}/{st.get('s2_cap', 0)} maxpos={st['maxpos']}  [{time.time()-t0:.0f}s]", flush=True)
    out = os.path.join(HERE, '..', '..', 'build', 'variants')
    os.makedirs(out, exist_ok=True)
    tag = 'asym' if '--asym' in a else 'sym' if '--sym' in a else 'all'
    if '--pas' in a:
        tag = a[a.index('--pas') + 1]
    if FORM == 'dnf':
        tag = 'dnf_' + tag
    with open(os.path.join(out, f'report_{tag}_seed{seed}_{trials}{"_s1" if do_s1 else ""}.json'), 'w') as fh:
        json.dump(report, fh, indent=1)
    ok = all(r['mscd_bad'] == 0 and r['ts_bad'] == 0 and r['s1_bad'] == 0 and r['s2_bad'] == 0 for r in report)
    print('ADAPTED ARENA = G6 ON EVERY VARIANT TESTED' if ok else 'MISMATCH FOUND')


if __name__ == '__main__':
    main()
