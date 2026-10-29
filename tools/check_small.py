#!/usr/bin/env python3
"""check_small.py -- brute-force check of the L_ON* reduction on ALL small PMR-3SAT instances.

For every monotone 3-SAT instance with n <= 3 variables and 1 <= m <= 3 distinct clauses (each clause 1..3 distinct
literals, all of one sign) that has a planar monotone rectilinear drawing (all 513 do), it builds the level with
tools/gen_on_instance.py (canonical drawing) and checks "g reachable <=> formula satisfiable" in the exact
abstract model of hu-on-lower §2:
   state = (hero cell, boulder set, set of unplugged holes);
   hero steps to an 8-neighbour: target must be floor without boulder; entering a hole = loss (never taken);
   diagonal step refused iff both corner cells are bad rock (stone or boulder)               [Sokoban corner rule];
   orthogonal step into a boulder pushes it iff the cell beyond is floor without boulder (no squeezing: heavy hero);
   a boulder pushed onto a hole plugs it (boulder and hole vanish, the cell becomes floor);
   no diagonal pushes; nothing else moves boulders or the hero.
 * satisfiable instance  : the generator's intended move string is replayed step by step in this model; it must
                           end on g with the hunger counter >= 150 throughout (constructive proof of reachability).
                           A sample of the smallest ones is also solved by the BFS, which must find g.
 * unsatisfiable instance: exhaustive BFS, no pruning; g must be unreachable.

BFS = push-level search: the hero's cell is replaced by its free region (min node id), computed on a compressed
graph whose nodes are the static floor components plus every cell a boulder or hole can ever occupy. Exact: all
hero cells of one free region have the same successors. Diagonal steps keep their corner conditions.

Usage: python check_small.py [--workers 10] [--out results.json] [--cap 3000000]
       python check_small.py --only '[[[2],[-2],[1,3]]]' [--n 3] ...       (only these clause sets)
       python check_small.py --only ... --export DIR   (write the compressed model of each selected level as
                                                         DIR/<name>.txt for the exact Rust BFS in fastbfs/)
"""
import argparse, itertools, json, os, sys, time
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_on_instance as G

D4 = [(1, 0), (-1, 0), (0, 1), (0, -1)]
D8 = D4 + [(1, 1), (1, -1), (-1, 1), (-1, -1)]


