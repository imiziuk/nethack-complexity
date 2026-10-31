#!/usr/bin/env python3
"""review6_hooks.py -- review 6: what do L_gen's check walks (after the two delimiter passes) cross?

Review-6 version: L_gen routed, per G', one undrawn 'hook' path from the chain head to every check location and
only counted its jumps. After the review-6 repairs (L_gen.Router._checks) the check walks are DRAWN on the chain
(Ani placement: Out_{i-1} -> Op_i at the SO_i box next to b_i, Op_i -> SD_i ending next to a_i; wires of length
0 or crossing nothing). This script re-runs the tile-block templates (SCD compound tile, diode tile; both lane
parities) and classifies every jump that the G''s chain piece makes AFTER its last Wb delimiter, from the router's
raw event list (not from Router.classify), by the role of the jumped floor point:
  SX           over the chain itself (single-use x single-use: safe in time order)
  GX.own       WCX on the g-side stub of an OWN leg (the F1 bug: must be 0)
  GX.pending   WCX on the stub of a leg whose G' is not finished (must be 0)
  GX.finished  WCX on the stub of a leg of a G' finished earlier in time (allowed: rule (iii))
  CHX.<role>   WCX over other floor (own dead middles 'mid.own', corridors, other legs' middles, SCD interiors)
Read-only import of L_gen. Env LGEN_GX_RULE=own reproduces the review-6 rule (positive control).
"""
import sys, random, collections, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import L_gen as L

NAMES = ['wall', 'win', 'slot', 'mid', 'scdint', 'loc', 'corr', 'coin', 'gx']


def classify_block(Rt):
    """per G' (time order): Counter of crossing kinds on its chain piece after its last Wb"""
    out = []
    segs = sorted(Rt.gseg, key=lambda g: (g['level'], g['e0']))
    finished = set()
    for g in segs:
        evs = Rt.events[g['e0']:g['e1']]
        last_wb = max(k for k, e in enumerate(evs) if e[0] == 'Wb')
        c = collections.Counter()
        for kind, f, info in evs[last_wb + 1:]:
            if kind in ('OP', 'SD', 'OUT', 'Wt', 'Wb'):
                continue
            if kind == 'SX':
                c['SX'] += 1
                continue
            lg = Rt.leg.get(f)
            if kind == 'GX':
                c['GX.own' if lg in g['own'] else 'GX.finished' if lg in finished else 'GX.pending'] += 1
            else:
                r = NAMES[Rt.role[f]]
                c['CHX.' + r + ('.own' if r == 'mid' and lg in g['own'] else '')] += 1
        out.append((g['key'], c))
        finished |= g['own']
    return out


def main():
    rng = random.Random(1)
    inst = L.random_instance(rng)
    N = L.netlist(inst); L.contract(N)
    B = L.Bus(N); B.order(); B.rows()
    Lv = L.Level(B); Lv.blocks()
    bad_total = 0
    for kind in ('scdc', 'dio'):
        tn = [t for t in B.tiles if B.tiles[t]['kind'] == kind][0]
        for par in (0, 1):
            r = L.block_template(Lv.tb[tn], par)
            errs = {k: v['err'] for k, v in r['levels'].items()}
            per = classify_block(r['router'])
            tot = collections.Counter()
            for _, c in per:
                tot.update(c)
            bad = tot['GX.own'] + tot['GX.pending']
            bad_total += bad
            nonsx = sum(1 for _, c in per if any(k != 'SX' for k in c))
            print(f'{kind} parity {par}: errors {errs}; G\' {len(per)}, with a non-SX crossing after the passes '
                  f'{nonsx}; own/pending GX {bad}')
            for k, v in sorted(tot.items()):
                print(f'   {k}: {v}')
    print('no own-component or pending GX' if bad_total == 0 else f'{bad_total} own/pending GX (F1 present)')


if __name__ == '__main__':
    main()
