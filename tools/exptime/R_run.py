#!/usr/bin/env python3
"""R_run.py -- differential brute force: A_core model vs the REAL compiled NetHack 5.0.0 (headless tty, wizard mode).

Phases (results in build/realgame/, summary in proofs/exptime/R-realgame.md):
  steps     every reachable (hero cell, boulders, holes) state of each small gadget window x all 8 keys; SCD: a
            stratified sample (2 states per reachable boulder configuration) + all states on the intended walks.
            Each query = fresh level in the real game, ONE key, engine state read back; compared with the model.
  walks     every traversal (port p -> port q, shortest model walk) from every local state (SCD: intended walks
            only), replayed key by key in the real game; final state and the hero cell after every key compared.
  screen    intended automaton walks TYPED into the tty (pyte screen: hero glyph after every key + message lines;
            ground truth dumped by a script) + a random single-step sample per gadget with the message line.
Usage (WSL): ~/nh-witness/venv/bin/python R_run.py [steps|walks|screen|all] [gadget ...]
"""
import json, os, random, sys, time
import multiprocessing as mp

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import R_model as M
import R_oracle as O

ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
OUT = os.path.join(ROOT, 'build', 'realgame')
os.makedirs(OUT, exist_ok=True)
SEED = 20261029
SCD_PER_CONFIG = 2

_G = None
_W = None


def log(*a):
    print(time.strftime('%H:%M:%S'), *a, flush=True)


# ---------------------------------------------------------------- gadget setup (model side)
def windows():
    G = M.gadgets()
    pj = G['precursor']
    s2_rows = list(pj.rows)
    s2_rows[5] = '#..0.0...#'          # precursor/1-toggle state 2: blocks at track x=3,5
    toggle = M.Window('toggle', [r.replace('T', '.') for r in pj.rows])      # T closed: ports D,E,F,G only
    scd_c = M.Window('SCD', M.scd_rows('c'))
    inits = {n: [(w.b0, w.h0)] for n, w in G.items()}
    inits['precursor'] = [(pj.b0, 0), (M.Window('x', s2_rows).b0, 0)]
    inits['SCD'] = [(G['SCD'].b0, 0), (scd_c.b0, 0)]
    G['toggle'] = toggle
    inits['toggle'] = inits['precursor']
    return G, inits


def scd_local_states(w):
    """A_core.explore on the flat SCD board with ports O, I, J (cached)."""
    cache = os.path.join(OUT, 'scd_local_states.json')
    if os.path.exists(cache):
        return [(b, 0) for b in json.load(open(cache))]
    import A_core as K
    S = set()
    for rows in (M.scd_rows('o'), M.scd_rows('c')):
        S |= set(K.explore(K.Board(rows)).states)
    json.dump(sorted(S), open(cache, 'w'))
    return [(b, 0) for b in sorted(S)]


def scd_state(w, B):
    bs = set(w.bset(B))
    prec = 'open' if {(5, 5), (7, 5)} <= bs else 'closed' if {(4, 5), (6, 5)} <= bs else 'mid' \
        if {(4, 5), (7, 5)} <= bs else 'other'
    tog = 'r' if {(17, 5), (19, 5)} <= bs else 'l' if {(16, 5), (18, 5)} <= bs else 'other'
    return prec, tog


def scd_clean(w, B):
    """flat SCD clean (A2-scd.md 5b): every component in its clean set (precursor/toggle track blocks in
    {(3,5),(3,6),(4,6)}, diode block on m1/m2) and the toggle in state r (4,6)."""
    bs = w.bset(B)
    prec = tuple(sorted(x - 1 for x, y in bs if y == 5 and x <= 10))
    tog = tuple(sorted(x - 13 for x, y in bs if y == 5 and x >= 13))
    d1 = [x - 1 for x, y in bs if y == 10 and x <= 5]
    d2 = [x - 6 for x, y in bs if y == 10 and x >= 7]
    return (prec in {(3, 5), (3, 6), (4, 6)} and tog == (4, 6) and len(d1) == 1 and d1[0] in (2, 3)
            and len(d2) == 1 and d2[0] in (2, 3))


def scd_relation(w, B, clean_only=True):
    rel = {}
    for p in sorted(w.port_idx):
        for (q, B2, H2), k in w.traversal_walks(B, 0, p).items():
            if clean_only and not scd_clean(w, B2):
                continue
            rel.setdefault(f'{p}->{q}', set()).add(scd_state(w, B2)[0])
    return {k: sorted(v) for k, v in sorted(rel.items())}


# ---------------------------------------------------------------- worker side (real game)
def init_worker(q):
    global _G
    import R_game
    _G = R_game.Game(q.get())
    _G.start()


