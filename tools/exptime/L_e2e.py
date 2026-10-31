#!/usr/bin/env python3
"""L_e2e.py -- review 6 repair test: abstract end-to-end check of every ROUTED G' WITH the crossings inside it.

B2_e2e and L_gen's S3 wire Ani's Thm 5.3 machinery around a component but leave out the crossings of the planar
drawing inside G' (review 6, F1). This script rebuilds each G' exactly as L_gen routed it (the `gseq` item list of
a block template: delimiters, every crossing of the G''s chain piece in trace order, the SO/SD contacts) as a
gadget network of IDEAL machinery (B2_ani I_WCX / I_SX / I_SO / I_SD, verified against the concrete boards in
B2_ani / M_verify) around the RAW component window (A_core exploration of Ani's Fig. 35a protodiode / Fig. 36a
proto-precursor) or, at level 1, around the SCD composite of postselected components (A2_scd 5a):

  component location l --stub (one WCX per GX on it, in series)-- Wb (WCX) -- mid (one WCX per CHX on it) --
  Wt (WCX) -- outer node.   Outer nodes, and both hallway ends of every crossing of anything that is not this
  G''s own leg, are ONE node `world` (over-approximation: the whole rest of the level, all of it joined).
  Chain: world -- c_in -- items in trace order -- c_out. SX with both lines on this piece = ideal SX; SX with
  another piece = a leak-free pass. Contacts: OP i = SO_i's Op on the chain (its In at b_i, Out = node `out_i`),
  SD i = SD_i from the chain end to a_i, OUT i = the chain continues from out_i.

Claim tested (Ani Thm 5.3 for this drawing): for every component state q,
      c_out reachable from (world, q, all machinery fresh)   <=>   the check sequence is legal from q (q clean).
Modes:
  tiles      : route the dio and scdc tile templates (both parities) three times -- repaired generator (expect
               every G' exact), POSITIVE CONTROL old GX rule with Ani placement and old rule with the review-6 HK
               placement (hooks with their recorded crossings; expect extra 'clean' states, i.e. the review-6
               counterexamples), and NEGATIVE CONTROLS on the repaired routing (delimiters removed / Wb only)
               which must be caught as non-exact; plus the two-player game on the routed diode G' (coin, lose/win
               variants; 'lose' must stay LOSE with the repaired G', must become WIN with the old GX and with no
               check path).
  xtemplates : every G' of the 8 crossover templates build/lgen/xtemplate_r6_*.json (repaired generator).
Usage: python L_e2e.py [tiles] [xtemplates]
"""
import json, os, random, sys, time
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import A_core as K
import A2_scd as A2
import B2_ani as BA
import B2_e2e as E

ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
OUT = os.path.join(ROOT, 'build', 'lgen')

PP_L, PD_L, SCD_L = ['A', 'B', 'C', 'E', 'F'], ['A', 'B', 'C', 'D'], ['O', 'I', 'J']


# ---------------------------------------------------------------- components
_COMP = {}


def comps():
    """kind -> (System, legs, hidden, checks, clean set)"""
    if _COMP:
        return _COMP
    Cp = K.explore(K.Board(A2.PROTO_PRECURSOR))
    Cd = K.explore(K.Board(A2.PROTODIODE))
    cl = lambda C, ch: {c for c in C.states if K.check_legal(C, c, ch)}
    _COMP['pp'] = (Cp, PP_L, ['D', 'G'], A2.PP_CHECKS, cl(Cp, A2.PP_CHECKS))
    _COMP['pd'] = (Cd, PD_L, [], A2.PD_CHECKS, cl(Cd, A2.PD_CHECKS))
    # level 1: the SCD composite of postselected components, both initial states, merged into one system
    Cp_, Cd_, S1, S2 = E.raw()
    Pp = A2.postselect_L(Cp_, A2.PP_CHECKS, A2.PP_L)[3]
    Pd = A2.postselect_L(Cd_, A2.PD_CHECKS, PD_L)[3]
    T, states = {}, set()
    for init in (S1, S2):
        g = {'prec': (A2.with_init(Pp, init), {'A': 'T', 'B': 'T', 'C': 'T', 'E': 'X', 'F': 'Y'}),
             'tog': (A2.with_init(Pp, S1), {'A': 'tT', 'B': 'tT', 'C': 'tT', 'E': 'O', 'F': 'T'}),
             'd1': (Pd, {'A': 'I', 'B': 'X', 'C': 'd1cd', 'D': 'd1cd'}),
             'd2': (Pd, {'A': 'Y', 'B': 'J', 'C': 'd2cd', 'D': 'd2cd'})}
        N = A2.Net2(g, {'O': 'O', 'I': 'I', 'J': 'J'}).explore()
        T.update(N.T)
        states |= set(N.states)
    Cs = K.System(['I', 'J', 'O'], sorted(states)[0], T, sorted(states))
    _COMP['scd'] = (Cs, SCD_L, [], [('O', 'O'), ('I', 'J')], cl(Cs, [('O', 'O'), ('I', 'J')]))
    return _COMP