class Model:
    def __init__(self, lay):
        W, H, grid = lay.W, lay.H, lay.grid
        floor = {(x, y) for y in range(H) for x in range(W) if grid[y][x] in '.^'}
        pit = lay.pit
        assert all((pit[0] + dx, pit[1] + dy) not in floor for dx, dy in D8), 'sentinel pit not isolated'
        br = lay.branch     # Rev. 3 branch-stair pocket: sealed, so it is not part of the hero's map
        assert br not in floor and all((br[0] + dx, br[1] + dy) not in floor for dx, dy in D8), 'pocket not sealed'
        # over-approximation of every cell a boulder can ever occupy
        dyn = set(lay.boulders)
        stack = list(dyn)
        while stack:
            b = stack.pop()
            for dx, dy in D4:
                h, t = (b[0] - dx, b[1] - dy), (b[0] + dx, b[1] + dy)
                if h in floor and t in floor and t not in dyn:
                    dyn.add(t)
                    stack.append(t)
        dyn |= set(lay.holes)
        static = floor - dyn
        # union-find on static cells over moves that are legal in every state
        par = {c: c for c in static}

        def find(c):
            while par[c] != c:
                par[c] = par[par[c]]
                c = par[c]
            return c

        def corners(a, d):
            return [(a[0] + d[0], a[1]), (a[0], a[1] + d[1])]
        for a in static:
            for d in D8:
                b = (a[0] + d[0], a[1] + d[1])
                if b not in static:
                    continue
                if d[0] and d[1] and not any(k in static for k in corners(a, d)):
                    continue
                ra, rb = find(a), find(b)
                if ra != rb:
                    par[ra] = rb
        comps = sorted({find(c) for c in static})
        cid = {r: i for i, r in enumerate(comps)}
        self.dynl = sorted(dyn)
        self.didx = {c: len(comps) + i for i, c in enumerate(self.dynl)}
        self.N = len(comps) + len(self.dynl)
        self.nstatic = len(comps)
        node = {c: cid[find(c)] for c in static}
        node.update(self.didx)
        self.node = node
        # edges; condition = None (always) or tuple of dynamic corner bits (any free corner suffices)
        adj = [dict() for _ in range(self.N)]
        for a in floor:
            for d in D8:
                b = (a[0] + d[0], a[1] + d[1])
                if b not in floor:
                    continue
                na, nb = node[a], node[b]
                if na == nb:
                    continue
                if d[0] and d[1]:
                    ks = [k for k in corners(a, d) if k in floor]
                    if not ks:
                        continue
                    if any(k in static for k in ks):
                        cond = None
                    else:
                        cond = sum(1 << (self.didx[k] - self.nstatic) for k in ks)
                else:
                    cond = None
                old = adj[na].get(nb, 0)
                if old is None:
                    continue
                if cond is None:
                    adj[na][nb] = None
                else:   # several alternative diagonals: keep a list of corner masks
                    adj[na][nb] = (old if isinstance(old, list) else []) + [cond]
        self.un_mask = [sum(1 << v for v, c in a.items() if c is None) for a in adj]
        self.static_all = (1 << self.nstatic) - 1

        self.dyn_all = (1 << len(self.dynl)) - 1
        self.co = [[(v, c) for v, c in a.items() if c is not None] for a in adj]
        self.corner_mask = 0
        for lst in self.co:
            for v, cond in lst:
                for c in cond:
                    self.corner_mask |= c
        self.extra_cache = {}
        # per dynamic cell and push direction: (hero node, target bit or 0 if target not floor)
        self.pushes = []
        for c in self.dynl:
            lst = []
            for dx, dy in D4:
                h, t = (c[0] - dx, c[1] - dy), (c[0] + dx, c[1] + dy)
                if h in node and t in floor:
                    lst.append((node[h], 1 << (node[t] - self.nstatic)))
            self.pushes.append(lst)
        self.hole_bit = {c: 1 << (self.didx[c] - self.nstatic) for c in lay.holes}
        self.b0 = sum(1 << (self.didx[c] - self.nstatic) for c in lay.boulders)
        self.h0 = sum(self.hole_bit.values())
        self.start = node[lay.start]
        self.goal = node[lay.goal]
        self.dcell = self.dynl
        self.floor = floor

    def region(self, s, bm, hm, base=0):
        """Free region of the hero standing on node s, as a node bitmask (bit-parallel flood fill).
        base = a set of nodes already known to be in the region (incremental flood)."""
        ns = self.nstatic
        passable = self.static_all | ((~(bm | hm) & self.dyn_all) << ns)
        frontier = 1 << s
        seen = base | frontier
        ck = bm & self.corner_mask
        adjc = self.extra_cache.get(ck)
        if adjc is None:    # full adjacency (incl. diagonals usable under this placement of corner boulders)
            adjc = list(self.un_mask)
            for u, lst in enumerate(self.co):
                for v, cond in lst:
                    if not all((bm & c) == c for c in cond):
                        adjc[u] |= 1 << v
            if len(self.extra_cache) > 3000:     # bound memory (~10 KB per entry)
                self.extra_cache.clear()
            self.extra_cache[ck] = adjc
        while frontier:
            acc = 0
            f = frontier
            while f:
                low = f & -f
                acc |= adjc[low.bit_length() - 1]
                f ^= low
            frontier = acc & passable & ~seen
            seen |= frontier
        return seen

    def solve(self, max_states=3_000_000, max_seconds=None):
        t_start = time.time()
        ns = self.nstatic
        b0, h0 = self.b0, self.h0
        D = len(self.dynl)
        sh1, sh2 = D, 2 * D
        # state = (boulders, unplugged holes, min node of the hero's free region): exact, since all hero cells
        # of one free region have the same successors.
        reg = self.region(self.start, b0, h0)
        seen = {b0 | (h0 << sh1) | (((reg & -reg).bit_length() - 1) << sh2)}
        frontier = [(b0, h0, reg)]
        pushes, region, goal = self.pushes, self.region, self.goal
        while frontier:
            if max_seconds and time.time() - t_start > max_seconds:
                raise RuntimeError('time cap')
            nxt = []
            for bm, hm, reg in frontier:
                if (reg >> goal) & 1:
                    return True, len(seen)
                m = bm
                while m:
                    low = m & -m
                    i = low.bit_length() - 1
                    m ^= low
                    for hn, tb in pushes[i]:
                        if not (reg >> hn) & 1 or bm & tb:
                            continue
                        if hm & tb:
                            nb, nh = bm ^ low, hm ^ tb
                        else:
                            nb, nh = (bm ^ low) | tb, hm
                        # incremental: if the target cell t was outside the region, it touched no region cell
                        # (a free floor cell next to the region is in it), so blocking it removes nothing.
                        tn = ns + tb.bit_length() - 1
                        r2 = region(ns + i, nb, nh, 0 if (reg >> tn) & 1 else reg)
                        k = nb | (nh << sh1) | (((r2 & -r2).bit_length() - 1) << sh2)
                        if k in seen:
                            continue
                        seen.add(k)
                        if len(seen) > max_states:
                            raise RuntimeError('state cap')
                        nxt.append((nb, nh, r2))
            frontier = nxt
        return False, len(seen)