def job_fast(args):
    name, queries, batch = args
    w = WINDOWS[name]
    t = time.time()
    res = O.run_fast(_G, w, queries, batch=batch, log=lambda s: log(name, s), timeout=1200)
    return name, res, time.time() - t, len(queries)


def job_screen(args):
    name, items = args
    w = WINDOWS[name]
    _G.start()        # fresh session without the MSGTYPE=hide of fast mode
    out = []
    for it in items:
        qid, h, bs, hs, keys = it
        try:
            r = O.run_screen(_G, w, h, bs, hs, keys)
        except Exception as e:
            r = {'error': repr(e)[:300]}
            _G.start()
        if r.get('truth', {}).get('kind') == 'fell':
            _G.start()
        out.append((qid, r))
    return name, out


WINDOWS, INITS = windows()


def pool(n):
    q = mp.Manager().Queue()
    for t in range(n):
        q.put(str(t))
    return mp.Pool(n, initializer=init_worker, initargs=(q,))


# ---------------------------------------------------------------- comparison
def expect_of(w, h, B, Hm, keys):
    """model prediction for a key string: (kind, final cell, boulders, holes, hero trace)"""
    tr = []
    kind = 'stay'
    for k in keys:
        kind, h, B, Hm = w.predict(h, B, Hm, k)
        if kind == 'loss':
            break
        tr.append(w.cells[h])
    return kind, h, B, Hm, tr


def compare(w, q, r):
    """q = (qid, hcell, bcells, hcells, keys) -> (ok, real_str, pred_str)"""
    qid, hc, bs, hs, keys = q
    kind, h2, B2, H2, tr = expect_of(w, w.idx[hc], w.mask(bs), w.mask(hs), keys)
    pred = 'LOSS(fell)' if kind == 'loss' else f'{w.cells[h2]} b={w.bset(B2)} holes={w.bset(H2)}'
    if r is None:
        return None, 'MISSING', pred
    if r['kind'] == 'nobuild':
        return None, 'NOBUILD', pred
    if r['kind'] == 'fell':
        return kind == 'loss', f'FELL dl={r["dl"]}', pred
    holes = sorted(c for c, t in r['traps'].items() if t == 'h')
    other = sorted(c for c, t in r['traps'].items() if t != 'h')
    real = f'{r["h"]} b={r["b"]} holes={holes}' + (f' other_traps={other}' if other else '')
    ok = kind != 'loss' and r['h'] == w.cells[h2] and r['b'] == w.bset(B2) and holes == w.bset(H2) and not other
    if ok and len(keys) > 1 and 'trace' in r:
        ok = r['trace'] == tr
        if not ok:
            real += f' trace={r["trace"]}'
    return ok, real, pred


def merge_dump(summary, fn):
    p = os.path.join(OUT, fn)
    old = json.load(open(p)) if os.path.exists(p) else {}
    for k, v in summary.items():
        if k.startswith('_') and k in old:
            old[k + '_prev'] = old[k]
        old[k] = v
    json.dump(old, open(p, 'w'), indent=1, default=str)


# ---------------------------------------------------------------- phase: steps
def step_queries(name, rng):
    w = WINDOWS[name]
    t = time.time()
    if name == 'SCD':
        loc = scd_local_states(w)
        R = w.reachable(loc)
        byB = {}
        for (h, B, Hm) in R:
            byB.setdefault(B, []).append(h)
        states = []
        for B in sorted(byB):
            hs = sorted(byB[B])
            for h in rng.sample(hs, min(SCD_PER_CONFIG, len(hs))):
                states.append((h, B, 0, rng.choice(M.KEYLIST)))
        info = dict(local_states=len(loc), reachable_hero_states=len(R), boulder_configs=len(byB))
        # every state on the intended walks, all 8 keys
        for (_, B, Hm, p, keys, *_r) in intended(name):
            for (h, B1, H1) in w.path_states(w.port_idx[p], B, Hm, keys):
                for k in M.KEYLIST:
                    states.append((h, B1, H1, k))
        qs = []
        seen = set()
        for (h, B, Hm, k) in states:
            if (h, B, Hm, k) in seen:
                continue
            seen.add((h, B, Hm, k))
            qs.append((len(qs), w.cells[h], w.bset(B), w.bset(Hm), k))
        info['model_time_s'] = round(time.time() - t, 1)
        return qs, info
    if name == 'toggle':
        return [], {}
    loc = sorted(w.local_states(INITS[name]))
    R = w.reachable(loc)
    qs = []
    for (h, B, Hm) in sorted(R):
        for k in M.KEYLIST:
            qs.append((len(qs), w.cells[h], w.bset(B), w.bset(Hm), k))
    # model self-test: HoleModel == A_core on hole-free windows
    selftest = 0
    if not w.has_holes:
        for (h, B, Hm) in R:
            for k in M.KEYLIST:
                if w.predict_hole(h, B, 0, k) != w.predict_acore(h, B, k):
                    selftest += 1
    return qs, dict(local_states=len(loc), reachable_hero_states=len(R), holemodel_vs_acore_diffs=selftest,
                    model_time_s=round(time.time() - t, 1))


