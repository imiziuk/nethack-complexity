#!/usr/bin/env python3
"""review6_hooks2.py -- review 6: per check location, which legs/floor do L_gen's hook paths cross (diode + SCD tile)."""
import sys, random
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import L_gen as L

final = {}

def wrap():
    orig = L.Router.dijkstra
    def dij(self, src, targets, level, own, limit=None, dead=(), pen=None, box=None):
        path, cost = orig(self, src, targets, level, own, limit=limit, dead=dead, pen=pen, box=box)
        if path is not None and isinstance(own, set) and not own:
            kinds = []
            for i, jv in path:
                if not jv:
                    continue
                if jv[0] == 'GX':
                    kinds.append(('GX', self.leg.get(jv[1])))
                elif jv[0] == 'CHX':
                    kinds.append(('CHX', ['wall','win','slot','mid','scdint','loc','corr','coin','gx'][self.role[jv[1]]],
                                  self.leg[jv[1]] if self.role[jv[1]] == L.MIDR else None))
                else:
                    kinds.append((jv[0],))
            self._hk_cur.append(kinds)
        return path, cost
    L.Router.dijkstra = dij
    og = L.Router._gprime
    def gp(self, head, G, own, rot, gap, rad):
        self._hk_cur = []
        nh, info = og(self, head, G, own, rot, gap, rad)
        if nh is not None:
            final[(G['tile'], G['name'], G['level'])] = dict(zip(G['locs'].keys(), self._hk_cur))
        return nh, info
    L.Router._gprime = gp

if __name__ == '__main__':
    wrap()
    rng = random.Random(1)
    inst = L.random_instance(rng)
    N = L.netlist(inst); L.contract(N)
    B = L.Bus(N); B.order(); B.rows()
    Lv = L.Level(B); Lv.blocks()
    for kind in sys.argv[1:] or ('dio', 'scdc'):
        tn = [t for t in B.tiles if B.tiles[t]['kind'] == kind][0]
        final.clear()
        r = L.block_template(Lv.tb[tn], 0)
        print(kind, {k: v['err'] for k, v in r['levels'].items()})
        for key, d in sorted(final.items(), key=str):
            for loc, ks in d.items():
                if ks:
                    print('  ', key[1], 'level', key[2], 'loc', loc, ks)
