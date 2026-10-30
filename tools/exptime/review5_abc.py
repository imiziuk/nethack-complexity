#!/usr/bin/env python3
"""review5_abc.py -- adversarial review 5, item 3(a).

Question: X-crossover's SCD tile joins the proto-precursor's A, B, C legs into one hallway (check port `*.ABC`).
If the check machinery can only enter that joined hallway, Ani's precursor check [A->D, C->G, B->A, B->C] degrades to
[T->D, T->G, T->T, T->T] (a T->T check is trivially legal).  Does the weaker check still give:
  (1) the same clean set (3 states)?   (2) broken absorbing?   (3) flat SCD postselected = ideal SCD?
Read-only use of A_core / A2_scd.
"""
import A_core as K
import A2_scd as S

bp = K.Board(S.PROTO_PRECURSOR)
Cp = K.explore(bp)
split_clean = {c for c in Cp.states if K.check_legal(Cp, c, S.PP_CHECKS)}

# joined-leg system: A, B, C identified as one node T (walks may pass between them freely)
J = S.net({'p': (Cp, {'A': 'T', 'B': 'T', 'C': 'T', 'E': 'E', 'F': 'F', 'D': 'D', 'G': 'G'})},
          ['T', 'E', 'F', 'D', 'G'])
JN = J.explore()
# map network states (1-tuples) back to the raw board states
def raw(st):
    return st[0]
joined_checks = [('T', 'D'), ('T', 'G')]     # B->A, B->C become T->T: always legal (stand still)
reach_states_all = Cp.states                 # evaluate on every raw state, starting the joined system there
def legal_joined(c):
    Nc = S.net({'p': (S.with_init(Cp, c), {'A': 'T', 'B': 'T', 'C': 'T', 'E': 'E', 'F': 'F', 'D': 'D', 'G': 'G'})},
               ['T', 'E', 'F', 'D', 'G'])
    frontier = {(c,)}
    for p, q in joined_checks:
        frontier = {s2 for s1 in frontier for (q2, s2) in Nc.traversals(s1, p) if q2 == q}
        if not frontier:
            return False
    return True

joined_clean = {c for c in Cp.states if legal_joined(c)}
print('split clean  :', sorted(S.track(bp, c, 2) for c in split_clean))
print('joined clean :', sorted(S.track(bp, c, 2) for c in joined_clean))
extra = joined_clean - split_clean
print('broken-but-joined-clean states:', sorted(S.track(bp, c, 2) for c in extra))
for c in sorted(extra, key=lambda c: S.track(bp, c, 2)):
    print(bp.show(c))
    print()

# flat SCD with the weaker component clean set
bd = K.Board(S.PROTODIODE)
Cd = K.explore(bd)
dclean = {c for c in Cd.states if K.check_legal(Cd, c, S.PD_CHECKS)}
S1 = [s for s in split_clean if S.track(bp, s, 2) == (4, 6)][0]
S2 = [s for s in split_clean if S.track(bp, s, 2) == (3, 5)][0]
ok_all = True
for prec_init, ai in ((S1, 'o'), (S2, 'c')):
    g = {'prec': (S.with_init(Cp, prec_init), {'A': 'T', 'B': 'T', 'C': 'T', 'E': 'X', 'F': 'Y', 'D': 'pD', 'G': 'pG'}),
         'tog': (S.with_init(Cp, S1), {'A': 'tT', 'B': 'tT', 'C': 'tT', 'E': 'O', 'F': 'T', 'D': 'tD', 'G': 'tG'}),
         'd1': (Cd, {'A': 'I', 'B': 'X', 'C': 'd1cd', 'D': 'd1cd'}),
         'd2': (Cd, {'A': 'Y', 'B': 'J', 'C': 'd2cd', 'D': 'd2cd'})}
    NW = S.Net2(g, {'O': 'O', 'I': 'I', 'J': 'J'})
    N = NW.explore()
    scd_clean, _, _ = K.postselect(N, [('O', 'O'), ('I', 'J')])
    comp = {'prec': joined_clean, 'tog': joined_clean, 'd1': dclean, 'd2': dclean}
    cl = {st for st in N.states if all(x in comp[n] for n, x in zip(NW.names, st)) and st in scd_clean}
    absorbing = all(s2 not in cl for st in N.states if st not in cl for p in N.ports for _, s2 in N.T[(st, p)])
    T = {(st, p): {(q, s2) for q, s2 in N.T[(st, p)] if s2 in cl} for st in cl for p in N.ports}
    P = K.System(N.ports, N.init, T, sorted(cl))
    s, c, _, _ = K.check(P, S.T_scd(ai))
    print(f'init {ai}: {len(N.states)} raw states, {len(cl)} clean (joined checks); absorbing {absorbing}; '
          f'postselected vs ideal SCD SOUND {s} COMPLETE {c}')
    ok_all &= absorbing and s and c