def phase_steps(names, nproc):
    rng = random.Random(SEED)
    jobs, infos, allq = [], {}, {}
    for n in names:
        qs, info = step_queries(n, rng)
        if not qs:
            continue
        infos[n] = info
        allq[n] = qs
        log(f'steps {n}: {len(qs)} queries, {info}')
        size = 1500
        for i in range(0, len(qs), size):
            jobs.append((n, qs[i:i + size], 300))
    res = {n: {} for n in allq}
    times = {n: 0.0 for n in allq}
    t0 = time.time()
    with pool(nproc) as P:
        for n, r, dt, cnt in P.imap_unordered(job_fast, jobs):
            res[n].update(r)
            times[n] += dt
            log(f'  {n}: +{cnt} in {dt:.1f}s ({cnt / dt:.0f} q/s in this worker)')
    wall = time.time() - t0
    summary = {}
    for n, qs in allq.items():
        w = WINDOWS[n]
        mism, nob, miss = [], 0, 0
        with open(os.path.join(OUT, f'steps_{n}.tsv'), 'w') as f:
            f.write('qid\thero\tboulders\tholes\tkey\tok\treal\tpredicted\n')
            for q in qs:
                ok, real, pred = compare(w, q, res[n].get(q[0]))
                if ok is None:
                    nob += real == 'NOBUILD'
                    miss += real == 'MISSING'
                elif not ok:
                    mism.append((q, real, pred))
                f.write(f'{q[0]}\t{q[1]}\t{q[2]}\t{q[3]}\t{q[4]}\t{ok}\t{real}\t{pred}\n')
        summary[n] = dict(infos[n], queries=len(qs), mismatches=len(mism), nobuild=nob, missing=miss,
                          worker_seconds=round(times[n], 1),
                          mismatch_examples=[dict(hero=q[1], boulders=q[2], holes=q[3], key=q[4], real=r_, pred=p_)
                                             for q, r_, p_ in mism[:20]])
        log(f'steps {n}: {len(qs)} queries, {len(mism)} mismatches, nobuild {nob}, missing {miss}')
    total = sum(len(q) for q in allq.values())
    summary['_speed'] = dict(total_queries=total, wall_s=round(wall, 1), workers=nproc,
                             q_per_s_total=round(total / wall, 1))
    merge_dump(summary, 'steps_summary.json')
    log('steps total', summary['_speed'])


# ---------------------------------------------------------------- intended walks
def walk_for(w, B, Hm, p, q, pred=None):
    """shortest model walk p -> q from (B, H) (first such traversal; pred filters (B2, H2))."""
    tw = w.traversal_walks(B, Hm, p)
    best = None
    for (qq, B2, H2), keys in tw.items():
        if qq == q and (pred is None or pred(B2, H2)):
            if best is None or len(keys) < len(best[0]):
                best = (keys, B2, H2)
    return best


def intended(name):
    """[(label, B, H, port p, keys, expected q, B2, H2)] -- the automaton walks of each gadget (model-derived)."""
    w = WINDOWS[name]
    out = []

    def add(label, B, Hm, p, q, pred=None):
        r = walk_for(w, B, Hm, p, q, pred)
        if r is None:
            out.append((label + ' [NO MODEL WALK]', B, Hm, p, '', q, B, Hm))
            return None
        keys, B2, H2 = r
        out.append((label, B, Hm, p, keys, q, B2, H2))
        return B2, H2

    if name == 'SCD':
        # intended = postselected semantics (A2-scd.md 5b): only traversals that END clean count
        Bc = INITS['SCD'][1][0]
        Bo = INITS['SCD'][0][0]
        op = lambda B2, H2: scd_clean(w, B2) and scd_state(w, B2)[0] == 'open'
        cl = lambda B2, H2: scd_clean(w, B2)
        s = add('closed init: O->O opens (button)', Bc, 0, 'O', 'O', op)
        if s:
            s2 = add('opened: I->J traverses (and closes)', s[0], 0, 'I', 'J', cl)
            if s2:
                out.append(('after I->J: ' + str(scd_state(w, s2[0])), s2[0], 0, 'I', '', 'I', s2[0], 0))
                add('after I->J: O->O re-opens', s2[0], 0, 'O', 'O', op)
        add('open init: I->J traverses (and closes)', Bo, 0, 'I', 'J', cl)
        return out
    # generic: for every initial state and port pair p->q, the shortest traversal (= the automaton relation of the
    # initial state); every other traversal of every local state is replayed by the 'walks' phase
    for (B, Hm) in INITS[name]:
        for p in sorted(w.port_idx):
            best = {}
            for (q, B2, H2), keys in w.traversal_walks(B, Hm, p).items():
                if q == p and B2 == B and H2 == Hm:
                    continue
                if q not in best or len(keys) < len(best[q][0]):
                    best[q] = (keys, B2, H2)
            for q in sorted(best):
                keys, B2, H2 = best[q]
                out.append((f'init {w.bset(B)}: {p}->{q}', B, Hm, p, keys, q, B2, H2))
    return out


