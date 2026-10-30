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