# ---------------------------------------------------------------- one G' as a gadget network
def build(kind, items, hooks=None, delim=('Wt', 'Wb'), world_outer=True, game=None, link_world=True):
    """returns (Builder, comp gadget name, cin, cout, world). hooks (HK placement only): {loc: crossing list};
    delim: which delimiter WCX exist (the others become plain hallways: negative controls).
    game: optional dict(outer={leg: node}, world=node) to embed the G' in a bigger game."""
    C, legs, hidden, checks, _ = comps()[kind]
    B = E.Builder()
    world = (game or {}).get('world', 'world')
    loc = {l: B.node('loc' + l) for l in legs + hidden}
    B.add('comp', C, {p: loc[p] for p in C.ports})
    outer = {l: ((game or {}).get('outer', {}).get(l, world) if world_outer else B.node('out' + l)) for l in legs}
    xg = {}                          # item index -> (bt, tp) of its crossing gadget
    mid, wbl = {}, {}
    # stubs: GXo items on leg l, in series between loc l and the Wb hallway end
    for l in legs:
        cur = loc[l]
        for n, it in enumerate(items):
            if it[0] == 'GXo' and it[1] == l:
                nx = B.node(f'stub{l}')
                xg[n] = B.wcx(cur, nx, f'gx{n}')
                cur = nx
        wbl[l] = cur
        mid[l] = B.node('mid' + l)
    dl = {}
    for l in legs:
        dl[('Wb', l)] = B.wcx(wbl[l], mid[l], f'Wb{l}') if 'Wb' in delim else None
        dl[('Wt', l)] = B.wcx(mid[l], outer[l], f'Wt{l}') if 'Wt' in delim else None
        if 'Wb' not in delim:
            B.chain(wbl[l], mid[l])
        if 'Wt' not in delim:
            B.chain(mid[l], outer[l])
    for n, it in enumerate(items):
        if it[0] == 'CHXm':
            xg[n] = B.wcx(mid[it[1]], mid[it[1]], f'cm{n}')
    sx = {}
    cin = B.node('cin')
    if link_world:
        B.chain(world, cin)
    cur = cin
    outs = {}
    k = 0
    while k < len(items):
        it = items[k]
        t = it[0]
        if t in ('W', 'GXf', 'GXp'):
            # a run of crossings of foreign floor joined only by chain hallway = one WCX(world, world) (L_gen.md §9)
            while k + 1 < len(items) and items[k + 1][0] in ('W', 'GXf', 'GXp'):
                k += 1
            bt, tp = B.wcx(world, world, f'w{k}')
            B.chain(cur, bt)
            cur = tp
        elif t in ('Wt', 'Wb'):
            g = dl[(t, it[1])]
            if g is not None:
                B.chain(cur, g[0])
                cur = g[1]
        elif t in ('GXo', 'CHXm'):
            bt, tp = xg[k]
            B.chain(cur, bt)
            cur = tp
        elif t == 'SXa':
            L_, R_ = B.node('sxL'), B.node('sxR')
            bt, tp = B.node('sxB'), B.node('sxT')
            B.add(f'sx{it[1]}', BA.I_SX(), {'L': L_, 'R': R_, 'Tp': tp, 'Bt': bt})
            sx[it[1]] = (tp, bt)
            B.chain(cur, L_)
            cur = R_
        elif t == 'SXb':
            tp, bt = sx[it[1]]
            B.chain(cur, tp)
            cur = bt
        elif t == 'OP':
            i = it[1]
            a, b = checks[i]
            op, out = B.node(f'op{i}'), B.node(f'out{i}')
            B.chain(cur, op)
            cur = op
            # the In wire b_i -> SO_i In, walked once; its SX crossings (stored box -> location) as later lines
            c = loc[b]
            for n in reversed(it[2] if len(it) > 2 else []):
                tp, bt = sx[n]
                B.chain(c, tp)
                c = bt
            B.add(f'SO{i}', BA.I_SO(), {'Op': op, 'In': c, 'Out': out})
            outs[i] = out
        elif t == 'SD':
            a, b = checks[it[1]]
            ids = it[2] if len(it) > 2 else []
            y = B.node(f'sdY{it[1]}') if ids else loc[a]
            c = y
            for n in ids:                         # the exit wire SD_i -> a_i, box -> location
                tp, bt = sx[n]
                B.chain(c, tp)
                c = bt
            if ids:
                B.chain(c, loc[a])
            B.add(f'SD{it[1]}', BA.I_SD(), {'X': cur, 'Y': y})
            cur = None
        elif t == 'OUT':
            cur = outs[it[1]]
        k += 1
    if hooks is not None:                       # HK placement (review-6 state): SO + SD on the chain, hooks drawn
        for i, (a, b) in enumerate(checks):
            op, out = B.node(f'op{i}'), B.node(f'out{i}')
            B.chain(cur, op)
            ain, bin_ = B.node(f'ah{i}'), B.node(f'bh{i}')
            B.add(f'SO{i}', BA.I_SO(), {'Op': op, 'In': bin_, 'Out': out})
            B.add(f'SD{i}', BA.I_SD(), {'X': op, 'Y': ain})
            # a-hook SD exit -> a (walked SD -> a: Bt on the SD side); b-hook b -> SO In (Bt on the b side)
            for hk_from, hk_to, lst in ((ain, loc[a], hooks[a]), (loc[b], bin_, hooks[b])):
                c = hk_from
                for n, x in enumerate(lst):
                    if x[0] == 'SX':
                        continue
                    if x[0] == 'GXo':            # WCX on own stub x[1] (hallway = loc .. Wb side of the stub)
                        bt, tp = B.wcx(loc[x[1]], wbl[x[1]], f'hgx{i}_{n}')
                    elif x[0] == 'CHXm':
                        bt, tp = B.wcx(mid[x[1]], mid[x[1]], f'hcm{i}_{n}')
                    else:
                        bt, tp = B.wcx(world, world, f'hw{i}_{n}')
                    B.chain(c, bt)
                    c = tp
                B.chain(c, hk_to)
            cur = out
    return B, 'comp', cin, cur, world