def all_traversals(name):
    w = WINDOWS[name]
    out = []
    loc = sorted(w.local_states(INITS[name]))
    for (B, Hm) in loc:
        for p in sorted(w.port_idx):
            for (q, B2, H2), keys in w.traversal_walks(B, Hm, p).items():
                out.append((f'{p}->{q}', B, Hm, p, keys, q, B2, H2))
    return out, len(loc)


def phase_walks(names, nproc):
    jobs, allw = [], {}
    for n in names:
        if n == 'SCD':
            # intended walks + a random sample: 150 local states x 1 random port x <= 5 random traversals
            ws = [x for x in intended(n) if x[4]]
            rng = random.Random(SEED + 2)
            w = WINDOWS[n]
            for (B, Hm) in rng.sample(scd_local_states(w), 150):
                p = rng.choice(sorted(w.port_idx))
                tw = sorted(w.traversal_walks(B, Hm, p).items())
                for (q, B2, H2), keys in rng.sample(tw, min(5, len(tw))):
                    ws.append((f'sample {p}->{q}', B, Hm, p, keys, q, B2, H2))
            nloc = None
        else:
            ws, nloc = all_traversals(n)
        w = WINDOWS[n]
        qs = [(i, w.cells[w.port_idx[p]], w.bset(B), w.bset(Hm), keys) for i, (lab, B, Hm, p, keys, q, B2, H2)
              in enumerate(ws) if keys]
        allw[n] = (ws, qs, nloc)
        log(f'walks {n}: {len(qs)} walks')
        for i in range(0, len(qs), 400):
            jobs.append((n, qs[i:i + 400], 100))
    res = {n: {} for n in allw}
    t0 = time.time()
    with pool(nproc) as P:
        for n, r, dt, cnt in P.imap_unordered(job_fast, jobs):
            res[n].update(r)
    summary = {}
    for n, (ws, qs, nloc) in allw.items():
        w = WINDOWS[n]
        fails = []
        with open(os.path.join(OUT, f'walks_{n}.tsv'), 'w') as f:
            f.write('qid\tlabel\tport\tboulders\tkeys\tok\treal\tpredicted\n')
            for q in qs:
                lab = ws[q[0]][0]
                ok, real, pred = compare(w, q, res[n].get(q[0]))
                expq = ws[q[0]][5]
                if ok and res[n][q[0]]['h'] != w.cells[w.port_idx[expq]]:
                    ok = False
                if not ok:
                    fails.append((lab, q, real, pred))
                f.write(f'{q[0]}\t{lab}\t{q[1]}\t{q[2]}\t{q[4]}\t{ok}\t{real}\t{pred}\n')
        summary[n] = dict(local_states=nloc, walks=len(qs), fails=len(fails),
                          keys_total=sum(len(q[4]) for q in qs),
                          fail_examples=[dict(label=l, start=q[1], boulders=q[2], keys=q[4], real=r_, pred=p_)
                                         for l, q, r_, p_ in fails[:10]])
        log(f'walks {n}: {len(qs)} walks, {len(fails)} FAIL')
    summary['_wall_s'] = round(time.time() - t0, 1)
    merge_dump(summary, 'walks_summary.json')


