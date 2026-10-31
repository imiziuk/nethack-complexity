#!/usr/bin/env python3
"""review6_weak.py -- review 6: does a check with one endpoint replaced by another own location still postselect?

If a hook (or the chain edge Op_i -> SD_i -> a_i) crosses the g-side stub of an own leg X with a WCX (L_gen's 'GX'),
the hero can use the WCX leak Bt->L/R: the check a_i -> b_i then also accepts a_i -> X (b-side hook crossing X's stub,
leak prepared from b_i's side) or X -> b_i (a-side edge crossing X's stub, leak taken at check time). This script
computes, for Ani's proto-precursor and protodiode, the clean set (check sequence legal) for the true checks and for
every single endpoint substitution, using A_core's exact traversal relation. Read-only imports.
"""
import sys
sys.path.insert(0, __file__.rsplit('\\', 1)[0].rsplit('/', 1)[0])
import A_core as K
import A2_scd as S2


def legal_from(bd, B, seq, memo):
    """seq: tuple of (set_of_start_ports, set_of_end_ports); True iff some realisation of the sequence is legal"""
    if not seq:
        return True
    key = (B, seq)
    if key in memo:
        return memo[key]
    (starts, ends), rest = seq[0], seq[1:]
    ok = False
    for p in starts:
        # a check traversal a->b may pass through other ports: closure of traversals until the hero stands on b
        seen = {(p, B)}
        st = [(p, B)]
        while st and not ok:
            q, Bc = st.pop()
            for r, B2 in bd.traversals(Bc, q):
                if r in ends and legal_from(bd, B2, rest, memo):
                    ok = True
                    break
                if (r, B2) not in seen:
                    seen.add((r, B2))
                    st.append((r, B2))
        if ok:
            break
    memo[key] = ok
    return ok


def run(name, rows, checks, locs):
    bd = K.Board(rows)
    C = K.explore(bd)
    states = sorted(C.states)
    base = tuple((frozenset([a]), frozenset([b])) for a, b in checks)
    clean = {B for B in states if legal_from(bd, B, base, {})}
    print(f'{name}: {len(states)} states, clean (true checks) {len(clean)}')
    worst = set(clean)
    for i, (a, b) in enumerate(checks):
        for side in (0, 1):
            for X in locs:
                if X in (a, b):
                    continue
                seq = list(base)
                s, e = seq[i]
                seq[i] = (s | {X}, e) if side == 0 else (s, e | {X})
                cl = {B for B in states if legal_from(bd, B, tuple(seq), {})}
                if cl != clean:
                    tag = f'{X}->{b}' if side == 0 else f'{a}->{X}'
                    print(f'   check {i} {a}->{b} also accepting {tag}: clean {len(cl)} (+{len(cl - clean)})')
                    worst |= cl
    print(f'   union over single substitutions: {len(worst)} "clean" states')


if __name__ == '__main__':
    # note: the check relation here is "reach port b" in the raw board (pockets D, G are port cells of the board)
    run('proto-precursor', S2.PROTO_PRECURSOR, S2.PP_CHECKS, sorted(set('ABCDEFG')))
    run('protodiode', S2.PROTODIODE, S2.PD_CHECKS, sorted(set('ABCD')))


def detail_protodiode():
    """the state the D-route/C-stub GX lets through, and its port relation (main-game behaviour)"""
    bd = K.Board(S2.PROTODIODE)
    C = K.explore(bd)
    true = (({'A'}, {'C'}), ({'D'}, {'B'}))
    weak = (({'A'}, {'C'}), ({'D', 'C'}, {'B'}))
    fz = lambda s: tuple((frozenset(a), frozenset(b)) for a, b in s)
    for B in sorted(C.states):
        t, w = legal_from(bd, B, fz(true), {}), legal_from(bd, B, fz(weak), {})
        rel = sorted({(p, q) for p in 'ABCD' for q, _ in bd.traversals(B, p) if q != p})
        print('  state', bd.show(B).replace('\n', ' | '), ' true-check', t, ' weak-check', w, ' moves', rel)


if __name__ == '__main__':
    print('protodiode, check D->B weakened to {D,C}->B (D-route crossing the C stub, L_gen diode tile):')
    detail_protodiode()


