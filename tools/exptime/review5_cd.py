#!/usr/bin/env python3
"""review5_cd.py -- review 5 item 3(c): protodiode check through ONE joined C-D port (X map's `d.CD`) vs split C, D."""
import A_core as K, A2_scd as S
bd = K.Board(S.PROTODIODE); Cd = K.explore(bd)
split = {c for c in Cd.states if K.check_legal(Cd, c, S.PD_CHECKS)}
def legal_joined(c):
    N = S.net({'d': (S.with_init(Cd, c), {'A': 'A', 'B': 'B', 'C': 'cd', 'D': 'cd'})}, ['A', 'B', 'cd'])
    fr = {(c,)}
    for p, q in [('A', 'cd'), ('cd', 'B')]:
        fr = {s2 for s1 in fr for (q2, s2) in N.traversals(s1, p) if q2 == q}
        if not fr: return False
    return True
joined = {c for c in Cd.states if legal_joined(c)}
print('states', len(Cd.states), 'split-clean', len(split), 'joined-clean', len(joined), 'extra', len(joined - split))
for c in joined - split: print(bd.show(c)); print()

# ---- repair 1 (2026-10-29): check map read off the tile geometry (Wb slots of component legs walled), v1 vs v2
import X_build as XB
def tile_clean(rmap, comp):
    pm = {P: rmap[(comp, P)] for (c_, P) in rmap if c_ == comp}
    out = set()
    for c in Cd.states:
        N = S.net({'d': (S.with_init(Cd, c), pm)}, sorted(set(pm.values())))
        fr = {(c,)}
        for a, b in S.PD_CHECKS:
            fr = {s2 for s1 in fr for (q2, s2) in N.traversals(s1, pm[a]) if q2 == pm[b]}
            if not fr: break
        if fr: out.add(c)
    return out
res = {}
for ver, mk in (('v1', XB.diode_tile_v1), ('v2', XB.diode_tile), ('v1-scd', XB.scd_tile_v1), ('v2-scd', XB.scd_tile)):
    tl = mk()
    if ver.startswith('v1'):
        owner, cport = XB.comp_owner(tl.cells, XB.local_comps(tl)); cut = []
    else:
        owner, cport = tl.owner, tl.cport
        cut = [tuple(Lg['Wb']) for l, Lg in tl.legs.items() if not l.startswith('tile.')]
    rmap = XB.check_regions(tl.cells, owner, cport, cut)
    for comp in sorted({k[0] for k in cport if k[0] in ('d', 'd1', 'd2')}):
        cl = tile_clean(rmap, comp)
        joinedCD = rmap[(comp, 'C')] == rmap[(comp, 'D')]
        print(f'{ver:7s} {comp}: C, D share a check region: {joinedCD}; clean {len(cl)} of {len(Cd.states)} '
              f'(= split clean set: {cl == split}); broken absorbing: '
              f'{all(c2 not in cl for c in Cd.states if c not in cl for p in Cd.ports for _, c2 in Cd.T[(c, p)])}')
        res[(ver, comp)] = cl == split
print('v2 tiles: every diode check = split [A->C, D->B]:', all(v for (ver, _), v in res.items() if ver.startswith('v2')),
      '| v1 tiles:', all(v for (ver, _), v in res.items() if ver.startswith('v1')))
