#!/usr/bin/env python3
"""D_tests.py -- tests for the hero-vs-nature checker (D_game.py / D_game.rs). See proofs/exptime/D-checker.md.
  (a) one-player agreement with tools/check_small.py (no traps): small L_ON* reduction levels, exact BFS vs attractor
  (f) fuzz: random small levels WITH traps, D_game.py vs an independent naive solver (exact hero cell, no region
      collapsing, plain fixed-point iteration) vs D_game.rs
  (b) hand-made coin levels with known answers (levels/coin_*.txt)
  (c) relation mode: Python and Rust traversal relations identical on levels/coin_states.txt
Usage: python D_tests.py [--fuzz 300] [--seed 1] [--skip-a]"""
import argparse, os, random, re, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import D_game as D

D8 = D.D8


# ------------------------------------------------------------------ independent naive solver (exact hero cell)
def naive(L, start=None, goal=None):
    floor, traps = L.floor, L.traps
    s0, g = L.cell_of(start, L.start), L.cell_of(goal, L.goal)
    init = ('P', frozenset(L.states['init']), frozenset(L.holes), s0)
    nodes, succ, todo = {init}, {}, [init]
    vio = 0
    while todo:
        k = todo.pop()
        kind, B, Hs, x = k
        out = set()
        if kind == 'P':
            for d in D8:
                t = (x[0] + d[0], x[1] + d[1])
                if t not in floor:
                    continue
                if t in B:
                    if d[0] and d[1]:
                        continue
                    u = (t[0] + d[0], t[1] + d[1])
                    if u not in floor or u in B:
                        continue
                    if u in traps:
                        vio += 1
                        continue
                    nB = B - {t}
                    nH = Hs
                    if u in Hs:
                        nH = Hs - {u}
                    else:
                        nB = nB | {u}
                    out.add(('P', nB, nH, t))
                    continue
                if t in Hs:
                    continue
                if d[0] and d[1]:
                    bad = lambda c: c not in floor or c in B
                    if bad((x[0] + d[0], x[1])) and bad((x[0], x[1] + d[1])):
                        continue
                out.add(('N', B, Hs, t) if t in traps else ('P', B, Hs, t))
        else:
            for l in L.landing[x]:
                if l not in B and l not in Hs:
                    out.add(('P', B, Hs, l))
            vio += not out
        succ[k] = out
        for n in out:
            if n not in nodes:
                nodes.add(n)
                todo.append(n)
    win = {k for k in nodes if k[0] == 'P' and k[3] == g}
    changed = True
    while changed:
        changed = False
        for k in nodes:
            if k in win:
                continue
            s = succ[k]
            if (k[0] == 'P' and any(n in win for n in s)) or (k[0] == 'N' and s and all(n in win for n in s)):
                win.add(k)
                changed = True
    return init in win, vio > 0


def rust_solve(path):
    exe = D.build_rust()
    tmp = os.path.join(os.path.dirname(exe), 'test.dmodel')
    D.export(D.Model(D.Level(open(path).read())), tmp)
    out = subprocess.run([exe, tmp], capture_output=True, text=True).stdout
    m = re.search(r'result=(\w+)', out)
    return m.group(1), out