def precursor_generated():
    """crossings found on the generated SCD tile (review6_hooks2.py): B-route over the A stub, C-route over the A and
    B stubs. Ani placement (crossings on the chain edge Op_i -> SD_i -> a_i): B is a_i of checks 2, 3 -> start may be
    A; C is a_i of check 1 -> start may be A or B."""
    bd = K.Board(S2.PROTO_PRECURSOR)
    C = K.explore(bd)
    fz = lambda s: tuple((frozenset(a), frozenset(b)) for a, b in s)
    true = [({'A'}, {'D'}), ({'C'}, {'G'}), ({'B'}, {'A'}), ({'B'}, {'C'})]
    weak = [({'A'}, {'D'}), ({'C', 'A', 'B'}, {'G'}), ({'B', 'A'}, {'A'}), ({'B', 'A'}, {'C'})]
    ct = {B for B in C.states if legal_from(bd, B, fz(true), {})}
    cw = {B for B in C.states if legal_from(bd, B, fz(weak), {})}
    print(f'proto-precursor, generated-tile crossings, Ani placement: clean {len(ct)} -> {len(cw)}')
    for B in sorted(cw - ct):
        print('   extra:', bd.show(B).replace('\n', ' | '))


if __name__ == '__main__':
    precursor_generated()


def generated():
    """review-6 repair check on the GENERATED templates: route the dio and scdc tile blocks (both parities) with
    L_gen as it is now, read every own-stub GX on each check walk (events after the G''s last Wb, up to SD_i:
    Out_{i-1} -> Op_i -> SD_i, the curve that brings the walk to a_i under Ani placement), turn each into the
    endpoint substitution X -> b_i, and compare the clean set with the true one (2 / 3). With the repaired rule
    there is no own GX, so every clean set must equal the true one."""
    import random, os
    import L_gen as L
    rng = random.Random(1)
    inst = L.random_instance(rng)
    N = L.netlist(inst); L.contract(N)
    Bs = L.Bus(N); Bs.order(); Bs.rows()
    Lv = L.Level(Bs); Lv.blocks()
    boards = {'pp': S2.PROTO_PRECURSOR, 'pd': S2.PROTODIODE}
    checks = {'pp': S2.PP_CHECKS, 'pd': S2.PD_CHECKS}
    sysm = {k: (K.Board(v), K.explore(K.Board(v))) for k, v in boards.items()}
    fz = lambda s: tuple((frozenset(a), frozenset(b)) for a, b in s)
    allok = True
    for kind in ('dio', 'scdc'):
        tn = [t for t in Bs.tiles if Bs.tiles[t]['kind'] == kind][0]
        for par in (0, 1):
            r = L.block_template(Lv.tb[tn], par)
            Rt = r['router']
            for g in sorted(Rt.gseg, key=lambda g: (g['level'], g['e0'])):
                ck = g['kind']
                if ck not in boards:
                    continue
                evs = Rt.events[g['e0']:g['e1']]
                last_wb = max(k for k, e in enumerate(evs) if e[0] == 'Wb')
                subs = {i: set() for i in range(len(g['checks']))}
                i = 0
                for kind_, f, info in evs[last_wb + 1:]:
                    if kind_ == 'SD':
                        i = info[1] + 1
                    elif kind_ == 'GX' and Rt.leg.get(f) in g['own'] and i < len(g['checks']):
                        subs[i].add(Rt.leg[f][1].split('.')[-1])
                bd, C = sysm[ck]
                true = [({a}, {b}) for a, b in checks[ck]]
                weak = [({a} | subs[k], {b}) for k, (a, b) in enumerate(checks[ck])]
                ct = {B for B in C.states if legal_from(bd, B, fz(true), {})}
                cw = {B for B in C.states if legal_from(bd, B, fz(weak), {})}
                allok &= ct == cw
                print(f'  {kind} parity {par} {g["key"][1]} ({ck}): own-stub GX substitutions '
                      f'{ {k: sorted(v) for k, v in subs.items() if v} }; clean {len(ct)} -> {len(cw)}')
    print('generated templates: every clean set = the true one' if allok else
          'generated templates: SOME CLEAN SET IS WEAKENED (F1)')
    return allok


if __name__ == '__main__' and '--generated' in sys.argv:
    generated()
