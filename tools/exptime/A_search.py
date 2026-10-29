#!/usr/bin/env python3
"""A_search.py -- random search for small reusable boulder gadgets that pass A_core.check against a target automaton.

Usage: python A_search.py diode --w 5 --h 4 --boulders 1-3 --iters 200000 --seed 1 [--workers 8]
Prints every distinct passing board (smallest floor count first at the end).
Targets are the abstract automata defined in A_check.py (TARGETS).
"""
import argparse, os, random, sys
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import A_core as K
import A_check as AC


def border_cells(w, h):
    out = []
    for x in range(1, w + 1):
        out.append((x, 0, 'N'))
        out.append((x, h + 1, 'S'))
    for y in range(1, h + 1):
        out.append((0, y, 'W'))
        out.append((w + 1, y, 'E'))
    return out


def random_board(rng, w, h, nports, bmin, bmax, pfloor):
    g = [['#'] * (w + 2) for _ in range(h + 2)]
    for y in range(1, h + 1):
        for x in range(1, w + 1):
            g[y][x] = '.' if rng.random() < pfloor else '#'
    floor = [(x, y) for y in range(1, h + 1) for x in range(1, w + 1) if g[y][x] == '.']
    nb = rng.randint(bmin, bmax)
    if len(floor) < nb + 2:
        return None
    for (x, y) in rng.sample(floor, nb):
        g[y][x] = '0'
    bc = border_cells(w, h)
    ps = rng.sample(bc, nports)
    names = 'ABCDEFGH'
    for k, (x, y, side) in enumerate(ps):
        # port must touch an interior floor cell
        ix, iy = {'N': (x, 1), 'S': (x, h), 'W': (1, y), 'E': (w, y)}[side]
        if g[iy][ix] == '#':
            g[iy][ix] = '.'
        g[y][x] = names[k]
    return [''.join(r) for r in g]


def evaluate(rows, target):
    try:
        b = K.Board(rows)
        C = K.explore(b, max_states=3000)
    except (K.LeakError, RuntimeError):
        return False
    A = AC.TARGETS[target]()
    s, c, _, _ = K.check(C, A)
    return s and c


def work(args):
    target, w, h, bmin, bmax, iters, seed, nports = args
    rng = random.Random(seed)
    found = []
    for _ in range(iters):
        rows = random_board(rng, w, h, nports, bmin, bmax, rng.choice([0.5, 0.6, 0.7, 0.8]))
        if rows is None:
            continue
        if evaluate(rows, target):
            found.append(tuple(rows))
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('target')
    ap.add_argument('--w', type=int, default=5)
    ap.add_argument('--h', type=int, default=4)
    ap.add_argument('--boulders', default='1-3')
    ap.add_argument('--iters', type=int, default=20000)
    ap.add_argument('--seed', type=int, default=1)
    ap.add_argument('--workers', type=int, default=8)
    a = ap.parse_args()
    bmin, bmax = map(int, a.boulders.split('-'))
    nports = AC.NPORTS[a.target]
    jobs = [(a.target, a.w, a.h, bmin, bmax, a.iters // a.workers, a.seed * 1000 + k, nports)
            for k in range(a.workers)]
    with Pool(a.workers) as pool:
        res = pool.map(work, jobs)
    allf = sorted({r for lst in res for r in lst}, key=lambda r: sum(row.count('.') for row in r))
    print(f'{len(allf)} passing boards')
    for r in allf[:15]:
        print('\n'.join(r))
        print()


if __name__ == '__main__':
    main()