NL = chr(10)


def export(model, path):
    """Dump the compressed graph exactly as Model.solve uses it (node ids; dynamic cell d has node ns + d)."""
    m, ns = model, model.nstatic
    bit2node = lambda mask: [ns + k for k in range(mask.bit_length()) if (mask >> k) & 1]
    with open(path, 'w') as fh:
        fh.write(('%d %d %d %d %d' + NL) % (m.N, ns, m.start, m.goal, len(m.hole_bit)))
        fh.write(('B %s' + NL) % ' '.join(map(str, bit2node(m.b0))))
        fh.write(('H %s' + NL) % ' '.join(map(str, bit2node(m.h0))))
        for u in range(m.N):
            fh.write(('U %d %s' + NL) % (u, ' '.join(str(v) for v in range(m.N) if (m.un_mask[u] >> v) & 1)))
        for u, lst in enumerate(m.co):
            for v, conds in lst:
                for c in conds:
                    fh.write(('C %d %d %s' + NL) % (u, v, ' '.join(map(str, bit2node(c)))))
        for i, lst in enumerate(m.pushes):
            for hn, tb in lst:
                fh.write(('P %d %d %d' + NL) % (ns + i, hn, ns + tb.bit_length() - 1))


def replay(lay, moves):
    S = G.Sim(lay)
    inv = {v: k for k, v in G.KEYS.items()}
    h = G.START_HUNGER
    minh = h
    for ch in moves:
        if ch == 'E':
            h += G.COOKIE - G.EAT_TURNS
            continue
        d = inv[ch]
        t = (S.pos[0] + d[0], S.pos[1] + d[1])
        h -= 1
        minh = min(minh, h)
        if t in S.b:
            assert not (d[0] and d[1]), 'diagonal push in move string'
            S.push(d)
            S.out.pop()
        else:
            assert S.can_step(S.pos, d), ('illegal step', S.pos, d)
            S.pos = t
    return S.pos == lay.goal, minh


def instances():
    out = []
    for n in (1, 2, 3):
        cls = []
        for size in (1, 2, 3):
            for vs in itertools.combinations(range(1, n + 1), size):
                cls.append(list(vs))
                cls.append([-v for v in vs])
        for m in (1, 2, 3):
            for combo in itertools.combinations(cls, m):
                inst = {'n': n, 'clauses': [list(c) for c in combo]}
                ok = True
                for s in ('pos', 'neg'):
                    if G.leg_order(n, inst['clauses'], s) is None:
                        ok = False
                out.append((inst, ok))
    return out


MAX_SECONDS = None


def _init(ms):
    global MAX_SECONDS
    MAX_SECONDS = ms