def winners(kind, items, **kw):
    """set of component states q from which c_out is reachable"""
    C, legs, hidden, checks, clean = comps()[kind]
    B, cname, cin, cout, world = build(kind, items, **kw)
    out = set()
    for q in C.states:
        inits = dict(B.inits)
        inits[cname] = q
        G = E.Game(B.gs, None, world, cout, inits)
        r, _, _ = G.solve(cap=3_000_000)
        if r['win']:
            out.add(q)
    return out


_CACHE = {}


def check_gprime(kind, items, **kw):
    """(exact?, |winners|, |clean|, extra states, missing states)"""
    key = (kind, repr(items), repr(sorted(kw.items())))
    if key not in _CACHE:
        clean = comps()[kind][4]
        w = winners(kind, items, **kw)
        _CACHE[key] = (w == clean, len(w), len(clean), len(w - clean), len(clean - w))
    return _CACHE[key]


def kind_of(g):
    return 'scd' if g['level'] == 1 else g['kind']


def summarize_items(gs):
    c = Counter()
    for g in gs:
        for it in g['items']:
            c[it[0]] += 1
    return dict(c)


# ---------------------------------------------------------------- the two-player game on the routed diode G'
def diode_game(items, variant, mode, hooks=None):
    """main game: start s on the diode's input side A; diode A -> B leads to bside; at bside the button O of an
    ideal SCD whose tunnel I -> J goes from the A side (I = s) to t; a hallway bside <-> coin; coin outcomes
    [s, beta] with beta = bside ('lose') or s ('win').
      ideal diode, goal t: 'lose' LOSE (after A -> B the hero cannot come back, nature never sends him to s),
                           'win' WIN (press O, coin, I -> J).
      raw protodiode, goal t ('nocheck'): 'lose' WIN -- A -> B into the bidirectional broken state #...0#,
                           press O, walk B -> A, I -> J.
      'checked': chain t -> this G' (as routed) -> CHX on the coin hallway -> g: must be LOSE / WIN."""
    import A_check as AC
    Cd = comps()['pd'][0]
    s, coin, bside, t, g = 's', 'coin', 'bside', 't', 'g'
    beta = bside if variant == 'lose' else s
    if mode in ('ideal', 'nocheck'):
        B = E.Builder()
        if mode == 'ideal':
            B.add('comp', AC.T_diode(), {'A': s, 'B': bside})
        else:
            B.add('comp', Cd, {'A': s, 'B': bside, 'C': 'cd', 'D': 'cd'})
        B.add('door', AC.T_scd_button(), {'O': bside, 'I': s, 'J': t})
        B.chain(bside, coin)
        return E.Game(B.gs, (coin, [s, beta]), s, t, B.inits).solve()[0]
    B, cname, cin, cout, world = build('pd', items, hooks=hooks, link_world=False,
                                       game=dict(world=bside, outer={'A': s, 'B': bside, 'C': 'cd', 'D': 'cd'}))
    B.add('door', AC.T_scd_button(), {'O': bside, 'I': s, 'J': t})
    B.chain(t, cin)
    bt, tp = B.wcx(bside, coin, 'chx')          # the coin hallway, crossed by the chain (Lemma 5.6 CHX)
    B.chain(cout, bt)
    B.chain(tp, g)
    return E.Game(B.gs, (coin, [s, beta]), s, g, B.inits).solve()[0]