print('JOINED-LEG CHECK SUFFICES' if ok_all and not extra else
      ('JOINED CLEAN SET DIFFERS BUT SCD STILL OK' if ok_all else 'JOINED-LEG CHECK INSUFFICIENT'))

# =====================================================================================================================
# Repair 1 (2026-10-29): the same attack, but with the check-location map READ OFF THE TILE GEOMETRY.
# For a tile, each component port is mapped to its hero-region in the tile with component interiors removed and every
# component-level delimiter slot Wb walled (= Ani Thm 5.3 check in progress: all WCX_b of that component closed).
# v1 tile (X crossover_v1, joined *.ABC): A, B, C share a region -> must reproduce the BROKEN verdict above.
# v2 tile (X_build.scd_tile, split legs): every port its own region -> clean set 3, broken absorbing, SOUND True.
import X_build as XB
print()
print('== tile-derived check maps (repair 1)')
verdicts = {}
for ver in ('v1', 'v2'):
    if ver == 'v1':
        tl = XB.scd_tile_v1()
        owner, cport = XB.comp_owner(tl.cells, XB.local_comps(tl))
        cut = []
    else:
        tl = XB.scd_tile()
        owner, cport = tl.owner, tl.cport
        cut = [tuple(Lg['Wb']) for l, Lg in tl.legs.items() if not l.startswith('tile.')]
    rmap = XB.check_regions(tl.cells, owner, cport, cut)

    def comp_clean(C, comp, checks):
        pm = {P: rmap[(comp, P)] for (c_, P) in rmap if c_ == comp}
        ext = sorted(set(pm.values()))
        out = set()
        for c in C.states:
            Nc = S.net({'p': (S.with_init(C, c), pm)}, ext)
            fr = {(c,)}
            for a, b in checks:
                fr = {s2 for s1 in fr for (q2, s2) in Nc.traversals(s1, pm[a]) if q2 == pm[b]}
                if not fr:
                    break
            if fr:
                out.add(c)
        return out
    shared = {comp: sorted(P for (c_, P), r in rmap.items() if c_ == comp and list(rmap.values()).count(r) > 1)
              for comp in ('tog', 'prec', 'd1', 'd2')}
    cl = {comp: comp_clean(Cp if comp in ('tog', 'prec') else Cd, comp,
                           S.PP_CHECKS if comp in ('tog', 'prec') else S.PD_CHECKS)
          for comp in ('tog', 'prec', 'd1', 'd2')}
    print(f'  {ver}: ports sharing a check region: {shared}')
    print(f'  {ver}: clean sets  prec {sorted(S.track(bp, c, 2) for c in cl["prec"])}  tog {len(cl["tog"])}  '
          f'd1 {len(cl["d1"])}/{len(Cd.states)}  d2 {len(cl["d2"])}/{len(Cd.states)}')
    okv = True
    for prec_init, ai in ((S1, 'o'), (S2, 'c')):
        g = {'prec': (S.with_init(Cp, prec_init), {'A': 'T', 'B': 'T', 'C': 'T', 'E': 'X', 'F': 'Y', 'D': 'pD', 'G': 'pG'}),
             'tog': (S.with_init(Cp, S1), {'A': 'tT', 'B': 'tT', 'C': 'tT', 'E': 'O', 'F': 'T', 'D': 'tD', 'G': 'tG'}),
             'd1': (Cd, {'A': 'I', 'B': 'X', 'C': 'd1cd', 'D': 'd1cd'}),
             'd2': (Cd, {'A': 'Y', 'B': 'J', 'C': 'd2cd', 'D': 'd2cd'})}
        NW = S.Net2(g, {'O': 'O', 'I': 'I', 'J': 'J'})
        N = NW.explore()
        scd_clean, _, _ = K.postselect(N, [('O', 'O'), ('I', 'J')])
        cset = {st for st in N.states if all(x in cl[n] for n, x in zip(NW.names, st)) and st in scd_clean}
        absorbing = all(s2 not in cset for st in N.states if st not in cset for p in N.ports for _, s2 in N.T[(st, p)])
        T = {(st, p): {(q, s2) for q, s2 in N.T[(st, p)] if s2 in cset} for st in cset for p in N.ports}
        s, c, _, _ = K.check(K.System(N.ports, N.init, T, sorted(cset)), S.T_scd(ai))
        print(f'  {ver} init {ai}: {len(N.states)} raw, {len(cset)} clean; broken absorbing {absorbing}; '
              f'postselected vs ideal SCD SOUND {s} COMPLETE {c}')
        okv &= absorbing and s and c
    okv &= len(cl['prec']) == 3
    verdicts[ver] = okv
print(f'v1 tile (joined *.ABC): {"PASSES" if verdicts["v1"] else "FAILS (as review 5 found)"};  '
      f'v2 tile (split legs): {"PASSES: clean set 3, broken absorbing, SOUND True" if verdicts["v2"] else "FAILS"}')
