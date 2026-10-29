#!/usr/bin/env python3
"""A_anneal.py -- simulated-annealing search for reusable boulder gadgets (EXPTIME workstream A).

State = a W x H interior (cells '#', '.', '0') inside a wall frame with fixed port cells on the frame.
Score (higher is better):
   +100 if complete (intended <= concrete from the initial state)
   - 60 * fraction of reachable concrete states that are not simulated by ANY intended state
   - 30 if not sound from the initial state (even if every state is individually simulated)
   - 0.2 * #floor cells - 0.5 * #boulders          (prefer small)
   leak (a boulder can reach a port) = -1000.
A pass = sound and complete. Usage:
   python A_anneal.py diode --w 6 --h 5 --ports "A:N1,B:S4" --iters 20000 --runs 24 --workers 12
Port spec "A:N1" = on the north frame above interior column 1 (1-based); sides N,S,W,E.
"""
import argparse, math, os, random, sys
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import A_core as K
import A_check as AC


def build(inner, ports, w, h):
    g = [['#'] * (w + 2) for _ in range(h + 2)]
    for y in range(h):
        for x in range(w):
            g[y + 1][x + 1] = inner[y][x]
    for name, side, k in ports:
        if side == 'N':
            g[0][k] = name
        elif side == 'S':
            g[h + 1][k] = name
        elif side == 'W':
            g[k][0] = name
        else:
            g[k][w + 1] = name
    return [''.join(r) for r in g]


def score(rows, target):
    try:
        b = K.Board(rows)
        C = K.explore(b, max_states=4000)
    except K.LeakError:
        return -1000.0, False
    except RuntimeError:
        return -500.0, False
    A = AC.TARGETS[target]()
    s, c, Rs, Rc = K.check(C, A)
    simd = {cc for (cc, a) in Rs}
    frac = 1 - len(simd) / len(C.states)
    nfloor = len(b.cells)
    nb = bin(b.b0).count('1')
    sc = (100 if c else 0) - 60 * frac - (0 if s else 30) - 0.2 * nfloor - 0.5 * nb
    return sc, s and c


def parse_ports(spec):
    out = []
    for item in spec.split(','):
        name, pos = item.split(':')
        out.append((name, pos[0], int(pos[1:])))
    return out


def run_grid(args):
    """anneal on a full board (frame + ports fixed); mutable = interior cells that are not ports."""
    target, rows, iters, seed = args
    rng = random.Random(seed)
    g = [list(r) for r in rows]
    H, W = len(g), len(g[0])
    mut = [(x, y) for y in range(1, H - 1) for x in range(1, W - 1) if g[y][x] in '.#0']
    cur, ok = score([''.join(r) for r in g], target)
    best = (cur, [r[:] for r in g], ok)
    found = []
    for it in range(iters):
        T = 6.0 * (1 - it / iters) + 0.05
        cand = [r[:] for r in g]
        for _ in range(rng.choice([1, 1, 1, 2, 2, 3])):
            x, y = rng.choice(mut)
            cand[y][x] = rng.choice('.#0')
        rr = [''.join(r) for r in cand]
        sc, ok2 = score(rr, target)
        if sc >= cur or rng.random() < math.exp((sc - cur) / T):
            g, cur = cand, sc
            if ok2:
                found.append((sc, tuple(rr)))
            if sc > best[0]:
                best = (sc, [r[:] for r in g], ok2)
    return best[0], tuple(''.join(r) for r in best[1]), best[2], found


def run(args):
    target, w, h, ports, iters, seed, init = args
    rng = random.Random(seed)
    if init:
        inner = [list(r) for r in init]
    else:
        inner = [[rng.choice('..#0' if rng.random() < 0.3 else '..#') for _ in range(w)] for _ in range(h)]
    # interior cell next to each port is floor
    def fix(inn):
        for name, side, k in ports:
            if side == 'N':
                inn[0][k - 1] = '.'
            elif side == 'S':
                inn[h - 1][k - 1] = '.'
            elif side == 'W':
                inn[k - 1][0] = '.'
            else:
                inn[k - 1][w - 1] = '.'
    fix(inner)
    cur, ok = score(build(inner, ports, w, h), target)
    best = (cur, [r[:] for r in inner], ok)
    found = []
    T0 = 8.0
    for it in range(iters):
        T = T0 * (1 - it / iters) + 0.05
        cand = [r[:] for r in inner]
        for _ in range(rng.choice([1, 1, 1, 2, 3])):
            y, x = rng.randrange(h), rng.randrange(w)
            cand[y][x] = rng.choice('.#0')
        fix(cand)
        sc, ok = score(build(cand, ports, w, h), target)
        if sc >= cur or rng.random() < math.exp((sc - cur) / T):
            inner, cur = cand, sc
            if ok:
                found.append((sc, tuple(build(inner, ports, w, h))))
            if sc > best[0]:
                best = (sc, [r[:] for r in inner], ok)
    return best[0], tuple(build(best[1], ports, w, h)), best[2], found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('target')
    ap.add_argument('--w', type=int, default=6)
    ap.add_argument('--h', type=int, default=5)
    ap.add_argument('--ports', default='')
    ap.add_argument('--iters', type=int, default=20000)
    ap.add_argument('--runs', type=int, default=12)
    ap.add_argument('--workers', type=int, default=12)
    ap.add_argument('--seed', type=int, default=1)
    ap.add_argument('--grid', help='comma-separated full board to anneal from (frame and ports kept)')
    a = ap.parse_args()
    if a.grid:
        rows = a.grid.split(',')
        jobs = [(a.target, rows, a.iters, a.seed * 10007 + k) for k in range(a.runs)]
        with Pool(a.workers) as pool:
            res = pool.map(run_grid, jobs)
    else:
        ports = parse_ports(a.ports)
        jobs = [(a.target, a.w, a.h, ports, a.iters, a.seed * 10007 + k, None) for k in range(a.runs)]
        with Pool(a.workers) as pool:
            res = pool.map(run, jobs)
    allfound = {}
    for sc, rows, ok, found in res:
        for s2, r2 in found:
            allfound[r2] = max(s2, allfound.get(r2, -1e9))
    res.sort(key=lambda t: -t[0])
    print(f'passing boards found: {len(allfound)}')
    for r2, s2 in sorted(allfound.items(), key=lambda kv: -kv[1])[:6]:
        print(f'PASS score {s2:.1f}')
        print('\n'.join(r2))
        print()
    print('best non-pass runs:')
    for sc, rows, ok, _ in res[:3]:
        print(f'score {sc:.1f} pass={ok}')
        print('\n'.join(rows))
        print()


if __name__ == '__main__':
    main()