# ---------------------------------------------------------------- phase: screen
def phase_screen(names, nproc, per_gadget=25):
    rng = random.Random(SEED + 1)
    jobs, meta = [], {}
    for n in names:
        w = WINDOWS[n]
        items, labels = [], {}
        for (lab, B, Hm, p, keys, q, B2, H2) in intended(n):
            if not keys:
                continue
            qid = len(items)
            items.append((qid, w.cells[w.port_idx[p]], w.bset(B), w.bset(Hm), keys))
            labels[qid] = ('walk', lab, q)
        if n != 'toggle':
            loc = scd_local_states(w) if n == 'SCD' else sorted(w.local_states(INITS[n]))
            if n == 'SCD':
                loc = rng.sample(loc, 200)
            R = sorted(w.reachable(loc))
            # prefer interesting steps (pushes, refusals, losses) but keep some plain ones
            cand = []
            for (h, B, Hm) in rng.sample(R, min(len(R), 400)):
                k = rng.choice(M.KEYLIST)
                kind, h2, B2, H2 = w.predict(h, B, Hm, k)
                cand.append(((B2 != B) or kind != 'move', h, B, Hm, k))
            cand.sort(key=lambda c: not c[0])
            if w.has_holes:      # make sure hole entries (loss) are typed for real
                for (h, B, Hm) in R:
                    for k in M.KEYLIST:
                        if w.predict(h, B, Hm, k)[0] == 'loss':
                            cand.insert(0, (True, h, B, Hm, k))
            for (_, h, B, Hm, k) in cand[:per_gadget]:
                qid = len(items)
                items.append((qid, w.cells[h], w.bset(B), w.bset(Hm), k))
                labels[qid] = ('step', k, None)
        meta[n] = (items, labels)
        for i in range(0, len(items), 15):
            jobs.append((n, items[i:i + 15]))
        log(f'screen {n}: {len(items)} items')
    res = {n: {} for n in meta}
    t0 = time.time()
    with pool(nproc) as P:
        for n, out in P.imap_unordered(job_screen, jobs):
            for qid, r in out:
                res[n][qid] = r
    summary = {}
    for n, (items, labels) in meta.items():
        w = WINDOWS[n]
        rows, npass, nfail, nkeys, msgs = [], 0, 0, 0, {}
        for it in items:
            qid, hc, bs, hs, keys = it
            r = res[n].get(qid, {'error': 'missing'})
            kind, h2, B2, H2, tr = expect_of(w, w.idx[hc], w.mask(bs), w.mask(hs), keys)
            if 'error' in r:
                ok, why = False, r['error']
            else:
                t = r['truth']
                nkeys += len(keys)
                if kind == 'loss':
                    ok = t.get('kind') == 'fell'
                else:
                    ok = (t.get('kind') == 'ok' and t['h'] == w.cells[h2] and t['b'] == w.bset(B2)
                          and sorted(c for c, x in t['traps'].items() if x == 'h') == w.bset(H2))
                    # screen hero after every key == model trace
                    ok = ok and r['heroes'] == tr and r['hero0'] == hc
                if labels[qid][0] == 'walk' and ok and kind != 'loss':
                    ok = t['h'] == w.cells[w.port_idx[labels[qid][2]]]
                why = ''
                for m in r['msgs']:
                    for s in m:
                        msgs[s] = msgs.get(s, 0) + 1
            npass += bool(ok)
            nfail += not ok
            rows.append(dict(kind=labels[qid][0], label=labels[qid][1], start=hc, boulders=bs, holes=hs, keys=keys,
                             ok=ok, model=('LOSS' if kind == 'loss' else [w.cells[h2], w.bset(B2), w.bset(H2)]),
                             screen_heroes=r.get('heroes'), msgs=r.get('msgs'), err=why,
                             truth={k: (sorted(v.items()) if k == 'traps' else v) for k, v in (r.get('truth') or {}).items()}))
        json.dump(rows, open(os.path.join(OUT, f'screen_{n}.json'), 'w'), indent=0, default=str)
        summary[n] = dict(items=len(items), walks=sum(1 for v in labels.values() if v[0] == 'walk'),
                          keys_typed=nkeys, pass_=npass, fail=nfail, messages=msgs)
        log(f'screen {n}: {npass} pass, {nfail} fail')
    summary['_wall_s'] = round(time.time() - t0, 1)
    merge_dump(summary, 'screen_summary.json')


if __name__ == '__main__':
    phase = sys.argv[1] if len(sys.argv) > 1 else 'all'
    names = sys.argv[2:] or ['diode', 'G_D', 'SLOT1', 'UTURN2', 'proto_precursor', 'precursor', 'toggle', 'G_C', 'G_X',
                             'G_D_tile', 'SCD']
    nproc = int(os.environ.get('RPROC', '6'))
    if phase in ('steps', 'all'):
        phase_steps(names, nproc)
    if phase in ('walks', 'all'):
        phase_walks(names, nproc)
    if phase in ('screen', 'all'):
        phase_screen(names, nproc)
