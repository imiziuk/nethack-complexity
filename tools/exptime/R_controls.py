#!/usr/bin/env python3
"""R_controls.py -- negative controls for the real-game step check: how many of the recorded real-game step results
(build/realgame/steps_*.tsv) would DISAGREE with deliberately wrong movement models. A large count shows the oracle
data discriminates each rule (the 0-mismatch result for A_core is not vacuous).

Variants: no_corner_rule (diagonal never blocked by corners), boulders_not_bad_rock (only stone blocks a diagonal),
diag_push (diagonal moves push boulders like orthogonal ones), squeeze (hero may step onto a boulder that cannot be
pushed), hole_is_bad_rock (holes block diagonals as stone does), hole_no_plug (a boulder pushed onto a hole stays).
Also counts outcome classes of the real results (push / plain step / refusal / fall / plug).
"""
import ast, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import R_model as M

OUT = os.path.join(HERE, '..', '..', 'build', 'realgame')
VARIANTS = ['no_corner_rule', 'boulders_not_bad_rock', 'diag_push', 'squeeze', 'hole_is_bad_rock', 'hole_no_plug']


def predict(w, h, B, Hm, key, v):
    dx, dy = M.KEYS[key]
    x, y = w.cells[h]
    t = w.idx.get((x + dx, y + dy))
    if t is None:
        return ('stay', h, B, Hm)
    tb = 1 << t
    diag = dx != 0 and dy != 0
    if B & tb and (not diag or v == 'diag_push'):
        b = w.idx.get((x + 2 * dx, y + 2 * dy))
        if b is None or B >> b & 1:
            if v == 'squeeze':
                return ('move', t, B, Hm)
            return ('stay', h, B, Hm)
        if Hm >> b & 1 and v != 'hole_no_plug':
            return ('move', t, B & ~tb, Hm & ~(1 << b))
        return ('move', t, (B & ~tb) | (1 << b), Hm)
    if B & tb:
        return ('stay', h, B, Hm)
    if diag and v != 'no_corner_rule':
        ok = False
        for c in ((x + dx, y), (x, y + dy)):
            i = w.idx.get(c)
            if i is None:
                continue
            if v == 'hole_is_bad_rock' and Hm >> i & 1:
                continue
            if v == 'boulders_not_bad_rock' or not (B >> i & 1):
                ok = True
        if not ok:
            return ('stay', h, B, Hm)
    if Hm & tb:
        return ('loss', t, B, Hm)
    return ('move', t, B, Hm)


REAL = re.compile(r'\((-?\d+), (-?\d+)\) b=(\[.*?\]) holes=(\[.*?\])')


def main():
    G = M.gadgets()
    res = {}
    classes = {}
    for f in sorted(os.listdir(OUT)):
        if not (f.startswith('steps_') and f.endswith('.tsv')):
            continue
        name = f[6:-4]
        w = G[name]
        cnt = {v: 0 for v in VARIANTS}
        cl = {}
        n = 0
        for line in open(os.path.join(OUT, f)):
            p = line.rstrip('\n').split('\t')
            if p[0] == 'qid':
                continue
            n += 1
            h = w.idx[ast.literal_eval(p[1])]
            B = w.mask([tuple(c) for c in ast.literal_eval(p[2])])
            Hm = w.mask([tuple(c) for c in ast.literal_eval(p[3])])
            k = p[4]
            if p[6].startswith('FELL'):
                real = ('loss',)
                c = 'fall'
            else:
                m = REAL.match(p[6])
                rh = (int(m.group(1)), int(m.group(2)))
                rb = [tuple(c) for c in ast.literal_eval(m.group(3))]
                rH = [tuple(c) for c in ast.literal_eval(m.group(4))]
                real = (rh, sorted(rb), sorted(rH))
                c = ('plug' if len(rH) < bin(Hm).count('1') else 'push' if rb != w.bset(B)
                     else 'refused' if rh == w.cells[h] else 'step' + ('_diag' if k in 'yubn' else ''))
                if c == 'refused':
                    dx, dy = M.KEYS[k]
                    x, y = w.cells[h]
                    t = (x + dx, y + dy)
                    c = ('refused_wall' if t not in w.idx else
                         'refused_boulder' if t in w.bset(B) else 'refused_diag_corner')
            cl[c] = cl.get(c, 0) + 1
            for v in VARIANTS:
                kind, h2, B2, H2 = predict(w, h, B, Hm, k, v)
                pv = ('loss',) if kind == 'loss' else (w.cells[h2], w.bset(B2), w.bset(H2))
                if pv != real:
                    cnt[v] += 1
        res[name] = dict(n=n, **cnt)
        classes[name] = cl
    print('| gadget | steps | ' + ' | '.join(VARIANTS) + ' |')
    print('|---|---|' + '---|' * len(VARIANTS))
    for name, r in res.items():
        print(f'| {name} | {r["n"]} | ' + ' | '.join(str(r[v]) for v in VARIANTS) + ' |')
    print()
    tot = {}
    for name, cl in classes.items():
        print(name, dict(sorted(cl.items())))
        for k, v in cl.items():
            tot[k] = tot.get(k, 0) + v
    print('TOTAL', dict(sorted(tot.items())))
    json.dump(dict(variants=res, classes=classes), open(os.path.join(OUT, 'controls.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