# ---------------------------------------------------------------- drivers
def route_tiles(env):
    old = {k: os.environ.get(k) for k in env}
    os.environ.update(env)
    try:
        import importlib
        import L_gen as L
        L = importlib.reload(L)
        rng = random.Random(1)
        inst = L.random_instance(rng)
        N = L.netlist(inst); L.contract(N)
        Bs = L.Bus(N); Bs.order(); Bs.rows()
        Lv = L.Level(Bs); Lv.blocks()
        out = {}
        for kind in ('dio', 'scdc'):
            tn = [t for t in Bs.tiles if Bs.tiles[t]['kind'] == kind][0]
            for par in (0, 1):
                r = L.block_template(Lv.tb[tn], par)
                rec = L.template_record(r)
                assert all(v['err'] is None for v in rec['levels'].values()), (kind, par, rec['levels'])
                out[(kind, par)] = rec
        return out
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def run_recs(recs, label, expect_exact, **kw):
    n = bad = 0
    extra = Counter()
    for (kind, par), rec in recs.items():
        hooks = {tuple(h['key']): h['locs'] for h in rec.get('hooks', [])}
        for g in rec['gseq']:
            k = kind_of(g)
            kw2 = dict(kw)
            if rec.get('placement') == 'hk':
                kw2['hooks'] = hooks[tuple(g['key'])]
            ex, nw, nc, ne, nm = check_gprime(k, g['items'], **kw2)
            n += 1
            if not ex:
                bad += 1
                extra[(k, nc, nw)] += 1
                print(f'   {label}: {kind} parity {par} G\' {g["key"][1]} ({k}): winners {nw} vs clean {nc} '
                      f'(+{ne} extra, -{nm} missing)', flush=True)
    ok = (bad == 0) if expect_exact else (bad > 0)
    print(f'{label}: {n} G\', {n - bad} exact, {bad} not exact {dict(extra)} -> '
          f'{"as expected" if ok else "UNEXPECTED"}', flush=True)
    return ok