# ------------------------------------------------------------------ random levels
def rand_level(rng, W=7, H=5):
    cells = [(x, y) for y in range(1, H + 1) for x in range(1, W + 1)]
    fl = [c for c in cells if rng.random() < 0.68]
    if len(fl) < 6:
        return None
    rng.shuffle(fl)
    s, g = fl[0], fl[1]
    rest = fl[2:]
    ntr = rng.choice([0, 1, 1, 2, 2])
    traps = rest[:ntr]
    rest = rest[ntr:]
    nb = rng.randint(1, 5)
    bould = rest[:nb]
    holes = rest[nb:nb + rng.choice([0, 0, 1, 2])]
    grid = [['#'] * (W + 2) for _ in range(H + 2)]
    for (x, y) in fl:
        grid[y][x] = '.'
    for c, ch in [(c, '0') for c in bould] + [(c, '^') for c in holes] + [(c, 'T') for c in traps] + \
            [(s, '@'), (g, 'G')]:
        grid[c[1]][c[0]] = ch
    lines = [''.join(r) for r in grid]
    cand = [c for c in fl if c not in traps]
    for t in traps:
        land = rng.sample(cand, rng.randint(1, 3))
        lines.append(':trap %d %d land %s' % (t[0], t[1], ' '.join('%d %d' % c for c in land)))
    return '\n'.join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--fuzz', type=int, default=300)
    ap.add_argument('--rust-every', type=int, default=3, help='also run Rust on every k-th fuzz level')
    ap.add_argument('--seed', type=int, default=1)
    ap.add_argument('--skip-a', action='store_true')
    ap.add_argument('--a-count', type=int, default=8)
    a = ap.parse_args()
    fails = 0

    # (b) coin levels
    expect = {'coin_lose.txt': ('LOSE', True), 'coin_win.txt': ('WIN', True), 'coin_block.txt': ('WIN', True),
              'coin_violation.txt': ('LOSE', False), 'coin_tile.txt': ('LOSE', True)}
    for fn, (want, coop) in expect.items():
        p = os.path.join(HERE, 'levels', fn)
        L = D.Level(open(p).read())
        res, _, _ = D.solve(L)
        rr, _ = rust_solve(p)
        nv, _ = naive(L)
        ok = res['result'] == want == rr and (nv == (want == 'WIN')) and res['coop_reach'] == coop
        fails += not ok
        print('(b) %-20s py=%s rust=%s naive=%s coop=%s %s' % (fn, res['result'], rr, nv, res['coop_reach'],
                                                              'ok' if ok else 'FAIL'))

    # (c) relation Python vs Rust
    p = os.path.join(HERE, 'levels', 'coin_states.txt')
    L = D.Level(open(p).read())
    _, rel = D.relation(L)
    py = {(r['state'], r['frm'], r['to'], r['exit_state']): r['win'] for r in rel}
    tmp = os.path.join(HERE, 'target', 'rel.dmodel')
    D.export(D.Model(L), tmp)
    out = subprocess.run([D.build_rust(), tmp, '--relation'], capture_output=True, text=True).stdout
    rs = {}
    for ln in out.splitlines():
        m = re.match(r'(\S+)\s+(\S+) -> (\S+) exit=(\S+)\s+(WIN|lose)', ln)
        if m:
            rs[m.group(1, 2, 3, 4)] = m.group(5) == 'WIN'
    ok = py == rs and len(py) > 0 and py[('init', '@', 'G', '*')] and not py[('open', '@', 'G', '*')]
    fails += not ok
    print('(c) relation coin_states: %d entries, python == rust: %s %s' % (len(py), py == rs, 'ok' if ok else 'FAIL'))

    # (f) fuzz with traps: python vs naive (vs rust)
    rng = random.Random(a.seed)
    n = nwin = nvio = nblock = 0
    t0 = time.time()
    tmpl = os.path.join(HERE, 'target', 'fuzz.txt')
    while n < a.fuzz:
        txt = rand_level(rng)
        if txt is None:
            continue
        L = D.Level(txt)
        n += 1
        res, _, _ = D.solve(L)
        nv, v = naive(L)
        py = res['result'] == 'WIN'
        nwin += py
        nblock += (not py) and res['coop_reach']
        nvio += v
        bad = py != nv or (v != (res['violations'] > 0))
        if a.rust_every and n % a.rust_every == 0:
            open(tmpl, 'w').write(txt)
            rr, _ = rust_solve(tmpl)
            bad |= (rr == 'WIN') != py
        if bad:
            fails += 1
            print('(f) MISMATCH py=%s naive=%s vio=%s/%s\n%s' % (py, nv, res['violations'], v, txt))
    print('(f) fuzz: %d random levels (%d WIN, %d LOSE only because of nature, %d with reachable violations), '
          '%.1f s, mismatches so far %d' % (n, nwin, nblock, nvio, time.time() - t0, fails))

    # (a) one-player agreement with check_small
    if not a.skip_a:
        import check_small as CS
        import gen_on_instance as G
        insts = [i for i, ok in CS.instances() if ok]
        insts.sort(key=lambda i: (sum(len(c) for c in i['clauses']), i['n']))
        done, seen = 0, set()
        for inst in insts:
            if done >= a.a_count:
                break
            key = str(G.compress(inst['n'], inst['clauses'])[:2])
            if key in seen:
                continue
            seen.add(key)
            lay = G.Layout(inst)
            try:
                reach, nst = CS.Model(lay).solve(max_states=200_000, max_seconds=60)
            except RuntimeError:
                continue
            L = D.level_from_layout(lay)
            t1 = time.time()
            res, _, _ = D.solve(L, max_states=2_000_000)
            path = os.path.join(HERE, 'target', 'a_level.txt')
            open(path, 'w').write('\n'.join(L.rows) + '\n')
            rr, out = rust_solve(path)
            ok = (res['result'] == 'WIN') == reach == (rr == 'WIN')
            fails += not ok
            done += 1
            print('(a) %-28s sat=%-5s check_small reach=%-5s states=%-7d | D py=%s (%d pos, %.1fs) rust=%s %s' % (
                inst['clauses'], G.satisfying(inst['n'], inst['clauses']) is not None, reach, nst, res['result'],
                res['player_nodes'] + res['nature_nodes'], time.time() - t1, rr, 'ok' if ok else 'FAIL'))
    print('ALL OK' if fails == 0 else '%d FAILURES' % fails)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
