"""engine_driver -- glue between engine.html and the unmodified generator gen_on_instance.py.

run(instance_json) does exactly what gen_on_instance.main() does (Layout -> lua -> stats -> satisfying ->
intended_play), minus file I/O and the optional "assignment" key, and additionally reports the structure the
generator already computed (leg orders, nesting levels, K chain, tile kinds, gadget labels) so the page can
draw and annotate it. Nothing here changes what the generator builds.
"""
import json, time, traceback
import gen_on_instance as g

# Cells of the X and Cl patterns that belong to P (tile-local, positive-side orientation; from pat_X / pat_Cl).
P_X = {(5, 0), (5, 1), (6, 1), (7, 1), (7, 2), (7, 3), (6, 3), (5, 3), (5, 4), (5, 5), (5, 6), (5, 7), (6, 7),
       (7, 7), (7, 8), (7, 9), (6, 9), (5, 9), (5, 10)}
P_CL = {(5, 6), (5, 7), (5, 8), (5, 9), (5, 10), (6, 6), (7, 6), (8, 6), (8, 5), (9, 5), (10, 5)}


def _expand(pts):
    out = [pts[0]]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        dx, dy = (x1 > x0) - (x1 < x0), (y1 > y0) - (y1 < y0)
        x, y = x0, y0
        while (x, y) != (x1, y1):
            x, y = x + dx, y + dy
            out.append((x, y))
    return out


def structure(lay):
    """Per-cell role codes derived from the generator's own tile table (lay.tile, lay.occ, lay.arcs, lay.lab)."""
    T, RM = g.T, lay.RM
    hubs = set()
    for s, x in lay.chain:
        f = lay.geo(s, x)[1]
        hubs |= {(lay.col[('hL', x)], lay.r(s, f)), (lay.col[('hR', x)], lay.r(s, f))}
    arc = set()
    for pts in lay.arcs:
        arc.update(_expand(pts))
    arc -= hubs
    gate = {}
    for s in ('pos', 'neg'):
        for x, legs in lay.side[s]['legs_of'].items():
            v = lay.geo(s, x)[0]
            for k in range(len(legs)):
                u, row = lay.u[(x, k)], lay.r(s, v[k])
                gate[(u, row)] = gate[(u - 1, row)] = (s, x, k, legs[k][1])

    def var_of_col(c):
        return next((i for i in range(1, lay.n + 1) if lay.fork[i] <= c <= lay.join[i]), 0)

    rows = [[' '] * lay.W for _ in range(lay.H)]
    tiles = []
    for (tc, tr), (kind, f, ports) in sorted(lay.tile.items()):
        classes = {c for c, _, _ in lay.occ.get((tc, tr), [])}
        info = dict(c=tc, r=tr, kind=kind)
        code = None
        if kind == 'wire':
            cells, _ = g.pat_wire(ports)
            f = 'id'
            if classes == {'P'}:
                if tr == RM:
                    code = 'f' if (tc, tr) in lay.junc else 'm'
                else:
                    code = 'F' if tr < RM else 'T'
                i = var_of_col(tc)
                if i and code != 'm':
                    info['var'] = lay.var_names[i - 1]
            else:
                code = 'a' if (tc, tr) in arc else 'k'
        elif kind == 'sentinel':
            cells = {(5, 5): 'p', (2, 2): 'b'}
        else:
            cells, _ = {'X': g.pat_X, 'Cl': g.pat_Cl, 'door': g.pat_door}[kind]()
            if kind == 'X':
                i = var_of_col(tc)
                if i and tr != RM:
                    info['var'] = lay.var_names[i - 1]
        if (tc, tr) in gate:
            s, x, k, v = gate[(tc, tr)]
            info.update(side=s, clause=x, leg=k, var=lay.var_names[v - 1])
        tiles.append(info)
        for (x, y), ch in cells.items():
            X, Y = g.TF[f](x, y)
            X, Y = tc * T + X, tr * T + Y
            if kind == 'X':
                c2 = 'x' if (x, y) in P_X else 'y'
            elif kind == 'Cl':
                c2 = 'c' if (x, y) in P_CL else 'q'
            elif kind == 'door':
                c2 = 'd'
            elif kind == 'sentinel':
                c2 = 's'
            else:
                c2 = code
            rows[Y][X] = c2
    rows[lay.start[1]][lay.start[0]] = '@'
    rows[lay.goal[1]][lay.goal[0]] = 'G'
    labels = [[x, y, name, lay.tile[t][0]] for (t, name), (x, y) in lay.lab.items()]
    return [''.join(r) for r in rows], tiles, labels


def run(instance_json):
    inst = json.loads(instance_json)
    t0 = time.time()
    try:
        lay = g.Layout(inst)                       # parse, compress, leg order, columns, rows, P, K, resolve
    except ValueError as e:                        # 'not PMR: no planar leg order on side ...'
        return json.dumps(dict(ok=False, kind='ValueError', error=str(e)))
    except AssertionError as e:
        return json.dumps(dict(ok=False, kind='AssertionError', error=repr(e.args),
                               trace=traceback.format_exc()))
    t1 = time.time()
    text = g.lua(lay)
    st = lay.stats()
    alpha = g.satisfying(lay.n, lay.cl)
    moves = None
    if alpha:
        S = g.intended_play(lay, alpha)
        assert S.pos == lay.goal
        st.update(solution_moves=S.moves, min_hunger=S.minh, max_visits=max(S.visits.values()),
                  max_moves_without_cookie=S.maxdry)
        moves = ''.join(S.out)
    else:
        st.update(solution_moves=None)
    t2 = time.time()
    roles, tiles, labels = structure(lay)
    sides = {}
    for s, d in lay.side.items():
        sides[s] = dict(seq=[list(p) for p in d['seq']], level={str(k): v for k, v in d['level'].items()},
                        pre=d['pre'])
    return json.dumps(dict(
        ok=True, n=lay.n, var_names=lay.var_names, clauses=lay.cl, sides=sides,
        chain=[list(c) for c in lay.chain], alpha=alpha, stats=st, ascii=lay.ascii(), lua=text, moves=moves,
        roles=roles, tiles=tiles, labels=labels, T=g.T, RM=lay.RM,
        start=list(lay.start), goal=list(lay.goal),
        time_layout=round(t1 - t0, 3), time_play=round(t2 - t1, 3)))