def main_tiles():
    t0 = time.time()
    ok = True
    print('== repaired generator (Ani placement, GX only on finished legs)', flush=True)
    rec_new = route_tiles({'LGEN_PLACEMENT': 'ani', 'LGEN_GX_RULE': 'finished'})
    for key, rec in rec_new.items():
        own_gx = sum(1 for g in rec['gseq'] for it in g['items'] if it[0] in ('GXo', 'GXp'))
        print(f'   {key}: items {summarize_items(rec["gseq"])}; own/pending GX {own_gx}; validate '
              f'{rec["validate"]["ok"]} {rec["validate"].get("rules")}', flush=True)
        ok &= own_gx == 0 and rec['validate']['ok']
    ok &= run_recs(rec_new, 'repaired', True)
    print('== negative controls on the repaired routing (the model must see detours)', flush=True)
    ok &= run_recs(rec_new, 'no delimiters', False, delim=())
    print('== positive control 1: old GX rule (own stubs crossable after the passes), Ani placement', flush=True)
    rec_own = route_tiles({'LGEN_PLACEMENT': 'ani', 'LGEN_GX_RULE': 'own'})
    for key, rec in rec_own.items():
        print(f'   {key}: items {summarize_items(rec["gseq"])}', flush=True)
    n_own = sum(1 for rec in rec_own.values() for g in rec['gseq'] for it in g['items'] if it[0] == 'GXo')
    if n_own:
        ok &= run_recs(rec_own, 'old rule + Ani placement', False)
    else:
        print('   (the router chose no own-stub GX under the old rule here: no information)')
    print('== positive control 2: review-6 state (old rule, HK placement, hooks with their crossings)', flush=True)
    rec_hk = route_tiles({'LGEN_PLACEMENT': 'hk', 'LGEN_GX_RULE': 'own'})
    for key, rec in rec_hk.items():
        n = sum(1 for h in rec.get('hooks', []) for v in h['locs'].values() for x in v if x[0] == 'GXo')
        print(f'   {key}: own-stub GX on hooks {n}', flush=True)
    ok &= run_recs(rec_hk, 'review-6 HK + old rule', False)
    print('== two-player game on the routed diode G\' (dio tile, parity 0)', flush=True)
    g_new = [g for g in rec_new[('dio', 0)]['gseq'] if g['kind'] == 'pd'][0]
    g_hk = [g for g in rec_hk[('dio', 0)]['gseq'] if g['kind'] == 'pd'][0]
    hk_hooks = {tuple(h['key']): h['locs'] for h in rec_hk[('dio', 0)]['hooks']}[tuple(g_hk['key'])]
    exp = {('lose', 'ideal'): False, ('win', 'ideal'): True, ('lose', 'nocheck'): True, ('win', 'nocheck'): True,
           ('lose', 'repaired'): False, ('win', 'repaired'): True, ('lose', 'review6'): True, ('win', 'review6'): True}
    for variant in ('lose', 'win'):
        for mode in ('ideal', 'nocheck', 'repaired', 'review6'):
            if mode in ('ideal', 'nocheck'):
                r = diode_game(None, variant, mode)
            elif mode == 'repaired':
                r = diode_game(g_new['items'], variant, 'checked')
            else:
                r = diode_game(g_hk['items'], variant, 'checked', hooks=hk_hooks)
            good = r['win'] == exp[(variant, mode)]
            ok &= good
            print(f'   {variant:4s} {mode:9s}: {"WIN " if r["win"] else "LOSE"} positions {r["positions"]:8d} '
                  f'{"as expected" if good else "UNEXPECTED"}', flush=True)
    print(f'tiles: {"ALL AS EXPECTED" if ok else "SOME UNEXPECTED RESULT"} ({time.time() - t0:.0f} s)', flush=True)
    return ok


def main_xtemplates():
    t0 = time.time()
    ok = True
    for fx in (0, 1):
        for fy in (0, 1):
            for par in (0, 1):
                f = os.path.join(OUT, f'xtemplate_r6_{fx}{fy}{par}.json')
                if not os.path.exists(f):
                    print(f'{f}: missing')
                    ok = False
                    continue
                rec = json.load(open(f))
                gs = rec.get('gseq', [])
                own_gx = sum(1 for g in gs for it in g['items'] if it[0] in ('GXo', 'GXp'))
                bad = 0
                for g in gs:
                    ex = check_gprime(kind_of(g), g['items'])[0]
                    bad += not ex
                good = bad == 0 and own_gx == 0 and rec['validate']['ok'] and len(gs) == 146
                ok &= good
                print(f'xtemplate {fx}{fy}{par}: {len(gs)} G\' ({Counter(kind_of(g) for g in gs)}), not exact {bad}, '
                      f'own/pending GX {own_gx}, validate {rec["validate"]["ok"]}, items {summarize_items(gs)} '
                      f'[{time.time() - t0:.0f} s, {len(_CACHE)} distinct G\']', flush=True)
    print(f'xtemplates: {"ALL AS EXPECTED" if ok else "SOME UNEXPECTED RESULT"}', flush=True)
    return ok


if __name__ == '__main__':
    modes = sys.argv[1:] or ['tiles']
    ok = True
    if 'tiles' in modes:
        ok &= main_tiles()
    if 'xtemplates' in modes:
        ok &= main_xtemplates()
    sys.exit(0 if ok else 1)