def run_one(job):
    inst, mode, cap = job
    t0 = time.time()
    lay = G.Layout(inst)
    alpha = G.satisfying(lay.n, lay.cl)
    rec = dict(inst=inst, mode=mode, sat=alpha is not None, **lay.stats())
    if mode == 'replay':
        S = G.intended_play(lay, alpha)
        ok, minh = replay(lay, ''.join(S.out))
        rec.update(reach=ok, replay_ok=ok, moves=S.moves, min_hunger=minh, max_visits=max(S.visits.values()),
                   maxdry=S.maxdry)
    else:
        model = Model(lay)
        try:
            reach, nstates = model.solve(max_states=cap, max_seconds=MAX_SECONDS)
            rec.update(reach=reach, states=nstates, dyn=len(model.dynl), nodes=model.N)
        except RuntimeError:
            rec.update(reach=None, states='cap')
    rec['secs'] = round(time.time() - t0, 2)
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--workers', type=int, default=10)
    ap.add_argument('--out', default=None)
    ap.add_argument('--cap', type=int, default=3_000_000)
    ap.add_argument('--max-seconds', type=int, default=1800, help='per-search time limit')
    ap.add_argument('--log', default=None, help='append one JSON line per finished job')
    ap.add_argument('--sat-bfs', type=int, default=20, help='number of smallest SAT instances also solved by BFS')
    ap.add_argument('--only', default=None, help='JSON list of clause lists; check only these levels')
    ap.add_argument('--export', default=None, help='with --only: write compressed models to this dir and exit')
    a = ap.parse_args()
    allin = instances()
    if a.only:
        want = {tuple(tuple(c) for c in cl) for cl in json.loads(a.only)}
        allin = [(i, ok) for i, ok in allin if tuple(tuple(c) for c in i['clauses']) in want]
        allin = list({json.dumps(i['clauses']): (i, ok) for i, ok in allin}.values())  # one n per clause set
        print('--only: %d instance(s) selected' % len(allin), flush=True)
        if a.export:
            os.makedirs(a.export, exist_ok=True)
            for i, ok in allin:
                name = json.dumps(i['clauses']).replace(' ', '')
                fn = os.path.join(a.export, ''.join(ch if ch.isalnum() or ch in '-,' else '_' for ch in name) + '.txt')
                export(Model(G.Layout(i)), fn)
                print('exported', name, '->', fn, 'sat' if G.satisfying(i['n'], i['clauses']) else 'unsat',
                      flush=True)
            return
    valid = [i for i, ok in allin if ok]
    # the generator deletes unused variables, so instances with the same compressed formula give the same level
    def key(i):
        n, cl, _, _ = G.compress(i['n'], i['clauses'])
        return (n, tuple(sorted(tuple(c) for c in cl)))
    distinct = {}
    for i in valid:
        distinct.setdefault(key(i), i)
    print('%d distinct levels after deleting unused variables' % len(distinct), flush=True)
    valid_all = valid
    valid = list(distinct.values())
    sat = [i for i in valid if G.satisfying(i['n'], i['clauses'])]
    uns = [i for i in valid if not G.satisfying(i['n'], i['clauses'])]
    print('enumerated %d monotone instances, %d with a planar drawing -> %d distinct levels: %d satisfiable, '
          '%d unsatisfiable' % (len(allin), len(valid_all), len(valid), len(sat), len(uns)), flush=True)
    small_sat = sorted(sat, key=lambda i: (sum(len(c) for c in i['clauses']), i['n']))[:a.sat_bfs]
    # heaviest jobs first so the pool stays busy
    jobs = ([(i, 'bfs', a.cap) for i in sorted(uns, key=lambda i: -sum(len(c) for c in i['clauses']))]
            + [(i, 'bfs', 50_000) for i in small_sat] + [(i, 'replay', 0) for i in sat])
    t0 = time.time()
    res = []
    with Pool(a.workers, initializer=_init, initargs=(a.max_seconds,)) as pool:
        for k, r in enumerate(pool.imap_unordered(run_one, jobs, chunksize=1)):
            res.append(r)
            if a.log:
                with open(a.log, 'a') as fh:
                    fh.write(json.dumps(r) + chr(10))
            if (k + 1) % 100 == 0:
                print('%d/%d jobs, %.0f s' % (k + 1, len(jobs), time.time() - t0), flush=True)
    by = lambda mode, s: [r for r in res if r['mode'] == mode and r['sat'] == s]
    bad = []
    for r in by('replay', True):
        if not (r['replay_ok'] and r['min_hunger'] >= 150):
            bad.append(r)
    for r in by('bfs', False):
        if r['reach'] is True:
            bad.append(r)
    for r in by('bfs', True):
        if r['reach'] is False:
            bad.append(r)
    unsat_done = [r for r in by('bfs', False) if r['reach'] is False]
    summ = dict(
        instances=len(valid_all), distinct_levels=len(valid), satisfiable_levels=len(sat),
        unsatisfiable_levels=len(uns),
        sat_replay_reaches_g=sum(r['replay_ok'] for r in by('replay', True)),
        sat_bfs_finds_g='%d/%d' % (sum(r['reach'] is True for r in by('bfs', True)), len(small_sat)),
        unsat_bfs_exhausted_unreachable='%d/%d' % (len(unsat_done), len(uns)),
        unsat_bfs_capped=[r['inst']['clauses'] for r in by('bfs', False) if r['reach'] is None],
        mismatches=len(bad),
        max_states_unsat=max([r['states'] for r in unsat_done], default=0),
        max_map_w_h=max(((r['width'], r['height']) for r in res), default=None),
        max_crossovers=max(r['crossovers'] for r in res),
        max_moves=max((r.get('moves') or 0) for r in res),
        min_hunger=min((r.get('min_hunger') or 9999) for r in res),
        max_visits=max((r.get('max_visits') or 0) for r in res),
        max_cookieless_run=max((r.get('maxdry') or 0) for r in res),
        slowest_job_secs=max(r['secs'] for r in res), wall_secs=round(time.time() - t0, 1))
    for r in bad:
        print('MISMATCH', json.dumps(r), flush=True)
    print(json.dumps(summ, indent=1))
    if a.out:
        json.dump(dict(summary=summ, results=res), open(a.out, 'w'), indent=0)


if __name__ == '__main__':
    main()
