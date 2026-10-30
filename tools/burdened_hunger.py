"""Hunger budget of the NP construction when the hero starts Burdened (hu-on-lower §1.3, §5.1).

vary_init_attr [attrib.c:763-776] can leave Str+Con = 16, so wc = 450 < 500 (the loadstone) and the hero is
Burdened (SLT_ENCUMBER). Burdened changes only speed: u_calc_moveamt gives 12 - 12/4 = 9 movement per turn
[allmain.c:139-141]; hunger stays 1 per turn (the extra point needs > SLT_ENCUMBER [eat.c:3197]).
So an action takes 1 or 2 turns. Exercise can raise Str/Con later (unencumbered again, speed 12); nothing lowers
them (no abuse: never Hungry, no Burdened abuse [attrib.c:521-566]).

For every satisfiable level of check_small (n, m <= 3) this replays the intended walk (moves only; the eating is
re-decided with the same policy: eat a fresh cookie iff hunger <= EAT_AT) under three speed models:
  exact9  : 9 movement per turn, start u.umovement = 12, an action costs 12, hunger -1 per new turn
  worst2  : every action costs 2 turns (upper bound for speed 9 and 12)
  exact12 : the original model (1 turn per action)
A meal (delay 1) is counted as 2 actions in every model. Reports min hunger per model.
"""
import json, sys
import gen_on_instance as G
import check_small as C


def run(lay, moves, model):
    S = G.Sim(lay)
    inv = {v: k for k, v in G.KEYS.items()}
    cookies = {(x, y) for y, row in enumerate(lay.grid) for x, ch in enumerate(row) if ch == '.'}
    cookies.discard(S.pos)
    h, minh, mv, turns = G.START_HUNGER, G.START_HUNGER, 12, 0

    def act():
        nonlocal h, mv, turns
        if model == 'exact12':
            h -= 1; turns += 1
        elif model == 'worst2':
            h -= 2; turns += 2
        else:
            while mv < 12:
                mv += 9; h -= 1; turns += 1
            mv -= 12

    for ch in moves:
        if ch == 'E':
            continue
        d = inv[ch]
        t = (S.pos[0] + d[0], S.pos[1] + d[1])
        act()
        minh = min(minh, h)
        if t in S.b:
            S.push(d)
            S.out.pop()
        else:
            assert S.can_step(S.pos, d)
            S.pos = t
        if S.pos in cookies and h <= G.EAT_AT:
            cookies.discard(S.pos)
            act(); act()
            minh = min(minh, h)
            h += G.COOKIE
    return S.pos == lay.goal, minh, h, turns


def main():
    valid = [i for i, ok in C.instances() if ok]
    distinct = {}
    for i in valid:
        n, cl, _, _ = G.compress(i['n'], i['clauses'])
        distinct.setdefault((n, tuple(sorted(tuple(c) for c in cl))), i)
    sat = [i for i in distinct.values() if G.satisfying(i['n'], i['clauses'])]
    agg = {m: dict(levels=0, reach=0, min_hunger=10**9, max_turns=0)
           for m in ('exact12', 'exact9', 'worst2')}
    for i in sat:
        lay = G.Layout(i)
        S = G.intended_play(lay, G.satisfying(lay.n, lay.cl))
        moves = ''.join(S.out)
        for m, a in agg.items():
            ok, minh, h, turns = run(lay, moves, m)
            a['levels'] += 1; a['reach'] += ok
            a['min_hunger'] = min(a['min_hunger'], minh)
            a['max_turns'] = max(a['max_turns'], turns)
    print(json.dumps(agg, indent=1))


if __name__ == '__main__':
    main()
