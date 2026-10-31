#!/usr/bin/env python3
"""review6_hooks2.py -- review 6: per G' and per check edge, which legs/floor do L_gen's check walks cross?

After the review-6 repairs the check walks are drawn on the chain (L_gen.Router._checks): for check i the edge
Out_{i-1} -> Op_i (ending at the SO_i box next to b_i) and the edge Op_i -> SD_i (ending next to a_i). This prints,
for the diode and SCD tile blocks (parity 0), every crossing on those edges with the crossed leg, flagged own /
finished / pending, from the router's raw events. Env LGEN_GX_RULE=own reproduces the review-6 rule."""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import L_gen as L

NAMES = ['wall', 'win', 'slot', 'mid', 'scdint', 'loc', 'corr', 'coin', 'gx']

if __name__ == '__main__':
    rng = random.Random(1)
    inst = L.random_instance(rng)
    N = L.netlist(inst); L.contract(N)
    B = L.Bus(N); B.order(); B.rows()
    Lv = L.Level(B); Lv.blocks()
    own_total = 0
    for kind in sys.argv[1:] or ('dio', 'scdc'):
        tn = [t for t in B.tiles if B.tiles[t]['kind'] == kind][0]
        r = L.block_template(Lv.tb[tn], 0)
        Rt = r['router']
        print(kind, {k: v['err'] for k, v in r['levels'].items()})
        finished = set()
        for g in sorted(Rt.gseg, key=lambda g: (g['level'], g['e0'])):
            evs = Rt.events[g['e0']:g['e1']]
            last_wb = max(k for k, e in enumerate(evs) if e[0] == 'Wb')
            edge, cur = None, []
            for kind_, f, info in evs[last_wb + 1:]:
                if kind_ in ('OP', 'SD'):
                    i = info[1]
                    a, b = g['checks'][i]
                    tag = f'Out{i - 1}->Op{i} (SO at {b})' if kind_ == 'OP' else f'Op{i}->SD{i} (SD at {a})'
                    if cur:
                        print(f'   {g["key"][1]} level {g["level"]} {tag}: {cur}')
                    cur = []
                    continue
                if kind_ in ('OUT', 'Wt', 'Wb'):
                    continue
                lg = Rt.leg.get(f)
                if kind_ == 'SX':
                    cur.append(('SX',))
                elif kind_ == 'GX':
                    st = 'OWN' if lg in g['own'] else 'finished' if lg in finished else 'PENDING'
                    own_total += st != 'finished'
                    cur.append(('GX', lg, st))
                else:
                    r_ = NAMES[Rt.role[f]]
                    cur.append(('CHX', r_, lg if r_ == 'mid' else None, 'own(dead)' if lg in g['own'] else ''))
            finished |= g['own']
    print('own/pending GX on check walks:', own_total)
